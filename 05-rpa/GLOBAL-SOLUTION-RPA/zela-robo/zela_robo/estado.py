"""Memória do robô (SQLite): quais pedidos já foram tratados e o histórico de execuções.

É o que garante a idempotência: rodar duas vezes com o mesmo arquivo não gera
encaminhamento nem e-mail em dobro. O banco guarda só chave, categoria e datas,
nunca o texto do relato.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pedidos (
    chave TEXT PRIMARY KEY, protocolo TEXT, categoria TEXT, prioridade TEXT,
    destino TEXT, execucao TEXT, processado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS execucoes (
    execucao TEXT PRIMARY KEY, inicio TEXT, duracao_s REAL, lidos INTEGER,
    novos INTEGER, encaminhados INTEGER, revisao INTEGER, rejeitados INTEGER, falhas INTEGER
);
"""


class Estado:
    def __init__(self, caminho: Path):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.conexao = sqlite3.connect(caminho, timeout=10)
        self.conexao.executescript(ESQUEMA)

    def ja_processados(self, chaves: list[str]) -> set[str]:
        achados: set[str] = set()
        for inicio in range(0, len(chaves), 500):
            lote = chaves[inicio:inicio + 500]
            marcas = ",".join("?" * len(lote))
            with closing(self.conexao.execute(
                    f"SELECT chave FROM pedidos WHERE chave IN ({marcas})", lote)) as cursor:
                achados.update(linha[0] for linha in cursor)
        return achados

    def proximo_protocolo(self, ano: int) -> int:
        """Sequência para pedidos que chegaram sem protocolo (central e balcão)."""
        with closing(self.conexao.execute(
                "SELECT COUNT(*) FROM pedidos WHERE protocolo LIKE ?", (f"ZR-{ano}-%",))) as cursor:
            return cursor.fetchone()[0] + 1

    def registrar(self, pedidos: list[dict], execucao: str) -> None:
        with self.conexao:
            self.conexao.executemany(
                "INSERT OR IGNORE INTO pedidos (chave, protocolo, categoria, prioridade, destino, execucao) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(p["chave"], p["protocolo"], p["categoria"], p["prioridade"], p["destino"], execucao)
                 for p in pedidos])

    def registrar_execucao(self, resumo: dict) -> None:
        with self.conexao:
            self.conexao.execute(
                "INSERT OR REPLACE INTO execucoes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (resumo["execucao"], resumo["inicio"], resumo["duracao_s"], resumo["lidos"],
                 resumo["novos"], resumo["encaminhados"], resumo["revisao_humana"],
                 resumo["rejeitados"], resumo["falhas_tratadas"]))

    def fechar(self) -> None:
        self.conexao.close()
