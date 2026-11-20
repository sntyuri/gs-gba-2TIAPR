"""Tarefa 1 e 2 do processo: coletar os arquivos da pasta de entrada e validar.

Três canais chegam em formatos diferentes e viram uma tabela única:
  - .json  exportação do aplicativo Zela ("meus-dados-zela.json")
  - .csv   planilha da central telefônica (separador ; ou ,)
  - .xlsx  planilha do balcão de atendimento

Arquivo que não dá para ler vai para a quarentena, com o motivo no log, e o
robô continua com os demais. Linha inválida vira "rejeitada", sem derrubar o arquivo.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from .catalogo import normalizar
from .registro import log

COLUNAS = ["chave", "protocolo", "origem", "arquivo", "data", "bairro", "referencia", "relato"]

# Nomes de coluna aceitos em cada campo (comparados sem acento e em minúsculas)
APELIDOS = {
    "relato": ("relato", "descricao", "texto", "reclamacao", "solicitacao", "mensagem"),
    "bairro": ("bairro", "regiao", "local"),
    "referencia": ("referencia", "ponto de referencia", "endereco"),
    "protocolo": ("protocolo", "id", "numero"),
    "data": ("data", "criadoem", "criado em", "data de abertura", "abertura"),
}
ORIGEM_POR_EXTENSAO = {".json": "aplicativo", ".csv": "central telefônica", ".xlsx": "balcão"}


class ArquivoInvalido(Exception):
    """O arquivo inteiro não pode ser aproveitado (vai para a quarentena)."""


def _ler_json(caminho: Path) -> pd.DataFrame:
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as erro:
        raise ArquivoInvalido(f"JSON corrompido ({erro.msg}, linha {erro.lineno})") from erro
    # A exportação do app traz {"conta": {...}, "solicitacoes": [...]}. O bloco "conta"
    # (nome e e-mail do cidadão) é ignorado de propósito: o robô não precisa dele.
    if isinstance(dados, dict):
        dados = dados.get("solicitacoes")
    if not isinstance(dados, list):
        raise ArquivoInvalido("JSON sem a lista de solicitações")
    return pd.DataFrame([item for item in dados if isinstance(item, dict)])


def _ler_csv(caminho: Path) -> pd.DataFrame:
    ultimo_erro = None
    for codificacao in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(caminho, sep=None, engine="python", dtype=str,
                               encoding=codificacao, keep_default_na=False)
        except UnicodeDecodeError as erro:
            ultimo_erro = erro
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as erro:
            raise ArquivoInvalido(f"CSV ilegível ({erro})") from erro
    raise ArquivoInvalido(f"codificação não reconhecida ({ultimo_erro})")


def _ler_xlsx(caminho: Path) -> pd.DataFrame:
    try:
        return pd.read_excel(caminho, dtype=str, engine="openpyxl").fillna("")
    except Exception as erro:  # openpyxl levanta tipos variados para arquivo danificado
        raise ArquivoInvalido(f"planilha ilegível ({type(erro).__name__})") from erro


LEITORES = {".json": _ler_json, ".csv": _ler_csv, ".xlsx": _ler_xlsx}


def _padronizar(tabela: pd.DataFrame, caminho: Path) -> pd.DataFrame:
    nomes = {normalizar(str(col)).strip(): col for col in tabela.columns}
    saida = pd.DataFrame(index=tabela.index)
    for campo, apelidos in APELIDOS.items():
        coluna = next((nomes[a] for a in apelidos if a in nomes), None)
        saida[campo] = tabela[coluna].fillna("").astype(str).str.strip() if coluna is not None else ""
    if not any(a in nomes for a in APELIDOS["relato"]):
        raise ArquivoInvalido("coluna obrigatória ausente: relato/descrição")
    saida["origem"] = ORIGEM_POR_EXTENSAO[caminho.suffix.lower()]
    saida["arquivo"] = caminho.name
    saida["chave"] = [_chave(linha) for linha in saida.to_dict("records")]
    return saida[COLUNAS]


def _chave(linha: dict) -> str:
    """Identidade do pedido, usada para não processar duas vezes (idempotência)."""
    if linha["protocolo"]:
        return f"protocolo:{linha['protocolo']}"
    base = "|".join(normalizar(linha[c]) for c in ("relato", "bairro", "data"))
    return "hash:" + hashlib.sha256(base.encode()).hexdigest()[:16]


def ler_arquivo(caminho: Path) -> pd.DataFrame:
    leitor = LEITORES.get(caminho.suffix.lower())
    if leitor is None:
        raise ArquivoInvalido(f"formato não aceito ({caminho.suffix or 'sem extensão'})")
    if caminho.stat().st_size == 0:
        raise ArquivoInvalido("arquivo vazio")
    tabela = leitor(caminho)
    if tabela.empty:
        raise ArquivoInvalido("arquivo sem nenhuma linha de dados")
    return _padronizar(tabela, caminho)


def _mover(caminho: Path, destino: Path) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    alvo = destino / f"{datetime.now():%Y%m%d-%H%M%S}_{caminho.name}"
    shutil.move(str(caminho), alvo)
    return alvo


def coletar(entrada: Path, quarentena: Path) -> tuple[pd.DataFrame, list[Path], list[dict]]:
    """Lê tudo o que está na pasta de entrada.

    Devolve (tabela consolidada, arquivos lidos com sucesso, falhas de arquivo).
    """
    tabelas, lidos, falhas = [], [], []
    arquivos = sorted(p for p in entrada.iterdir() if p.is_file() and not p.name.startswith("."))
    for caminho in arquivos:
        try:
            tabela = ler_arquivo(caminho)
        except ArquivoInvalido as erro:
            motivo = str(erro)
        except OSError as erro:  # arquivo sumiu ou está bloqueado por outro programa
            motivo = f"não foi possível abrir ({type(erro).__name__})"
        else:
            tabelas.append(tabela)
            lidos.append(caminho)
            log.info("Arquivo lido: %s (%d linhas)", caminho.name, len(tabela))
            continue
        falhas.append({"arquivo": caminho.name, "motivo": motivo})
        try:
            _mover(caminho, quarentena)
            log.warning("FALHA TRATADA | arquivo %s enviado para a quarentena: %s",
                        caminho.name, motivo)
        except OSError as erro:
            log.error("Não foi possível mover %s para a quarentena: %s", caminho.name, erro)
    consolidada = pd.concat(tabelas, ignore_index=True) if tabelas else pd.DataFrame(columns=COLUNAS)
    return consolidada, lidos, falhas


def validar(tabela: pd.DataFrame, tamanho_minimo: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa linhas aproveitáveis das rejeitadas (com o motivo)."""
    tabela = tabela.copy()
    relato = tabela["relato"].str.strip()
    motivo = pd.Series("", index=tabela.index)
    motivo[relato.str.len() < tamanho_minimo] = f"relato com menos de {tamanho_minimo} caracteres"
    motivo[relato == ""] = "relato vazio"
    repetida = tabela.duplicated("chave", keep="first") & (motivo == "")
    motivo[repetida] = "repetida no mesmo lote"
    tabela["motivo"] = motivo
    validas = tabela[motivo == ""].drop(columns="motivo").reset_index(drop=True)
    rejeitadas = tabela[motivo != ""].reset_index(drop=True)
    for linha in rejeitadas.to_dict("records"):
        log.warning("FALHA TRATADA | linha rejeitada em %s (%s): %s",
                    linha["arquivo"], linha["protocolo"] or "sem protocolo", linha["motivo"])
    return validas, rejeitadas


def arquivar(arquivos: list[Path], processados: Path) -> None:
    destino = processados / f"{datetime.now():%Y-%m-%d}"
    for caminho in arquivos:
        try:
            _mover(caminho, destino)
        except OSError as erro:
            log.error("Não foi possível arquivar %s: %s", caminho.name, erro)
