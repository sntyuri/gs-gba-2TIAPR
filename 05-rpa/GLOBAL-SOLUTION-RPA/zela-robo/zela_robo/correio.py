"""Tarefa 6 do processo: avisar cada órgão por e-mail, com a planilha em anexo.

Dois modos, escolhidos no .env (ZELA_EMAIL_MODO):
  arquivo  (padrão) grava cada mensagem como .eml em saida/<execução>/emails/.
           Não precisa de senha e permite conferir tudo antes de ligar o envio.
  smtp     envia de verdade (ex.: Gmail com senha de app). A senha vem só do .env.

Caminho seguro: se o envio falhar depois das tentativas, a mensagem é gravada
em emails/pendentes/ para reenvio manual, e o robô continua.
"""

from __future__ import annotations

import smtplib
import ssl
import time
from email.message import EmailMessage
from pathlib import Path

from .config import Config
from .registro import log

XLSX = ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def montar(remetente: str, destinatario: str, assunto: str, corpo: str,
           anexo: Path | None = None) -> EmailMessage:
    mensagem = EmailMessage()
    mensagem["From"] = remetente
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)
    if anexo is not None and anexo.exists():
        mensagem.add_attachment(anexo.read_bytes(), maintype=XLSX[0], subtype=XLSX[1],
                                filename=anexo.name)
    return mensagem


def _gravar(mensagem: EmailMessage, pasta: Path, nome: str) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.eml"
    caminho.write_bytes(mensagem.as_bytes())
    return caminho


def _enviar_smtp(cfg: Config, mensagens: list[EmailMessage]) -> None:
    contexto = ssl.create_default_context()
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_porta, timeout=20) as servidor:
        servidor.starttls(context=contexto)
        servidor.login(cfg.smtp_usuario, cfg.smtp_senha)
        for mensagem in mensagens:
            servidor.send_message(mensagem)


def entregar(cfg: Config, mensagens: dict[str, EmailMessage], pasta: Path,
             dormir=time.sleep) -> dict:
    """Entrega as mensagens ({nome: mensagem}). Devolve o que aconteceu."""
    resultado = {"modo": cfg.email_modo, "enviados": 0, "gravados": 0, "pendentes": 0, "falha": ""}
    if not mensagens:
        return resultado

    if cfg.email_modo != "smtp":
        for nome, mensagem in mensagens.items():
            _gravar(mensagem, pasta, nome)
        resultado["gravados"] = len(mensagens)
        log.info("E-mails gravados em arquivo (.eml): %d", len(mensagens))
        return resultado

    if not (cfg.smtp_usuario and cfg.smtp_senha):
        resultado["falha"] = "ZELA_SMTP_USUARIO ou ZELA_SMTP_SENHA não configurados no .env"
    else:
        if cfg.email_destino_teste:  # os órgãos são fictícios: em teste, tudo vai para um endereço só
            for mensagem in mensagens.values():
                mensagem.replace_header("To", cfg.email_destino_teste)
        for tentativa in range(1, cfg.smtp_tentativas + 1):
            try:
                _enviar_smtp(cfg, list(mensagens.values()))
                resultado["enviados"] = len(mensagens)
                log.info("E-mails enviados por SMTP: %d", len(mensagens))
                return resultado
            except (smtplib.SMTPException, OSError) as erro:
                resultado["falha"] = f"{type(erro).__name__}"
                if tentativa < cfg.smtp_tentativas:
                    espera = cfg.smtp_espera * 2 ** (tentativa - 1)
                    log.warning("Envio de e-mail falhou (%s), tentativa %d de %d. "
                                "Nova tentativa em %.0f s.", resultado["falha"], tentativa,
                                cfg.smtp_tentativas, espera)
                    dormir(espera)

    for nome, mensagem in mensagens.items():
        _gravar(mensagem, pasta / "pendentes", nome)
    resultado["pendentes"] = len(mensagens)
    log.error("FALHA TRATADA | e-mails não enviados (%s). %d mensagens gravadas em "
              "emails/pendentes para reenvio.", resultado["falha"], len(mensagens))
    return resultado
