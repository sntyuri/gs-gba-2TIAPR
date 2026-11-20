"""LLM open source do Hugging Face rodando LOCALMENTE (sem chave de API).

O agente do CitizenTech usa o LangChain, mas o LangChain só sabe fazer "tool
calling" (o modelo pedir para chamar uma ferramenta) com modelos servidos por
API. Este módulo implementa essa ponte para um modelo carregado com a
biblioteca transformers na CPU da própria máquina:

  1. mensagens do LangChain  ->  formato de chat do Hugging Face
  2. tokenizer.apply_chat_template(..., tools=esquemas)   (o template do modelo
     descreve as ferramentas no prompt, no formato em que ele foi treinado)
  3. model.generate()  ->  texto gerado
  4. blocos <tool_call>{"name": ..., "arguments": {...}}</tool_call> do texto
     ->  AIMessage.tool_calls (o LangChain executa a ferramenta e devolve o
     resultado como ToolMessage, que volta ao passo 1)

Otimização para CPU: reaproveitamento do prefixo (KV cache). Cada passo do
agente reenvia o prompt de sistema, os esquemas das ferramentas e a conversa
anterior; o cache de atenção da parte que coincide com a chamada anterior é
reutilizado e o modelo só processa os tokens novos (ex.: o resultado da
ferramenta). A saída é a mesma (decodificação gulosa), só que mais rápida.

Modelo padrão: Qwen/Qwen3-1.7B (Apache 2.0). Foi treinado para chamar
ferramentas, entende português e cabe na CPU (cerca de 7 GB de RAM em float32).
Testamos e descartamos: bfloat16 (sem AVX-512 BF16 fica 3x mais lento) e
quantização dinâmica int8 (mais rápida, mas o modelo deixou de chamar ferramentas).
Para trocar de modelo, defina CITIZENTECH_HF_MODEL, por exemplo:
    CITIZENTECH_HF_MODEL=Qwen/Qwen3-4B          # melhor, cerca de 2,5x mais lento
    CITIZENTECH_HF_MODEL=Qwen/Qwen3-0.6B        # mais rápido, bem menos preciso
    CITIZENTECH_HF_MODEL=Qwen/Qwen2.5-3B-Instruct

O download (cerca de 3,4 GB para o 1.7B) acontece na primeira execução e fica
no cache do Hugging Face (~/.cache/huggingface). Não é preciso token: o modelo
é público. Depois disso tudo roda offline; nenhum dado sai da máquina.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool

MODELO_PADRAO = "Qwen/Qwen3-1.7B"

_MODELOS: dict[tuple, tuple] = {}     # (modelo, dtype) -> (tokenizer, modelo): um só carregamento por processo
_PREFIXO: dict[tuple, tuple] = {}     # (modelo, dtype) -> (tokens já processados, KV cache) da última geração
_LOCK_CARGA = threading.Lock()
_LOCK_GERACAO = threading.Lock()      # uma geração por vez (a CPU já usa todos os núcleos)
MIN_PREFIXO = 64                      # abaixo disso não compensa reaproveitar o cache

RE_TOOL_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
RE_THINK = re.compile(r"<think>.*?</think>", re.S)
RE_ESPECIAIS = re.compile(r"<\|[^|>]+\|>")


def carregar(modelo: str, dtype: str = "float32"):
    """Carrega (uma vez) o tokenizer e os pesos do modelo do Hugging Face Hub."""
    chave = (modelo, dtype)
    with _LOCK_CARGA:
        if chave not in _MODELOS:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            t0 = time.time()
            tok = AutoTokenizer.from_pretrained(modelo)
            mod = AutoModelForCausalLM.from_pretrained(modelo, dtype=getattr(torch, dtype))
            mod.eval()
            print(f"[llm_local] {modelo} carregado em {time.time() - t0:.0f} s "
                  f"({sum(p.numel() for p in mod.parameters()) / 1e9:.2f} B parâmetros, {dtype}, CPU, "
                  f"{torch.get_num_threads()} threads)")
            _MODELOS[chave] = (tok, mod)
        return _MODELOS[chave]


def _texto(msg: BaseMessage) -> str:
    c = msg.content
    if isinstance(c, str):
        return c
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in c)


def para_chat_hf(mensagens: list[BaseMessage]) -> list[dict]:
    """Converte mensagens do LangChain para o formato de chat do transformers."""
    conversa = []
    for m in mensagens:
        if isinstance(m, SystemMessage):
            conversa.append({"role": "system", "content": _texto(m)})
        elif isinstance(m, HumanMessage):
            conversa.append({"role": "user", "content": _texto(m)})
        elif isinstance(m, AIMessage):
            d: dict[str, Any] = {"role": "assistant", "content": _texto(m)}
            if m.tool_calls:
                d["tool_calls"] = [{"type": "function", "function": {"name": tc["name"], "arguments": tc["args"]}}
                                   for tc in m.tool_calls]
            conversa.append(d)
        elif isinstance(m, ToolMessage):
            conversa.append({"role": "tool", "name": m.name, "content": _texto(m)})
    return conversa


def extrair_chamadas(texto: str, nomes_validos: set[str] | None = None) -> tuple[str, list[dict]]:
    """Separa o texto livre das chamadas de ferramenta <tool_call>{...}</tool_call>."""
    chamadas = []
    for bloco in RE_TOOL_CALL.findall(texto):
        try:
            d = json.loads(bloco)
        except json.JSONDecodeError:
            continue
        nome = d.get("name")
        args = d.get("arguments", d.get("parameters", {})) or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if not nome or (nomes_validos and nome not in nomes_validos):
            continue
        chamadas.append({"name": nome, "args": args if isinstance(args, dict) else {},
                         "id": f"call_{uuid.uuid4().hex[:12]}", "type": "tool_call"})
    conteudo = RE_TOOL_CALL.sub("", texto)
    conteudo = conteudo.split("<tool_call>")[0]          # chamada truncada pelo limite de tokens
    return conteudo.strip(), chamadas


def _gerar(chave: tuple, mod, ids, args: dict) -> tuple[Any, int]:
    """model.generate() reaproveitando o KV cache do maior prefixo em comum com a geração anterior."""
    anterior = _PREFIXO.pop(chave, None)          # o cache é "consumido": se a geração falhar, não fica inconsistente
    reaproveitados = 0
    cache = None
    if anterior is not None:
        tokens_ant, cache_ant = anterior
        n = min(len(tokens_ant), ids.shape[1] - 1)    # pelo menos 1 token novo precisa ser processado
        iguais = (tokens_ant[:n] == ids[0, :n]).int()
        comum = int(iguais.cumprod(0).sum()) if n > 0 else 0
        if comum >= MIN_PREFIXO:
            excesso = cache_ant.get_seq_length() - comum
            if excesso > 0:
                cache_ant.crop(-excesso)      # valor negativo = remover N tokens (transformers 4.4x e 5.x)
            cache, reaproveitados = cache_ant, comum
    try:
        saida = mod.generate(input_ids=ids, attention_mask=ids.new_ones(ids.shape), past_key_values=cache,
                             return_dict_in_generate=True, **args)
    except Exception:
        if cache is None:
            raise
        saida = mod.generate(input_ids=ids, attention_mask=ids.new_ones(ids.shape),   # sem cache, por segurança
                             return_dict_in_generate=True, **args)
        reaproveitados = 0
    kv = getattr(saida, "past_key_values", None)
    if kv is not None and hasattr(kv, "crop") and hasattr(kv, "get_seq_length"):
        _PREFIXO[chave] = (saida.sequences[0, :kv.get_seq_length()].clone(), kv)
    return saida.sequences, reaproveitados


class ChatHFLocal(BaseChatModel):
    """Chat model do LangChain para um LLM do Hugging Face rodando na CPU, com tool calling."""

    modelo: str = MODELO_PADRAO
    max_new_tokens: int = 900
    temperatura: float = 0.0          # 0 = decodificação gulosa: respostas reproduzíveis
    dtype: str = "float32"            # CPUs sem AVX-512 BF16 são mais rápidas em float32
    pensar: bool = False              # modo "thinking" do Qwen3 (mais lento; desligado)
    reaproveitar_prefixo: bool = True

    @property
    def _llm_type(self) -> str:
        return "huggingface-local"

    @property
    def _identifying_params(self) -> dict:
        return {"modelo": self.modelo, "dtype": self.dtype, "temperatura": self.temperatura}

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        """Anexa os esquemas JSON das ferramentas; eles vão para o chat template a cada chamada."""
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools], **kwargs)

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, tools: list | None = None,
                  **kwargs) -> ChatResult:
        import torch

        tok, mod = carregar(self.modelo, self.dtype)
        prompt = tok.apply_chat_template(para_chat_hf(messages), tools=tools or None, add_generation_prompt=True,
                                         tokenize=False, enable_thinking=self.pensar)
        ids = tok(prompt, return_tensors="pt")["input_ids"]
        n_in = ids.shape[1]
        args = {"max_new_tokens": self.max_new_tokens, "pad_token_id": tok.pad_token_id or tok.eos_token_id}
        if self.temperatura > 0:
            args.update(do_sample=True, temperature=self.temperatura, top_p=0.9)
        else:
            args.update(do_sample=False, temperature=None, top_p=None, top_k=None)
        with _LOCK_GERACAO, torch.inference_mode():
            t0 = time.perf_counter()
            if self.reaproveitar_prefixo:
                seqs, reaproveitados = _gerar((self.modelo, self.dtype), mod, ids, args)
            else:
                seqs, reaproveitados = mod.generate(input_ids=ids, attention_mask=torch.ones_like(ids), **args), 0
            dur = time.perf_counter() - t0
        novos = seqs[0, n_in:]
        bruto = tok.decode(novos, skip_special_tokens=False)
        texto = RE_ESPECIAIS.sub("", RE_THINK.sub("", bruto))
        if stop:
            for s in stop:
                texto = texto.split(s)[0]
        nomes = {t["function"]["name"] for t in tools} if tools else None
        conteudo, chamadas = extrair_chamadas(texto, nomes)
        n_out = int(novos.shape[0])
        msg = AIMessage(
            content=conteudo, tool_calls=chamadas,
            usage_metadata={"input_tokens": n_in, "output_tokens": n_out, "total_tokens": n_in + n_out},
            response_metadata={"modelo": self.modelo, "segundos": round(dur, 1), "tokens_prefixo_reaproveitados": reaproveitados,
                               "tokens_por_segundo": round(n_out / dur, 1) if dur > 0 else None},
        )
        return ChatResult(generations=[ChatGeneration(message=msg)])


def criar_llm_local(modelo: str | None = None, **kwargs) -> ChatHFLocal:
    return ChatHFLocal(modelo=modelo or os.getenv("CITIZENTECH_HF_MODEL", MODELO_PADRAO), **kwargs)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Teste rápido do LLM local (baixa o modelo na primeira vez)")
    ap.add_argument("--modelo", default=None)
    ap.add_argument("--pergunta", default="Em uma frase: por que buracos aparecem mais depois da chuva?")
    a = ap.parse_args()
    llm = criar_llm_local(a.modelo)
    r = llm.invoke(a.pergunta)
    print(r.content)
    print(r.usage_metadata, r.response_metadata)
