"""Tarefa 5 do processo: devolver o resultado em Excel, a interface que a
prefeitura já conhece (pandas para montar, openpyxl para formatar).

A planilha de triagem tem cinco abas: Resumo, Encaminhados, Revisão humana,
Rejeitadas e Execução. Cada órgão também recebe a sua própria planilha.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import catalogo

CORES_PRIORIDADE = {"Urgente": "F4B6B6", "Alta": "FAD7A0", "Média": "FCF3CF", "Baixa": "D5F5E3"}
CABECALHO = PatternFill("solid", fgColor="1F3A5F")

COLUNAS_PEDIDO = {
    "protocolo": "Protocolo", "prioridade_rotulo": "Prioridade", "prazo_dias": "Prazo (dias úteis)",
    "categoria_nome": "Categoria", "orgao": "Órgão responsável", "bairro": "Bairro",
    "referencia": "Ponto de referência", "relato": "Relato (sem dados pessoais)",
    "motivos": "Por que esta prioridade", "confianca_pct": "Confiança da IA (%)",
    "origem": "Canal", "data": "Data do pedido",
}
COLUNAS_REVISAO = {
    "protocolo": "Protocolo", "motivo_revisao": "Por que precisa de revisão",
    "categoria_nome": "Categoria sugerida pela IA", "confianca_pct": "Confiança da IA (%)",
    "segunda_nome": "Segunda opção", "categoria_correta": "Categoria correta (preencher)",
    "prioridade_rotulo": "Prioridade sugerida", "bairro": "Bairro",
    "relato": "Relato (sem dados pessoais)", "origem": "Canal",
}


def _seguro(valor):
    """Impede que um relato começado por = + - @ seja executado como fórmula no Excel."""
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@"):
        return "'" + valor
    return valor


def _tabela(dados: pd.DataFrame, colunas: dict) -> pd.DataFrame:
    saida = dados.reindex(columns=list(colunas)).rename(columns=colunas)
    return saida.apply(lambda coluna: coluna.map(_seguro))


def _formatar(aba, larguras: dict | None = None) -> None:
    for celula in aba[1]:
        celula.fill = CABECALHO
        celula.font = Font(bold=True, color="FFFFFF")
        celula.alignment = Alignment(vertical="center", wrap_text=True)
    aba.freeze_panes = "A2"
    if aba.max_row > 1:
        aba.auto_filter.ref = aba.dimensions
    for indice, coluna in enumerate(aba.iter_cols(min_row=1, max_row=1), start=1):
        titulo = str(coluna[0].value or "")
        largura = (larguras or {}).get(titulo)
        if largura is None:
            maior = max((len(str(c.value or "")) for c in aba[get_column_letter(indice)]), default=10)
            largura = min(max(12, maior + 2), 45)
        aba.column_dimensions[get_column_letter(indice)].width = largura
        if titulo.startswith(("Relato", "Por que")):
            for celula in aba[get_column_letter(indice)][1:]:
                celula.alignment = Alignment(wrap_text=True, vertical="top")
        if titulo.startswith("Prioridade"):
            for celula in aba[get_column_letter(indice)][1:]:
                cor = CORES_PRIORIDADE.get(str(celula.value))
                if cor:
                    celula.fill = PatternFill("solid", fgColor=cor)
                    celula.font = Font(bold=celula.value == "Urgente")


INDICADORES = {
    "execucao": "Execução", "inicio": "Início", "lidos": "Linhas lidas", "novos": "Pedidos novos",
    "ja_processados": "Já tratados antes (ignorados)", "encaminhados": "Encaminhados pelo robô",
    "revisao_humana": "Enviados para revisão humana", "rejeitados": "Linhas rejeitadas",
    "urgentes": "Pedidos urgentes", "dados_pessoais_removidos": "Dados pessoais removidos dos relatos",
    "falhas_tratadas": "Falhas tratadas", "motor_ia": "Motor de IA",
    "limiar_confianca": "Limiar de confiança", "clima": "Previsão de chuva", "emails": "E-mails",
    "cpu_pct": "CPU da máquina (%)", "memoria_pct": "Memória da máquina (%)",
    "memoria_robo_mb": "Memória usada pelo robô (MB)", "disco_livre_mb": "Disco livre (MB)",
}

LARGURAS = {"Relato (sem dados pessoais)": 70, "Por que esta prioridade": 45,
            "Por que precisa de revisão": 40}


def gravar_triagem(caminho: Path, encaminhados: pd.DataFrame, revisao: pd.DataFrame,
                   rejeitadas: pd.DataFrame, resumo: dict, etapas: list[dict]) -> Path:
    por_orgao = (encaminhados.groupby(["orgao", "prioridade_rotulo"]).size().unstack(fill_value=0)
                 if not encaminhados.empty else pd.DataFrame())
    por_orgao = por_orgao.reindex(columns=[c for c in CORES_PRIORIDADE if c in por_orgao.columns])
    if not por_orgao.empty:
        por_orgao["Total"] = por_orgao.sum(axis=1)
        por_orgao = por_orgao.sort_values("Total", ascending=False)
    por_orgao.index.name = "Órgão responsável"

    execucao = pd.DataFrame(
        [(rotulo, _seguro(str(resumo[chave]))) for chave, rotulo in INDICADORES.items() if chave in resumo],
        columns=["Indicador", "Valor"])
    falhas = pd.DataFrame(resumo.get("falhas", []) or [{"onde": "-", "motivo": "nenhuma falha nesta execução"}])
    tarefas = pd.DataFrame(etapas)

    with pd.ExcelWriter(caminho, engine="openpyxl") as planilha:
        por_orgao.reset_index().to_excel(planilha, sheet_name="Resumo", index=False)
        _tabela(encaminhados, COLUNAS_PEDIDO).to_excel(planilha, sheet_name="Encaminhados", index=False)
        _tabela(revisao, COLUNAS_REVISAO).to_excel(planilha, sheet_name="Revisão humana", index=False)
        rejeitadas.reindex(columns=["arquivo", "protocolo", "origem", "motivo"]).rename(columns={
            "arquivo": "Arquivo", "protocolo": "Protocolo", "origem": "Canal",
            "motivo": "Motivo da rejeição"}).to_excel(planilha, sheet_name="Rejeitadas", index=False)
        execucao.to_excel(planilha, sheet_name="Execução", index=False)
        linha = len(execucao) + 3
        falhas.rename(columns={"onde": "Falha tratada em", "motivo": "Motivo"}).to_excel(
            planilha, sheet_name="Execução", index=False, startrow=linha)
        tarefas.to_excel(planilha, sheet_name="Execução", index=False, startrow=linha + len(falhas) + 3)

        for nome in ("Resumo", "Encaminhados", "Revisão humana", "Rejeitadas"):
            _formatar(planilha.sheets[nome], LARGURAS)
        aba = planilha.sheets["Execução"]
        aba.column_dimensions["A"].width = 32
        aba.column_dimensions["B"].width = 60
        aba.column_dimensions["C"].width = 16
        for celula in aba[1]:
            celula.fill, celula.font = CABECALHO, Font(bold=True, color="FFFFFF")

        # Revisão humana: a pessoa escolhe a categoria certa em uma lista
        aba = planilha.sheets["Revisão humana"]
        if len(revisao):
            nomes = ",".join(c.nome.replace(",", "") for c in catalogo.CATEGORIAS)
            lista = DataValidation(type="list", formula1=f'"{nomes}"', allow_blank=True)
            aba.add_data_validation(lista)
            coluna = get_column_letter(list(COLUNAS_REVISAO).index("categoria_correta") + 1)
            lista.add(f"{coluna}2:{coluna}{len(revisao) + 1}")
            for celula in aba[coluna][1:]:
                celula.fill = PatternFill("solid", fgColor="FFF9C4")
    return caminho


def gravar_orgao(caminho: Path, pedidos: pd.DataFrame, colunas: dict | None = None) -> Path:
    with pd.ExcelWriter(caminho, engine="openpyxl") as planilha:
        _tabela(pedidos, colunas or COLUNAS_PEDIDO).to_excel(planilha, sheet_name="Pedidos", index=False)
        _formatar(planilha.sheets["Pedidos"], LARGURAS)
    return caminho
