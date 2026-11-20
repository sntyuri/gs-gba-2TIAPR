"""Testes automatizados do Zela Robô.  Rodar com:  python -m pytest -q

Cobrem o fluxo completo e, principalmente, os casos de falha: arquivo corrompido,
coluna ausente, linha inválida, API fora do ar, SMTP fora do ar, modelo ausente,
execução em dobro e reprocessamento do mesmo arquivo.
"""

from __future__ import annotations

import json
import os
import shutil
import smtplib
import sys
from pathlib import Path

import openpyxl
import pytest
import requests

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from zela_robo import catalogo, clima, correio, ingestao, monitor, privacidade  # noqa: E402
from zela_robo.config import Config  # noqa: E402
from zela_robo.ia import Triagem, priorizar  # noqa: E402
from zela_robo.pipeline import executar  # noqa: E402


class RespostaFalsa:
    def __init__(self, chuva):
        self.chuva = chuva

    def raise_for_status(self):
        pass

    def json(self):
        return {"daily": {"precipitation_sum": [self.chuva]}}


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    """Robô apontado para uma pasta temporária, com a API de clima respondendo 'sem chuva'."""
    monkeypatch.setattr(clima.requests, "get", lambda *a, **k: RespostaFalsa(0.0))
    config = Config(base=tmp_path, clima_espera=0, smtp_espera=0, email_modo="arquivo")
    config.criar_pastas()
    shutil.copy(RAIZ / "modelos" / "triagem.joblib", config.modelo) if (RAIZ / "modelos" / "triagem.joblib").exists() else None
    return config


def copiar_exemplos(config, *nomes):
    for nome in nomes or [p.name for p in config.exemplos.iterdir()]:
        shutil.copy(config.exemplos / nome, config.entrada / nome)


def abrir_triagem(resumo):
    pasta = Path(resumo["pasta_saida"])
    return openpyxl.load_workbook(next(pasta.glob("triagem_*.xlsx")))


# ---------- proteção de dados ----------

def test_remove_cpf_telefone_e_email():
    texto, total = privacidade.mascarar(
        "Poste apagado. Meu CPF é 529.982.247-25, telefone (11) 91234-5678, e-mail ana@teste.example")
    assert total == 3
    assert "529" not in texto and "91234" not in texto and "@" not in texto


def test_nao_confunde_numero_de_casa_ano_ou_linha_de_onibus():
    texto, total = privacidade.mascarar("Buraco em frente ao número 1234, desde 2024, linha 5010")
    assert total == 0 and "1234" in texto


# ---------- regras e prioridade ----------

@pytest.mark.parametrize("relato, categoria, prioridade", [
    ("Tem um fio solto caído na calçada soltando faísca perto da creche", "iluminacao", "urgente"),
    ("Buraco enorme na avenida principal", "vias", "media"),
    ("Tem lixo e entulho acumulados no terreno baldio da esquina.", "residuos", "baixa"),
    ("Semáforo apagado no cruzamento da avenida, quase teve acidente", "transito", "urgente"),
])
def test_regras_iguais_as_do_aplicativo(relato, categoria, prioridade):
    assert catalogo.pontuar_categorias(relato)[0][0] == categoria
    assert priorizar(categoria, relato, chuva_forte=False)["prioridade"] == prioridade


def test_chuva_forte_sobe_a_prioridade_de_drenagem_mas_nao_de_barulho():
    relato = "A boca de lobo da esquina está entupida"
    assert priorizar("agua", relato, False)["prioridade"] == "media"
    com_chuva = priorizar("agua", relato, True)
    assert com_chuva["prioridade"] == "alta" and "chuva forte" in com_chuva["motivos"]
    assert priorizar("barulho", "Som alto no bar", True)["prioridade"] == "baixa"


# ---------- entrada de arquivos ----------

def test_arquivos_ruins_vao_para_a_quarentena_e_os_bons_sao_lidos(cfg):
    copiar_exemplos(cfg)
    tabela, lidos, falhas = ingestao.coletar(cfg.entrada, cfg.quarentena)
    assert {p.name for p in lidos} == {"meus-dados-zela.json", "central_156.csv", "balcao_atendimento.xlsx"}
    assert {f["arquivo"] for f in falhas} == {"exportacao_corrompida.json", "planilha_sem_relato.csv", "anotacoes.txt"}
    assert len(list(cfg.quarentena.iterdir())) == 3
    assert len(tabela) == 27


def test_linhas_invalidas_sao_rejeitadas_com_motivo(cfg):
    copiar_exemplos(cfg, "central_156.csv")
    tabela, _, _ = ingestao.coletar(cfg.entrada, cfg.quarentena)
    validas, rejeitadas = ingestao.validar(tabela, 15)
    assert len(validas) == 10
    assert sorted(rejeitadas["motivo"]) == ["relato com menos de 15 caracteres", "relato vazio", "repetida no mesmo lote"]


def test_dados_da_conta_do_cidadao_nao_entram_no_robo(cfg):
    copiar_exemplos(cfg, "meus-dados-zela.json")
    tabela, _, _ = ingestao.coletar(cfg.entrada, cfg.quarentena)
    assert "Fictícia" not in tabela.to_csv() and "teste.example" not in tabela.to_csv()


# ---------- fluxo completo ----------

def test_fluxo_completo_gera_planilha_emails_e_respostas(cfg):
    copiar_exemplos(cfg)
    resumo = executar(cfg)
    assert resumo["status"] == "ok"
    assert (resumo["novos"], resumo["rejeitados"]) == (24, 3)
    assert resumo["encaminhados"] + resumo["revisao_humana"] == 24
    assert resumo["revisao_humana"] >= 1
    pasta = Path(resumo["pasta_saida"])
    planilha = abrir_triagem(resumo)
    assert planilha.sheetnames == ["Resumo", "Encaminhados", "Revisão humana", "Rejeitadas", "Execução"]
    assert planilha["Encaminhados"].max_row - 1 == resumo["encaminhados"]
    assert (pasta / "emails" / "central_revisao.eml").exists()
    assert len(json.loads((pasta / "respostas_cidadao.json").read_text(encoding="utf-8"))) == 24
    assert not any(cfg.entrada.iterdir())  # entrada esvaziada: arquivos arquivados ou em quarentena


def test_nenhum_dado_pessoal_chega_a_planilha_email_ou_log(cfg):
    copiar_exemplos(cfg)
    resumo = executar(cfg)
    assert resumo["dados_pessoais_removidos"] == 3
    proibidos = ["529.982.247-25", "91234-5678", "joao.teste@email.example"]
    textos = [(cfg.logs / "robo.log").read_text(encoding="utf-8")]
    for aba in abrir_triagem(resumo):
        textos += [str(c) for linha in aba.iter_rows(values_only=True) for c in linha]
    textos += [p.read_text(encoding="utf-8", errors="ignore") for p in Path(resumo["pasta_saida"]).rglob("*.json")]
    assert not any(dado in texto for dado in proibidos for texto in textos)


def test_rodar_duas_vezes_nao_duplica_encaminhamento(cfg):
    copiar_exemplos(cfg, "meus-dados-zela.json")
    primeira = executar(cfg)
    copiar_exemplos(cfg, "meus-dados-zela.json")
    segunda = executar(cfg)
    assert primeira["novos"] == 8
    assert (segunda["novos"], segunda["ja_processados"]) == (0, 8)
    assert len([p for p in cfg.saida.iterdir() if p.is_dir()]) == 1  # nenhum e-mail novo


def test_pasta_vazia_nao_e_erro(cfg):
    assert executar(cfg)["status"] == "ok: nada a processar"


# ---------- falhas de serviços externos ----------

def test_api_de_clima_fora_do_ar_tenta_de_novo_e_segue(cfg, monkeypatch):
    chamadas = []

    def fora_do_ar(*a, **k):
        chamadas.append(k.get("timeout"))
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(clima.requests, "get", fora_do_ar)
    copiar_exemplos(cfg, "meus-dados-zela.json")
    resumo = executar(cfg)
    assert len(chamadas) == 3 and all(t == cfg.clima_timeout for t in chamadas)
    assert resumo["status"] == "ok" and resumo["novos"] == 8
    assert any(f["onde"] == "API de previsão do tempo" for f in resumo["falhas"])


def test_api_de_clima_com_resposta_invalida_e_tratada(cfg, monkeypatch):
    monkeypatch.setattr(clima.requests, "get", lambda *a, **k: RespostaFalsa(None))
    assert clima.consultar(cfg).disponivel is False


def test_chuva_forte_e_usada_no_fluxo(cfg, monkeypatch):
    monkeypatch.setattr(clima.requests, "get", lambda *a, **k: RespostaFalsa(42.0))
    copiar_exemplos(cfg, "meus-dados-zela.json")
    resumo = executar(cfg)
    assert resumo["clima"].startswith("42.0 mm")
    linhas = list(abrir_triagem(resumo)["Encaminhados"].iter_rows(values_only=True))
    assert any("chuva forte" in str(linha[8]) for linha in linhas)


def test_smtp_fora_do_ar_grava_emails_pendentes(cfg, monkeypatch):
    def falhar(*a, **k):
        raise smtplib.SMTPServerDisconnected("servidor fora do ar")

    monkeypatch.setattr(correio, "_enviar_smtp", falhar)
    cfg.email_modo, cfg.smtp_usuario, cfg.smtp_senha = "smtp", "robo@teste.example", "senha-de-teste"
    copiar_exemplos(cfg, "meus-dados-zela.json")
    resumo = executar(cfg)
    assert resumo["status"] == "ok"
    pendentes = list((Path(resumo["pasta_saida"]) / "emails" / "pendentes").glob("*.eml"))
    assert len(pendentes) >= 1
    assert any(f["onde"] == "envio de e-mail" for f in resumo["falhas"])


def test_smtp_sem_senha_configurada_nao_tenta_enviar(cfg):
    cfg.email_modo = "smtp"
    mensagem = correio.montar("a@teste.example", "b@teste.example", "assunto", "corpo")
    resultado = correio.entregar(cfg, {"teste": mensagem}, cfg.saida / "emails")
    assert resultado["pendentes"] == 1 and "não configurados" in resultado["falha"]


def test_sem_modelo_e_sem_treino_usa_as_regras(cfg):
    cfg.modelo.unlink(missing_ok=True)
    cfg.treino = cfg.base / "nao_existe.csv"
    triagem = Triagem(cfg.modelo, cfg.treino)
    assert triagem.modelo is None
    assert triagem.classificar(["Buraco enorme no asfalto da avenida"])[0].categoria == "vias"
    assert triagem.classificar(["Preciso de ajuda com uma coisa"])[0].categoria == "outros"
    copiar_exemplos(cfg, "meus-dados-zela.json")
    resumo = executar(cfg)
    assert resumo["status"] == "ok" and resumo["motor_ia"] == "zela-triagem-regras-v1"


def test_modelo_salvo_corrompido_e_treinado_de_novo(cfg):
    cfg.modelo.write_bytes(b"isto nao e um modelo")
    os.utime(cfg.modelo, None)
    assert Triagem(cfg.modelo, cfg.treino).modelo is not None


def test_erro_ao_gravar_planilha_nao_marca_pedidos_como_tratados(cfg, monkeypatch):
    from zela_robo import relatorio

    def disco_cheio(*a, **k):
        raise PermissionError("planilha aberta em outro programa")

    monkeypatch.setattr(relatorio, "gravar_triagem", disco_cheio)
    copiar_exemplos(cfg, "meus-dados-zela.json")
    resumo = executar(cfg)
    assert resumo["status"].startswith("erro")
    assert (cfg.entrada / "meus-dados-zela.json").exists()  # continua na entrada
    monkeypatch.undo()
    monkeypatch.setattr(clima.requests, "get", lambda *a, **k: RespostaFalsa(0.0))
    assert executar(cfg)["novos"] == 8  # a próxima execução processa normalmente


def test_execucao_em_dobro_e_bloqueada(cfg):
    cfg.trava.write_text(str(os.getppid()))  # simula outro robô em execução
    assert executar(cfg)["status"].startswith("cancelada")
    cfg.trava.write_text("999999999")  # trava deixada por execução interrompida
    assert executar(cfg)["status"].startswith("ok")


def test_relato_que_parece_formula_nao_e_executado_no_excel(cfg):
    (cfg.entrada / "ataque.csv").write_text(
        'relato;bairro\n=cmd|calc!A1 buraco enorme no asfalto da rua;Centro\n',
        encoding="utf-8")
    resumo = executar(cfg)
    celulas = [str(c) for aba in abrir_triagem(resumo) for linha in aba.iter_rows(values_only=True) for c in linha]
    assert any(c.startswith("'=cmd") for c in celulas)
    assert not any(c.startswith("=cmd") for c in celulas)


def test_trava_e_liberada(cfg):
    trava = monitor.Trava(cfg.trava)
    assert trava.adquirir() and cfg.trava.exists()
    trava.liberar()
    assert not cfg.trava.exists()
