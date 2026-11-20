"""Agente generativo do CitizenTech (LangChain + LLM open source do Hugging Face).

Arquitetura agêntica: um LLM local (padrão Qwen3-1.7B, rodando na CPU com a
biblioteca transformers, sem chave de API) recebe a pergunta, decide quais
ferramentas chamar (banco compartilhado, RAG, detector de visão, MQTT),
observa os resultados e redige a resposta. O ciclo "pensar -> chamar
ferramenta -> observar" é executado pelo grafo criado por
langchain.agents.create_agent, com memória de conversa por thread_id.
A ponte entre o LangChain e o modelo local está em llm_local.py.

Duas tarefas críticas usam um PIPELINE FIXO em vez do agente livre:
  - gerar_relatorio_inspecao(): o código consulta ranking, eventos, base de
    conhecimento e monta a rota; o LLM só redige. Com um modelo pequeno isso é
    mais rápido e evita que ele "esqueça" de consultar algum dado.
  - alertar_trecho_critico(): a regra (só nível ALTA) é aplicada pelo código;
    o modelo não decide sozinho acionar um dispositivo físico.

Perfis:
  zeladoria - equipe da prefeitura: ranking, relatório de inspeção, rota, alertas
  cidadao   - linguagem simples; registra reportes; nunca fala em nome da prefeitura
  geral     - os dois públicos

Uso rápido:
    from agente import criar_agente, perguntar, gerar_relatorio_inspecao
    ag = criar_agente("zeladoria")
    resposta, passos = perguntar(ag, "Quais trechos precisam de vistoria esta semana?")
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
try:  # .env na raiz do repositório (CITIZENTECH_HF_MODEL, MQTT_BASE, ...)
    from dotenv import load_dotenv
    load_dotenv(AQUI.parent.parent / ".env")
except ImportError:
    pass
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent))

from langchain.agents import create_agent  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402

import ferramentas  # noqa: E402

import banco  # noqa: E402
from llm_local import MODELO_PADRAO, criar_llm_local  # noqa: E402

PROMPT_BASE = """Você é o assistente do CitizenTech · Monitor de Pavimento, um protótipo acadêmico (FIAP,
Global Solution 2026.2) que detecta e prioriza buracos em vias urbanas a partir de três fontes:
sensores IoT em veículos (ESP32: profundidade, umidade, botão de reporte), visão computacional
(detector YOLO em fotos e vídeos) e reportes de cidadãos. Tudo é gravado em um banco compartilhado e
resumido na view de prioridade por trecho. Responda sempre em português do Brasil.

REGRAS DE DADOS
- Nunca invente trechos, pontuações, contagens, datas ou estatísticas. Todo dado sobre trechos,
  eventos, detecções ou dispositivos deve vir do bloco <dados_atuais_do_banco> anexado à pergunta
  ou de uma ferramenta de consulta chamada nesta conversa.
- Se uma ferramenta devolver erro ou lista vazia, diga isso claramente em vez de supor valores.
- Ao citar números, diga de onde vieram (ex.: "segundo o ranking do banco, ...").

REGRAS DE CONHECIMENTO (RAG)
- Cada pergunta chega acompanhada de trechos da base de conhecimento recuperados automaticamente
  (bloco <contexto_base_conhecimento>). Para perguntas sobre procedimentos, direitos do cidadão,
  fórmula de prioridade, limitações, funcionamento dos módulos ou ODS, responda com base nesses
  trechos e cite a fonte (nome do documento) ao final. Se precisar de outro assunto, chame
  buscar_base_conhecimento. Não responda essas perguntas de memória.
- Se a base não cobrir a pergunta, diga que a informação não está na base do projeto e, se for o
  caso, indique um canal oficial (SP156) ou um profissional (advogado, Defensoria Pública).

RESPONSABILIDADE
- A pontuação é uma triagem. Nenhuma detecção automática confirma a gravidade de um buraco: a
  vistoria técnica presencial continua obrigatória. Deixe isso explícito quando recomendar ações.
- O CitizenTech não é a Prefeitura e não abre protocolos oficiais. Não dê parecer jurídico para um
  caso concreto; ofereça orientações gerais e indique onde buscar ajuda.
- Ações com efeito (registrar reporte, gravar detecções, enviar alerta ao ESP32) só depois de o
  usuário confirmar o trecho e a intenção. Informe o resultado da ação.
- Não peça nem registre dados pessoais (nome, CPF, telefone, endereço residencial).

ESTILO
- Seja direto e organizado. Use listas curtas e tabelas simples quando ajudarem.
- Quando pedirem um relatório de inspeção, use as seções: Resumo, Ranking de prioridade (com as
  evidências de cada trecho), Rota sugerida (agrupada por bairro, alta antes de média), Alertas e
  condições (umidade, reportes recentes), Limitações e validação humana necessária.
"""

PROMPT_PERFIL = {
    "zeladoria": "\nPÚBLICO: equipe de zeladoria/subprefeitura. Foque em priorização, evidências, rota de inspeção e "
                 "ações operacionais (sinalização provisória, vistoria). Pode enviar alerta ao ESP32 quando solicitado.\n",
    "cidadao": "\nPÚBLICO: cidadão. Use linguagem simples e acolhedora. Explique como reportar pelo SP156, como se "
               "proteger e quais são seus direitos em termos gerais. Pode registrar um reporte no CitizenTech "
               "depois que o cidadão confirmar o trecho (use listar_trechos para mostrar as opções) e a descrição. "
               "Nunca envie alertas ao ESP32 nem prometa reparo.\n",
    "geral": "\nPÚBLICO: equipe de zeladoria e cidadãos. Adapte o tom a quem está falando.\n",
}

PROMPT_RELATORIO = (
    "Gere o relatório de inspeção de pavimento de hoje para a equipe de zeladoria. Consulte o ranking "
    "de prioridade, detalhe cada trecho com registro (eventos IoT e detecções de visão) e monte a rota "
    "sugerida. Siga as seções padrão do relatório."
)


def criar_modelo(nome: str | None = None, **kwargs):
    """LLM open source do Hugging Face rodando localmente (CITIZENTECH_HF_MODEL; padrão Qwen/Qwen3-1.7B)."""
    return criar_llm_local(nome, **kwargs)


def ferramentas_do_perfil(perfil: str) -> list:
    if perfil == "cidadao":
        return ferramentas.FERRAMENTAS_CONSULTA + [ferramentas.registrar_reporte_cidadao, ferramentas.analisar_foto_buracos]
    return ferramentas.TODAS


def criar_agente(perfil: str = "geral", modelo=None, tools: list | None = None):
    """Cria o grafo do agente (modelo + ferramentas + prompt do perfil + memória por thread)."""
    if perfil not in PROMPT_PERFIL:
        raise ValueError(f"perfil inválido: {perfil} (use {list(PROMPT_PERFIL)})")
    llm = modelo if modelo is not None else criar_modelo()
    return create_agent(
        model=llm,
        tools=tools if tools is not None else ferramentas_do_perfil(perfil),
        system_prompt=PROMPT_BASE + PROMPT_PERFIL[perfil],
        checkpointer=InMemorySaver(),
        name=f"citizentech-{perfil}",
    )


def texto_da_mensagem(msg) -> str:
    """Conteúdo textual de uma mensagem (string ou lista de blocos, conforme o modelo)."""
    c = msg.content
    if isinstance(c, str):
        return c
    partes = []
    for b in c:
        if isinstance(b, dict) and b.get("type") == "text":
            partes.append(b.get("text", ""))
        elif isinstance(b, str):
            partes.append(b)
    return "".join(partes)


MARCA_CONTEXTO = "<contexto_base_conhecimento>"
# Trava contra "alucinação de ação": o modelo diz que registrou sem ter chamado a ferramenta (rodada 3, caso 8)
RE_DIZ_QUE_REGISTROU = re.compile(r"\b(registrei|vou registrar|foi registrad[oa]|est[áa] registrad[oa]|reporte registrad[oa]|"
                                  r"registro (foi )?(feito|realizado|conclu[ií]do)|o sistema registra)", re.I)
AVISO_SEM_REGISTRO = ("\n\n> ⚠️ **Atenção:** nenhum reporte foi gravado no banco nesta resposta (a ferramenta de registro "
                      "não foi executada). Confirme o código do trecho e a descrição e peça o registro novamente.")


def contexto_automatico(texto: str, k: int = 3, incluir_banco: bool = True) -> tuple[str, list]:
    """Anexa à pergunta (1) o retrato atual do banco (só para a zeladoria) e (2) os k trechos mais
    próximos da base (RAG).

    Por que automático: na 1ª rodada de avaliação o modelo pequeno deixou de chamar a busca na base
    em 4 de 5 perguntas sobre procedimentos/direitos e respondeu de memória (inclusive com orientação
    jurídica errada). Na 2ª, com só o RAG automático, ele passou a responder perguntas de dados a partir
    dos documentos, sem consultar o banco. Anexar os dois blocos resolve os dois casos; o agente segue
    decidindo as ações (registrar, analisar foto, alertar) e os detalhamentos (detalhar_trecho).
    Na 3ª rodada, o retrato do banco distraiu as respostas ao cidadão (ranking misturado numa pergunta
    sobre indenização): o cidadão recebe só a base de conhecimento."""
    import rag
    base = rag.formatar_contexto(rag.buscar(texto, k=k))
    passos_base = [{"ferramenta": "buscar_base_conhecimento", "argumentos": {"pergunta": texto, "modo": "automático"}},
                   {"resultado_de": "buscar_base_conhecimento", "resumo": base[:400]}]
    if not incluir_banco:
        return (f"{texto}\n\n{MARCA_CONTEXTO}\n{base}\n</contexto_base_conhecimento>\n"
                "(Trechos recuperados automaticamente da base de conhecimento do projeto. Se a pergunta for sobre "
                "procedimentos, direitos, regras ou funcionamento, responda com base neles e cite a fonte; se não "
                "cobrirem a pergunta, diga que a informação não está na base. Para registrar um reporte, chame a "
                "ferramenta registrar_reporte_cidadao.)"), passos_base
    conn = ferramentas.conexao()
    linhas = banco.prioridades(conn, apenas_com_registro=True)
    ranking = "\n".join(
        f"- {l['uid']} · {l['nome']} ({l['bairro'] or '-'}): nível {l['nivel']}, {l['pontuacao']} pts; "
        f"{l['graves']} graves, {l['leves']} leves, {l['reportes']} reportes, {l['deteccoes_visao']} detecções visuais; "
        f"prof. máx. {l['prof_max_mm'] if l['prof_max_mm'] is not None else '-'} mm; "
        f"umidade média {l['umidade_media'] if l['umidade_media'] is not None else '-'}%"
        for l in linhas) or "- nenhum trecho com registro"
    fatos = "\n".join(f"- {a}" for a in alertas_calculados(linhas, banco.status_dispositivos(conn)))
    passos = [{"ferramenta": "consultar_ranking_prioridade", "argumentos": {"modo": "automático"}},
              {"resultado_de": "consultar_ranking_prioridade", "resumo": ranking[:400]}] + passos_base
    conteudo = (f"{texto}\n\n<dados_atuais_do_banco>\nRanking de prioridade (do mais crítico ao menos):\n{ranking}\n"
                f"Fatos calculados pelo sistema:\n{fatos}\n</dados_atuais_do_banco>\n\n"
                f"<contexto_base_conhecimento>\n{base}\n</contexto_base_conhecimento>\n"
                "(Blocos anexados automaticamente. Use os DADOS para perguntas sobre trechos, pontuações, umidade, "
                "detecções e dispositivos; para os eventos de um trecho específico, chame detalhar_trecho. Use a BASE "
                "para procedimentos, direitos e regras, citando a fonte. Se nada cobrir a pergunta, diga que a "
                "informação não está disponível.)")
    return conteudo, passos


def perguntar(agente, texto: str, thread_id: str = "demo", recursion_limit: int = 40, contexto: bool = True):
    """Envia uma pergunta e devolve (resposta, passos), onde passos lista as ferramentas chamadas
    (as consultas automáticas aparecem com "modo": "automático")."""
    perfil = getattr(agente, "name", "") or ""
    conteudo, passos_rag = (contexto_automatico(texto, incluir_banco=not perfil.endswith("cidadao"))
                            if contexto else (texto, []))
    estado = agente.invoke(
        {"messages": [HumanMessage(content=conteudo)]},
        config={"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit},
    )
    msgs = estado["messages"]
    # mensagens geradas nesta rodada: tudo depois da última HumanMessage
    idx = max(i for i, m in enumerate(msgs) if isinstance(m, HumanMessage))
    novas = msgs[idx + 1:]
    passos = list(passos_rag)
    for m in novas:
        if isinstance(m, AIMessage) and m.tool_calls:
            for tc in m.tool_calls:
                passos.append({"ferramenta": tc["name"], "argumentos": tc["args"]})
        elif isinstance(m, ToolMessage):
            conteudo = m.content if isinstance(m.content, str) else str(m.content)
            passos.append({"resultado_de": m.name, "resumo": conteudo[:400]})
    resposta = next((texto_da_mensagem(m) for m in reversed(novas) if isinstance(m, AIMessage) and texto_da_mensagem(m)), "")
    chamadas = {p["ferramenta"] for p in passos if "ferramenta" in p}
    if RE_DIZ_QUE_REGISTROU.search(resposta) and "registrar_reporte_cidadao" not in chamadas:
        resposta += AVISO_SEM_REGISTRO
        passos.append({"resultado_de": "trava_de_acao", "resumo": "resposta afirmava registro sem chamada da ferramenta: aviso anexado"})
    return resposta, passos


# ------------------------------------------------------------------ pipelines fixos
PROMPT_RELATORIO_DADOS = """Redija o relatório de inspeção de pavimento de hoje ({data}) para a equipe de zeladoria,
usando SOMENTE os dados abaixo, que vieram do banco do CitizenTech e da base de conhecimento.
Não invente trechos, números ou datas. Use exatamente estas seções, em Markdown:

## Resumo
(2 a 3 frases: quantos trechos têm registro, quantos em prioridade alta e o principal risco)
## Ranking de prioridade
(tabela: posição, trecho, bairro, nível, pontuação e as evidências: graves, leves, reportes, detecções visuais, profundidade máxima, umidade)
## Rota sugerida
(siga a ordem da ROTA abaixo e explique em uma linha por parada o motivo)
## Alertas e condições
(use SOMENTE a lista ALERTAS abaixo, já calculada pelo sistema; não acrescente outros)
## Limitações e validação humana necessária
(a pontuação é triagem; a vistoria presencial confirma a gravidade; cite o procedimento da base)

RANKING (vw_prioridade_trechos):
{ranking}

ÚLTIMOS EVENTOS POR TRECHO:
{eventos}

ROTA (calculada pelo sistema: nível alta antes de média, agrupada por bairro):
{rota}

ALERTAS (calculados pelo sistema):
{alertas}

DISPOSITIVOS:
{dispositivos}

PROCEDIMENTO (base de conhecimento):
{procedimento}
"""


def _rastrear(passos: list, ferramenta, **args) -> str:
    """Executa uma ferramenta e registra a chamada no mesmo formato do agente (rastro na interface)."""
    passos.append({"ferramenta": ferramenta.name, "argumentos": args})
    resultado = ferramenta.invoke(args)
    passos.append({"resultado_de": ferramenta.name, "resumo": str(resultado)[:400]})
    return resultado


def rota_sugerida(linhas: list[dict]) -> list[dict]:
    """Ordena as paradas: nível (alta > media > baixa), depois bairro do trecho mais crítico, depois pontuação."""
    ordem_nivel = {"alta": 0, "media": 1, "baixa": 2}
    candidatos = [l for l in linhas if l["nivel"] in ordem_nivel]
    melhor_por_bairro: dict[str, float] = {}
    for l in candidatos:
        melhor_por_bairro[l["bairro"] or "-"] = max(melhor_por_bairro.get(l["bairro"] or "-", 0), l["pontuacao"])
    candidatos.sort(key=lambda l: (ordem_nivel[l["nivel"]], -melhor_por_bairro[l["bairro"] or "-"],
                                   l["bairro"] or "-", -l["pontuacao"]))
    return [{"parada": i, "uid": l["uid"], "trecho": l["nome"], "bairro": l["bairro"], "nivel": l["nivel"],
             "pontuacao": l["pontuacao"]} for i, l in enumerate(candidatos, start=1)]


def alertas_calculados(linhas: list[dict], dispositivos: list[dict]) -> list[str]:
    """Fatos de alerta extraídos pelo código (o LLM pequeno erra limiares quando calcula sozinho)."""
    alertas = []
    for l in linhas:
        if l.get("umidade_media") is not None and l["umidade_media"] >= 80:
            alertas.append(f"Pista úmida/chuva em {l['nome']}: umidade média {l['umidade_media']}% (≥ 80%), "
                           "pontuação multiplicada por 1,2.")
        if l.get("reportes"):
            alertas.append(f"{l['reportes']} reporte(s) manual(is) de motorista/cidadão em {l['nome']}.")
        if l.get("graves"):
            alertas.append(f"{l['graves']} buraco(s) grave(s) medido(s) pelo sensor em {l['nome']} "
                           f"(profundidade máxima {l['prof_max_mm']} mm): sinalização provisória recomendada até a vistoria.")
        if l.get("deteccoes_visao"):
            alertas.append(f"{l['deteccoes_visao']} detecção(ões) visual(is) confirmada(s) em {l['nome']} "
                           f"(confiança média {l['conf_media_visao']}).")
    for d in dispositivos:
        if d.get("status") != "online":
            alertas.append(f"Dispositivo {d['device_id']} {d.get('status')} desde {d.get('atualizado_em')}.")
    return alertas or ["Nenhum alerta."]


def gerar_relatorio_inspecao(modelo=None, max_trechos: int = 6) -> tuple[str, list]:
    """Relatório de inspeção da zeladoria: o código coleta os dados, o LLM redige (pipeline fixo)."""
    from datetime import datetime

    passos: list = []
    _rastrear(passos, ferramentas.consultar_ranking_prioridade, apenas_com_registro=True)
    linhas = banco.prioridades(ferramentas.conexao(), apenas_com_registro=True)[:max_trechos]
    campos = ["uid", "nome", "bairro", "nivel", "pontuacao", "graves", "leves", "reportes", "deteccoes_visao",
              "conf_media_visao", "prof_max_mm", "umidade_media"]
    ranking = [{c: l.get(c) for c in campos} for l in linhas]
    eventos = {}
    for l in linhas:
        _rastrear(passos, ferramentas.detalhar_trecho, codigo_trecho=l["uid"])
        eventos[l["uid"]] = [{k: e[k] for k in ("recebido_em", "tipo", "severidade", "profundidade_mm", "umidade_pct")}
                             for e in banco.eventos_do_trecho(ferramentas.conexao(), l["uid"], 4)]
    dispositivos = _rastrear(passos, ferramentas.status_dispositivos)
    procedimento = _rastrear(passos, ferramentas.buscar_base_conhecimento,
                             pergunta="procedimento de triagem, vistoria presencial e sinalização provisória de buracos")
    if not linhas:
        return "Nenhum trecho com registro no banco até agora: não há o que priorizar.", passos

    js = lambda o: json.dumps(o, ensure_ascii=False)  # noqa: E731
    prompt = PROMPT_RELATORIO_DADOS.format(
        data=datetime.now().strftime("%d/%m/%Y"), ranking=js(ranking), eventos=js(eventos),
        rota=js(rota_sugerida(linhas)), dispositivos=dispositivos, procedimento=procedimento[:1800],
        alertas="\n".join(f"- {a}" for a in alertas_calculados(linhas, banco.status_dispositivos(ferramentas.conexao()))))
    llm = modelo if modelo is not None else criar_modelo(max_new_tokens=1200)
    resposta = llm.invoke([SystemMessage(content=PROMPT_BASE + PROMPT_PERFIL["zeladoria"]), HumanMessage(content=prompt)])
    return texto_da_mensagem(resposta).strip(), passos


def alertar_trecho_critico(device_id: str = "esp32-01") -> tuple[str, list]:
    """Envia o alerta ao ESP32 SÓ se o trecho mais crítico estiver em nível ALTA (regra no código, não no LLM)."""
    passos: list = []
    _rastrear(passos, ferramentas.consultar_ranking_prioridade, apenas_com_registro=True)
    linhas = banco.prioridades(ferramentas.conexao(), apenas_com_registro=True)
    if not linhas or linhas[0]["nivel"] != "alta":
        topo = f"{linhas[0]['nome']} ({linhas[0]['nivel']}, {linhas[0]['pontuacao']})" if linhas else "nenhum"
        return f"Nenhum trecho em prioridade ALTA (mais crítico: {topo}). Alerta não enviado.", passos
    t = linhas[0]
    r = json.loads(_rastrear(passos, ferramentas.enviar_alerta_esp32, device_id=device_id,
                             motivo=f"trecho crítico: {t['nome']} ({t['pontuacao']} pts)"))
    estado = "enviado" if r.get("enviado") else ("simulado (modo sem rede)" if r.get("simulado") else f"NÃO enviado: {r.get('erro')}")
    return (f"Alerta {estado} ao {device_id} pelo tópico `{r['topico']}`.\n\nTrecho: **{t['nome']}** ({t['bairro']}), "
            f"pontuação {t['pontuacao']} (nível alta: {t['graves']} graves, {t['leves']} leves, {t['reportes']} reportes, "
            f"{t['deteccoes_visao']} detecções visuais). O LED vermelho do veículo pisca por 5 s. "
            "A vistoria presencial continua necessária para confirmar a gravidade."), passos


def imprimir_passos(passos: list) -> None:
    for p in passos:
        if "ferramenta" in p:
            print(f"  -> {p['ferramenta']}({p['argumentos']})")
        else:
            print(f"  <- {p['resultado_de']}: {p['resumo'][:160].replace(chr(10), ' ')}...")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Conversa com o agente CitizenTech no terminal")
    ap.add_argument("--perfil", default="geral", choices=list(PROMPT_PERFIL))
    ap.add_argument("--pergunta", default=None, help="uma única pergunta (senão, modo interativo)")
    ap.add_argument("--relatorio", action="store_true", help="gera o relatório de inspeção (pipeline fixo)")
    a = ap.parse_args()
    if a.relatorio:
        r, p = gerar_relatorio_inspecao()
        imprimir_passos(p)
        print("\n" + r)
        raise SystemExit
    ag = criar_agente(a.perfil)
    if a.pergunta:
        r, p = perguntar(ag, a.pergunta)
        imprimir_passos(p)
        print("\n" + r)
    else:
        print("Agente CitizenTech (Ctrl+C para sair)")
        while True:
            try:
                q = input("\nvocê> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q:
                continue
            r, p = perguntar(ag, q)
            imprimir_passos(p)
            print("\nagente> " + r)
