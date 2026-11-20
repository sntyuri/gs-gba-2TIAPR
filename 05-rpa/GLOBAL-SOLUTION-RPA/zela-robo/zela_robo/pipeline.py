"""Orquestração: o processo de triagem da central, tarefa por tarefa.

    1 Coletar  2 Validar  3 Proteger dados  4 Consultar clima  5 Classificar (IA)
    6 Priorizar  7 Gerar planilhas  8 Avisar órgãos  9 Registrar e arquivar

Cada tarefa é cronometrada (tempo de ciclo) e tem a sua falha tratada. Se as
planilhas não puderem ser gravadas, nada é marcado como processado: os arquivos
continuam na entrada e a próxima execução tenta de novo.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import catalogo, clima, correio, ingestao, monitor, privacidade, relatorio
from .config import Config
from .estado import Estado
from .ia import Triagem, priorizar
from .registro import configurar, log

REMETENTE = "Zela Robô <robo@prefeitura.example>"


class _Cronometro:
    def __init__(self):
        self.etapas: list[dict] = []

    @contextmanager
    def tarefa(self, nome: str):
        inicio = time.perf_counter()
        registro = {"Tarefa": nome, "Responsável": "robô", "Duração (s)": 0.0}
        try:
            yield registro
        finally:
            registro["Duração (s)"] = round(time.perf_counter() - inicio, 3)
            self.etapas.append(registro)


def _triar(validas: pd.DataFrame, triagem: Triagem, cfg: Config, chuva_forte: bool) -> pd.DataFrame:
    dados = validas.copy()
    limpos = [privacidade.mascarar(texto) for texto in dados["relato"]]
    dados["relato"] = [texto for texto, _ in limpos]
    dados["dados_removidos"] = [total for _, total in limpos]
    dados["referencia"] = [privacidade.mascarar(texto)[0] for texto in dados["referencia"]]

    decisoes = triagem.classificar(dados["relato"].tolist())
    dados["categoria"] = [d.categoria for d in decisoes]
    dados["confianca"] = [d.confianca for d in decisoes]
    dados["segunda"] = [d.segunda for d in decisoes]
    dados["motor"] = [d.motor for d in decisoes]

    prioridades = [priorizar(cat, texto, chuva_forte)
                   for cat, texto in zip(dados["categoria"], dados["relato"])]
    for campo in ("prioridade", "pontos", "emergencia", "prazo_dias", "motivos"):
        dados[campo] = [p[campo] for p in prioridades]

    def motivo_revisao(linha) -> str:
        if linha["categoria"] == "outros":
            return "assunto não reconhecido pela IA"
        if linha["confianca"] < cfg.limiar_confianca:
            return f"confiança abaixo de {cfg.limiar_confianca:.0%}"
        return ""

    dados["motivo_revisao"] = dados.apply(motivo_revisao, axis=1) if len(dados) else ""
    dados["revisao"] = dados["motivo_revisao"] != ""

    def nome(cid): return catalogo.buscar_categoria(cid).nome
    dados["categoria_nome"] = dados["categoria"].map(nome)
    dados["segunda_nome"] = dados["segunda"].map(nome)
    dados["orgao"] = dados["categoria"].map(lambda c: catalogo.buscar_categoria(c).orgao)
    dados["destino"] = [catalogo.CENTRAL.orgao if revisao else orgao
                        for revisao, orgao in zip(dados["revisao"], dados["orgao"])]
    dados["prioridade_rotulo"] = dados["prioridade"].map(catalogo.ROTULO_PRIORIDADE)
    dados["confianca_pct"] = (dados["confianca"] * 100).round(0).astype(int)
    dados["categoria_correta"] = ""
    dados["ordem"] = dados["prioridade"].map(catalogo.ORDEM_PRIORIDADE)
    return dados.sort_values(["ordem", "prazo_dias"]).drop(columns="ordem").reset_index(drop=True)


def _resposta_cidadao(linha: dict) -> str:
    prazo = "até 1 dia útil" if linha["prazo_dias"] == 1 else f"até {linha['prazo_dias']} dias úteis"
    rotulo = linha["prioridade_rotulo"].lower()
    if linha["revisao"]:
        texto = ("Recebemos o seu pedido. Para não encaminhar para o lugar errado, uma pessoa da "
                 f"Central de Atendimento vai ler o seu relato e direcionar. Previsão de resposta: {prazo}.")
    else:
        texto = (f"Recebemos o seu pedido sobre {linha['categoria_nome'].lower()}. Ele foi encaminhado "
                 f"para {linha['orgao']}, com prioridade {rotulo} ({linha['motivos']}). "
                 f"Previsão de resposta: {prazo}.")
    if linha["emergencia"]:
        texto += " Se houver risco imediato, ligue 193 (Bombeiros) ou 199 (Defesa Civil)."
    return texto


def _mensagens(dados: pd.DataFrame, pasta: Path, execucao: str) -> dict:
    """Uma mensagem por órgão, com a planilha dele em anexo, e uma para a fila de revisão."""
    mensagens = {}
    encaminhados = dados[~dados["revisao"]]
    for orgao, pedidos in encaminhados.groupby("orgao", sort=True):
        categoria = catalogo.buscar_categoria(pedidos["categoria"].iloc[0])
        anexo = relatorio.gravar_orgao(pasta / f"pedidos_{categoria.id}_{execucao}.xlsx", pedidos)
        urgentes = int((pedidos["prioridade"] == "urgente").sum())
        assunto = f"[Zela] {len(pedidos)} pedido(s) novo(s) para {orgao}"
        if urgentes:
            assunto = f"[Zela][URGENTE: {urgentes}] {len(pedidos)} pedido(s) novo(s) para {orgao}"
        linhas = [f"- {p['protocolo']} | {p['prioridade_rotulo']} | prazo {p['prazo_dias']} dia(s) útil(eis)"
                  f" | {p['bairro'] or 'bairro não informado'}" for p in pedidos.to_dict("records")]
        corpo = (f"Olá, equipe de {orgao}.\n\nA triagem automática da Zela encaminhou "
                 f"{len(pedidos)} pedido(s), em ordem de prioridade:\n\n" + "\n".join(linhas) +
                 "\n\nOs relatos completos (sem dados pessoais) e o motivo de cada prioridade estão "
                 "na planilha em anexo.\nSe algum pedido não for da sua área, avise a Central de Atendimento "
                 f"({catalogo.CENTRAL.email}).\n\nMensagem automática do Zela Robô.")
        mensagens[f"orgao_{categoria.id}"] = correio.montar(REMETENTE, categoria.email, assunto, corpo, anexo)

    fila = dados[dados["revisao"]]
    if len(fila):
        anexo = relatorio.gravar_orgao(pasta / f"revisao_humana_{execucao}.xlsx", fila,
                                       relatorio.COLUNAS_REVISAO)
        corpo = (f"Olá, Central de Atendimento.\n\n{len(fila)} pedido(s) precisam da leitura de uma "
                 "pessoa, porque a IA não teve segurança para encaminhar sozinha.\nNa planilha em anexo, "
                 "preencha a coluna \"Categoria correta\".\n\nMensagem automática do Zela Robô.")
        mensagens["central_revisao"] = correio.montar(
            REMETENTE, catalogo.CENTRAL.email,
            f"[Zela] {len(fila)} pedido(s) aguardando revisão humana", corpo, anexo)
    return mensagens


def executar(cfg: Config | None = None) -> dict:
    """Uma execução completa. Nunca levanta exceção: devolve o resumo com o status."""
    cfg = cfg or Config()
    cfg.criar_pastas()
    configurar(cfg.logs)
    inicio = datetime.now()
    execucao = f"{inicio:%Y%m%d-%H%M%S}"
    resumo = {"execucao": execucao, "inicio": inicio.isoformat(timespec="seconds"), "status": "ok",
              "lidos": 0, "novos": 0, "ja_processados": 0, "encaminhados": 0, "revisao_humana": 0,
              "rejeitados": 0, "falhas_tratadas": 0, "falhas": [], "duracao_s": 0.0}
    log.info("=== Execução %s iniciada ===", execucao)

    trava = monitor.Trava(cfg.trava)
    if not trava.adquirir():
        resumo["status"] = "cancelada: outra execução em andamento"
        return resumo
    estado = None
    try:
        if not monitor.ha_espaco(cfg.saida, cfg.disco_minimo_mb):
            resumo["status"] = "adiada: disco quase cheio"
            return resumo
        estado = Estado(cfg.estado_db)
        _processar(cfg, estado, execucao, resumo)
    except Exception as erro:  # última barreira: registra e encerra com segurança
        log.exception("ERRO NÃO PREVISTO | %s. Nada foi marcado como processado; "
                      "os arquivos continuam na pasta de entrada.", erro)
        resumo["status"] = f"erro: {type(erro).__name__}"
        resumo["falhas"].append({"onde": "execução", "motivo": f"{type(erro).__name__}: {erro}"})
    finally:
        resumo["duracao_s"] = round((datetime.now() - inicio).total_seconds(), 2)
        resumo["falhas_tratadas"] = len(resumo["falhas"])
        if resumo.get("pasta_saida"):  # relatório de execução, já com a duração final
            try:
                (Path(resumo["pasta_saida"]) / "relatorio_execucao.json").write_text(
                    json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError as erro:
                log.error("Não foi possível gravar o relatório de execução: %s", erro)
        if estado is not None:
            try:
                estado.registrar_execucao(resumo)
            finally:
                estado.fechar()
        trava.liberar()
        log.info("=== Execução %s encerrada: %s | lidos %d, novos %d, encaminhados %d, revisão %d, "
                 "rejeitados %d, falhas tratadas %d, %.1f s ===", execucao, resumo["status"],
                 resumo["lidos"], resumo["novos"], resumo["encaminhados"], resumo["revisao_humana"],
                 resumo["rejeitados"], resumo["falhas_tratadas"], resumo["duracao_s"])
    return resumo


def _processar(cfg: Config, estado: Estado, execucao: str, resumo: dict) -> None:
    relogio = _Cronometro()
    falhas = resumo["falhas"]

    with relogio.tarefa("1. Coletar arquivos da entrada") as t:
        tabela, arquivos, falhas_arquivo = ingestao.coletar(cfg.entrada, cfg.quarentena)
        falhas += [{"onde": f["arquivo"], "motivo": f"quarentena: {f['motivo']}"} for f in falhas_arquivo]
        resumo["lidos"] = len(tabela)
        t["Resultado"] = f"{len(arquivos)} arquivo(s), {len(tabela)} linha(s), {len(falhas_arquivo)} em quarentena"

    if not arquivos and not falhas_arquivo:
        log.info("Pasta de entrada vazia: nada a processar.")
        resumo["status"] = "ok: nada a processar"
        return

    with relogio.tarefa("2. Validar e descartar repetidos") as t:
        validas, rejeitadas = ingestao.validar(tabela, cfg.tamanho_minimo_relato)
        falhas += [{"onde": f"{r['arquivo']} ({r['protocolo'] or 'sem protocolo'})",
                    "motivo": f"linha rejeitada: {r['motivo']}"} for r in rejeitadas.to_dict("records")]
        antigos = estado.ja_processados(validas["chave"].tolist())
        novos = validas[~validas["chave"].isin(antigos)].reset_index(drop=True)
        resumo.update(rejeitados=len(rejeitadas), ja_processados=len(antigos), novos=len(novos))
        if antigos:
            log.info("Idempotência: %d pedido(s) já tratados em execuções anteriores foram ignorados.",
                     len(antigos))
        t["Resultado"] = f"{len(novos)} novo(s), {len(antigos)} já tratado(s), {len(rejeitadas)} rejeitado(s)"

    if novos.empty and rejeitadas.empty and not falhas_arquivo:
        log.info("Nenhum pedido novo nos arquivos recebidos: nada a encaminhar.")
        ingestao.arquivar(arquivos, cfg.processados)
        resumo["status"] = "ok: nenhum pedido novo"
        return

    with relogio.tarefa("3. Consultar previsão de chuva (API)") as t:
        previsao = clima.consultar(cfg) if len(novos) else clima.Previsao(False, detalhe="sem pedidos novos")
        if not previsao.disponivel and previsao.tentativas:
            falhas.append({"onde": "API de previsão do tempo", "motivo": previsao.detalhe})
        resumo["clima"] = (f"{previsao.chuva_mm:.1f} mm em 24 h" if previsao.disponivel
                           else f"indisponível ({previsao.detalhe})")
        t["Resultado"] = resumo["clima"]

    with relogio.tarefa("4. Remover dados pessoais, classificar (IA) e priorizar") as t:
        triagem = Triagem(cfg.modelo, cfg.treino)
        if triagem.modelo is None:
            falhas.append({"onde": "modelo de IA", "motivo": "indisponível: usado o classificador por regras"})
        dados = _triar(novos, triagem, cfg, previsao.chuva_forte)
        ano = datetime.now().year
        proximo = estado.proximo_protocolo(ano)
        for indice in dados.index[dados["protocolo"] == ""]:
            dados.at[indice, "protocolo"] = f"ZR-{ano}-{proximo:05d}"
            proximo += 1
        resumo.update(motor_ia=triagem.motor, limiar_confianca=cfg.limiar_confianca,
                      encaminhados=int((~dados["revisao"]).sum()) if len(dados) else 0,
                      revisao_humana=int(dados["revisao"].sum()) if len(dados) else 0,
                      urgentes=int((dados["prioridade"] == "urgente").sum()) if len(dados) else 0,
                      dados_pessoais_removidos=int(dados["dados_removidos"].sum()) if len(dados) else 0)
        for linha in dados.to_dict("records"):
            log.info("Decisão | %s | %s | confiança %d%% | prioridade %s | destino: %s%s",
                     linha["protocolo"], linha["categoria"], linha["confianca_pct"], linha["prioridade"],
                     linha["destino"], f" | REVISÃO HUMANA ({linha['motivo_revisao']})" if linha["revisao"] else "")
        t["Resultado"] = f"{resumo['encaminhados']} encaminhado(s), {resumo['revisao_humana']} para revisão humana"

    pasta = cfg.saida / execucao
    pasta.mkdir(parents=True, exist_ok=True)
    resumo.update(monitor.medir(cfg.saida))

    with relogio.tarefa("5. Avisar os órgãos por e-mail") as t:
        entrega = correio.entregar(cfg, _mensagens(dados, pasta, execucao), pasta / "emails")
        if entrega["pendentes"]:
            falhas.append({"onde": "envio de e-mail", "motivo": f"{entrega['falha']}: mensagens em emails/pendentes"})
        resumo["emails"] = (f"modo {entrega['modo']}: {entrega['enviados']} enviado(s), "
                            f"{entrega['gravados']} gravado(s) em arquivo, {entrega['pendentes']} pendente(s)")
        t["Resultado"] = resumo["emails"]

    with relogio.tarefa("6. Gerar planilha de triagem e respostas ao cidadão") as t:
        respostas = [{"protocolo": l["protocolo"], "status": "triagem" if l["revisao"] else "encaminhada",
                      "destino": l["destino"], "prioridade": l["prioridade"], "prazoDias": int(l["prazo_dias"]),
                      "mensagem": _resposta_cidadao(l)} for l in dados.to_dict("records")]
        (pasta / "respostas_cidadao.json").write_text(
            json.dumps(respostas, ensure_ascii=False, indent=2), encoding="utf-8")
        resumo["falhas_tratadas"] = len(falhas)
        t["Resultado"] = f"saida/{execucao}/triagem_{execucao}.xlsx"
        humana = {"Tarefa": "7. Conferir a fila de revisão", "Responsável": "pessoa da Central",
                  "Duração (s)": "", "Resultado": f"{resumo['revisao_humana']} pedido(s) aguardando"}
        # a duração desta tarefa só existe depois de gravar a planilha: ela fica no relatório JSON
        relatorio.gravar_triagem(pasta / f"triagem_{execucao}.xlsx", dados[~dados["revisao"]],
                                 dados[dados["revisao"]], rejeitadas, resumo,
                                 relogio.etapas + [{**t, "Duração (s)": ""}, humana])
    relogio.etapas.append(humana)

    # Só agora, com tudo gravado, os pedidos são marcados como tratados e os arquivos saem da entrada.
    estado.registrar(dados.to_dict("records"), execucao)
    ingestao.arquivar(arquivos, cfg.processados)
    resumo["etapas"] = relogio.etapas
    resumo["pasta_saida"] = str(pasta)
