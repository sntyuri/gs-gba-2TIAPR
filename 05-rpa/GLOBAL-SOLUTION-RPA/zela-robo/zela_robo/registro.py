"""Log de auditoria: cada decisão e cada falha ficam em logs/robo.log e no terminal.

O log nunca recebe o texto do relato, só protocolo, categoria e motivo.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMATO = "%(asctime)s | %(levelname)-7s | %(message)s"


def configurar(pasta_logs: Path) -> logging.Logger:
    log = logging.getLogger("zela")
    log.setLevel(logging.INFO)
    for antigo in list(log.handlers):  # reexecuções no mesmo processo (agendador, testes)
        log.removeHandler(antigo)
        antigo.close()
    pasta_logs.mkdir(parents=True, exist_ok=True)
    arquivo = RotatingFileHandler(pasta_logs / "robo.log", maxBytes=1_000_000,
                                  backupCount=3, encoding="utf-8")
    tela = logging.StreamHandler(sys.stdout)
    for destino in (arquivo, tela):
        destino.setFormatter(logging.Formatter(FORMATO, "%Y-%m-%d %H:%M:%S"))
        log.addHandler(destino)
    log.propagate = False
    return log


log = logging.getLogger("zela")
