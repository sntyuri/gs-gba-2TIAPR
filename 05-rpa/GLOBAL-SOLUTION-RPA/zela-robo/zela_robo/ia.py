"""Tarefa 3 do processo: a decisão que não cabe em regra fixa.

- Categoria: modelo de aprendizado de máquina (TF-IDF + regressão logística,
  scikit-learn) treinado com relatos sintéticos rotulados (dados/treino.csv).
- Confiança: probabilidade da categoria vencedora. Abaixo do limiar, o robô não
  encaminha: manda para a fila de revisão humana.
- Prioridade: regras explicáveis (as mesmas do aplicativo), somadas à previsão de chuva.

Caminho seguro: se o modelo não puder ser carregado nem treinado, o robô usa o
classificador por regras do aplicativo e registra isso no log.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from . import catalogo
from .registro import log

VERSAO_MODELO = "zela-triagem-ml-v1"
VERSAO_REGRAS = "zela-triagem-regras-v1"


def criar_modelo() -> Pipeline:
    atributos = FeatureUnion([
        ("palavras", TfidfVectorizer(preprocessor=catalogo.normalizar, ngram_range=(1, 2),
                                     sublinear_tf=True, min_df=1)),
        # pedaços de palavra: aguenta erro de digitação ("onibuz", "semafaro")
        ("pedacos", TfidfVectorizer(preprocessor=catalogo.normalizar, analyzer="char_wb",
                                    ngram_range=(3, 5), sublinear_tf=True, min_df=2)),
    ])
    return Pipeline([("atributos", atributos),
                     ("classificador", LogisticRegression(C=10, max_iter=2000))])


def treinar(caminho_treino: Path) -> Pipeline:
    dados = pd.read_csv(caminho_treino, dtype=str).dropna(subset=["relato", "categoria"])
    desconhecidas = set(dados["categoria"]) - set(catalogo.IDS_CATEGORIAS)
    if desconhecidas:
        raise ValueError(f"categorias desconhecidas no treino: {sorted(desconhecidas)}")
    return criar_modelo().fit(dados["relato"], dados["categoria"])


@dataclass
class Decisao:
    categoria: str
    confianca: float
    segunda: str
    motor: str


class Triagem:
    """Carrega (ou treina) o modelo uma vez e classifica lotes de relatos."""

    def __init__(self, caminho_modelo: Path, caminho_treino: Path):
        self.modelo = None
        self.motor = VERSAO_REGRAS
        try:
            self.modelo = self._carregar(caminho_modelo, caminho_treino)
            self.motor = VERSAO_MODELO
        except Exception as erro:  # qualquer problema com o modelo cai no caminho seguro
            log.error("FALHA TRATADA | modelo de IA indisponível (%s: %s). "
                      "Usando o classificador por regras.", type(erro).__name__, erro)

    @staticmethod
    def _carregar(caminho_modelo: Path, caminho_treino: Path) -> Pipeline:
        if caminho_modelo.exists():
            # só aproveita o modelo salvo se ele for mais novo que os dados de treino
            if not caminho_treino.exists() or caminho_modelo.stat().st_mtime >= caminho_treino.stat().st_mtime:
                try:
                    return joblib.load(caminho_modelo)
                except Exception as erro:
                    log.warning("Modelo salvo ilegível (%s). Treinando de novo.", type(erro).__name__)
        modelo = treinar(caminho_treino)
        caminho_modelo.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(modelo, caminho_modelo)
        log.info("Modelo treinado com %s e salvo em %s", caminho_treino.name, caminho_modelo.name)
        return modelo

    def classificar(self, relatos: list[str]) -> list[Decisao]:
        if not relatos:
            return []
        if self.modelo is None:
            return [self._por_regras(texto) for texto in relatos]
        classes = list(self.modelo.classes_)
        decisoes = []
        for probabilidades in self.modelo.predict_proba(relatos):
            ordem = probabilidades.argsort()[::-1]
            decisoes.append(Decisao(classes[ordem[0]], float(probabilidades[ordem[0]]),
                                    classes[ordem[1]], VERSAO_MODELO))
        return decisoes

    @staticmethod
    def _por_regras(texto: str) -> Decisao:
        (primeira, pontos1), (segunda, pontos2) = catalogo.pontuar_categorias(texto)[:2]
        if pontos1 < 2:
            return Decisao("outros", 0.20, primeira, VERSAO_REGRAS)
        confianca = min(97, max(30, 40 + 10 * (pontos1 - pontos2) + 5 * min(pontos1, 6))) / 100
        return Decisao(primeira, confianca, segunda, VERSAO_REGRAS)


def priorizar(categoria_id: str, relato: str, chuva_forte: bool) -> dict:
    """Prioridade, prazo e a explicação em linguagem simples."""
    categoria = catalogo.buscar_categoria(categoria_id)
    sinais = catalogo.detectar_sinais(relato)
    motivos = [motivo for _, motivo, _ in sinais]
    extra = 0
    if chuva_forte and categoria.id in catalogo.CATEGORIAS_SENSIVEIS_A_CHUVA:
        extra = 2
        motivos.append("há previsão de chuva forte nas próximas 24 horas")
    nivel, pontos, ha_risco = catalogo.definir_prioridade(categoria, sinais, extra)
    return {
        "prioridade": nivel,
        "pontos": pontos,
        "emergencia": ha_risco,
        "prazo_dias": catalogo.calcular_prazo(categoria, nivel),
        "motivos": "; ".join(motivos) or "sem sinais de risco imediato no relato",
    }
