"""Agendamento com a biblioteca schedule: o robô confere a pasta de entrada sozinho.

Para produção, o README mostra o mesmo agendamento com Cron (Linux) e com o
Agendador de Tarefas (Windows), que sobrevivem a reinicializações da máquina.
"""

from __future__ import annotations

import time

from .config import Config
from .pipeline import executar
from .registro import configurar, log


def agendar(cfg: Config, horario: str | None = None, max_execucoes: int | None = None) -> None:
    try:
        import schedule
    except ImportError:
        configurar(cfg.logs)
        log.error("Biblioteca 'schedule' não instalada. Rode: python -m pip install -r requirements.txt")
        return

    contador = {"total": 0}

    def tarefa():
        executar(cfg)  # executar() nunca levanta exceção: uma falha não derruba o agendador
        contador["total"] += 1

    if horario:
        schedule.every().day.at(horario).do(tarefa)
        descricao = f"todos os dias às {horario}"
    else:
        schedule.every(cfg.intervalo_minutos).minutes.do(tarefa)
        descricao = f"a cada {cfg.intervalo_minutos} minuto(s)"

    configurar(cfg.logs)
    log.info("Agendador ligado: %s. Ctrl+C para parar.", descricao)
    if not horario:
        tarefa()  # primeira execução imediata
    try:
        while max_execucoes is None or contador["total"] < max_execucoes:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Agendador desligado pelo operador.")
    finally:
        schedule.clear()
