"""Observabilidade: saúde da máquina (psutil) e trava contra execução em dobro."""

from __future__ import annotations

import os
from pathlib import Path

import psutil

from .registro import log


def medir(pasta: Path) -> dict:
    disco = psutil.disk_usage(str(pasta))
    return {
        "cpu_pct": psutil.cpu_percent(interval=0.2),
        "memoria_pct": psutil.virtual_memory().percent,
        "memoria_robo_mb": round(psutil.Process().memory_info().rss / 1024 ** 2, 1),
        "disco_livre_mb": int(disco.free / 1024 ** 2),
    }


def ha_espaco(pasta: Path, minimo_mb: int) -> bool:
    livre = psutil.disk_usage(str(pasta)).free / 1024 ** 2
    if livre < minimo_mb:
        log.error("FALHA TRATADA | disco quase cheio (%.0f MB livres, mínimo %d MB). "
                  "Execução adiada para não gravar relatório pela metade.", livre, minimo_mb)
        return False
    return True


class Trava:
    """Impede duas execuções ao mesmo tempo (ex.: o agendador dispara antes de a anterior acabar)."""

    def __init__(self, caminho: Path):
        self.caminho = caminho
        self.minha = False

    def adquirir(self) -> bool:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        if self.caminho.exists():
            try:
                pid = int(self.caminho.read_text().strip())
            except (ValueError, OSError):
                pid = None
            if pid and pid != os.getpid() and psutil.pid_exists(pid):
                log.warning("FALHA TRATADA | já existe uma execução em andamento (PID %s). "
                            "Esta foi cancelada.", pid)
                return False
            log.warning("Trava antiga encontrada (execução anterior interrompida). Removida.")
        self.caminho.write_text(str(os.getpid()))
        self.minha = True
        return True

    def liberar(self) -> None:
        if self.minha:
            self.caminho.unlink(missing_ok=True)
            self.minha = False
