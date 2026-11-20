"""Consumo de webservice: previsão de chuva do Open-Meteo (API pública, sem chave).

Com chuva forte prevista, bueiros entupidos e galhos em risco sobem na fila.
Só latitude e longitude da cidade são enviadas: nenhum dado de cidadão sai do robô.

Resiliência: timeout, novas tentativas com espera crescente e caminho seguro
(sem previsão, o robô segue com a prioridade normal e avisa no relatório).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from .config import Config
from .registro import log


@dataclass
class Previsao:
    disponivel: bool
    chuva_mm: float | None = None
    chuva_forte: bool = False
    tentativas: int = 0
    detalhe: str = ""


def consultar(cfg: Config, dormir=time.sleep) -> Previsao:
    if not cfg.clima_ativo:
        return Previsao(False, detalhe="consulta desligada na configuração")
    parametros = {
        "latitude": cfg.clima_latitude, "longitude": cfg.clima_longitude,
        "daily": "precipitation_sum", "forecast_days": 1, "timezone": "America/Sao_Paulo",
    }
    erro = ""
    for tentativa in range(1, cfg.clima_tentativas + 1):
        try:
            resposta = requests.get(cfg.clima_url, params=parametros, timeout=cfg.clima_timeout)
            resposta.raise_for_status()
            chuva = resposta.json()["daily"]["precipitation_sum"][0]
            if not isinstance(chuva, (int, float)) or chuva < 0:
                raise ValueError(f"valor de chuva inválido: {chuva!r}")
            forte = chuva >= cfg.clima_chuva_forte_mm
            log.info("Previsão do tempo: %.1f mm de chuva em 24 h (%s)", chuva,
                     "chuva forte" if forte else "sem chuva forte")
            return Previsao(True, float(chuva), forte, tentativa)
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as falha:
            erro = f"{type(falha).__name__}"
            if tentativa < cfg.clima_tentativas:
                espera = cfg.clima_espera * 2 ** (tentativa - 1)
                log.warning("Previsão do tempo falhou (%s), tentativa %d de %d. "
                            "Nova tentativa em %.0f s.", erro, tentativa,
                            cfg.clima_tentativas, espera)
                dormir(espera)
    log.error("FALHA TRATADA | previsão do tempo indisponível após %d tentativas (%s). "
              "Seguindo sem o ajuste de chuva.", cfg.clima_tentativas, erro)
    return Previsao(False, tentativas=cfg.clima_tentativas,
                    detalhe=f"API indisponível ({erro})")
