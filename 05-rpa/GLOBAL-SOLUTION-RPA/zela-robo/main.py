"""Zela Robô: triagem e encaminhamento automático de pedidos de zeladoria urbana.

Ponto de entrada único do protótipo.

    python main.py --demo      copia os arquivos de exemplo para entrada/ e executa
    python main.py             processa o que estiver em entrada/
    python main.py --agendar   executa a cada N minutos (ZELA_INTERVALO_MIN, padrão 15)
    python main.py --agendar --horario 08:00
    python main.py --avaliar   mede a IA no conjunto de teste rotulado
"""

from __future__ import annotations

import argparse
import shutil
import sys

from zela_robo.config import Config


def copiar_exemplos(cfg: Config) -> int:
    cfg.criar_pastas()
    arquivos = [p for p in sorted(cfg.exemplos.iterdir()) if p.is_file()]
    for arquivo in arquivos:
        shutil.copy2(arquivo, cfg.entrada / arquivo.name)
    return len(arquivos)


def main(argumentos: list[str] | None = None) -> int:
    leitor = argparse.ArgumentParser(description="Zela Robô: triagem automática de zeladoria urbana")
    leitor.add_argument("--demo", action="store_true", help="usa os arquivos de dados/exemplos")
    leitor.add_argument("--agendar", action="store_true", help="mantém o robô rodando no intervalo configurado")
    leitor.add_argument("--horario", help="com --agendar: executa todos os dias neste horário (HH:MM)")
    leitor.add_argument("--avaliar", action="store_true", help="mede a IA no conjunto de teste rotulado")
    opcoes = leitor.parse_args(argumentos)
    for fluxo in (sys.stdout, sys.stderr):  # acentos no terminal do Windows
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")
    cfg = Config()

    if opcoes.avaliar:
        from scripts.avaliar import avaliar
        return avaliar(cfg)

    if opcoes.demo:
        print(f"{copiar_exemplos(cfg)} arquivos de exemplo copiados para {cfg.entrada}")

    if opcoes.agendar:
        from zela_robo.agendador import agendar
        agendar(cfg, opcoes.horario)
        return 0

    from zela_robo.pipeline import executar
    resumo = executar(cfg)
    if resumo.get("pasta_saida"):
        print(f"\nResultado em: {resumo['pasta_saida']}")
    return 0 if resumo["status"].startswith("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
