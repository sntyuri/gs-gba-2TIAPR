"""Mede a IA no conjunto de teste rotulado (dados/teste_rotulado.csv).

    python main.py --avaliar

O teste foi escrito à mão, separado do treino. O script compara o modelo com o
classificador por regras do aplicativo, mostra o efeito do limiar de confiança
e lista cada erro. Grava evidencias/avaliacao.md e evidencias/avaliacao_erros.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from zela_robo import catalogo  # noqa: E402
from zela_robo.config import Config  # noqa: E402
from zela_robo.ia import Triagem, treinar  # noqa: E402

LIMIARES = (0.0, 0.30, 0.40, 0.45, 0.50, 0.60, 0.70)


def _por_limiar(teste: pd.DataFrame, limiar: float) -> dict:
    """O robô só encaminha sozinho o que tem confiança >= limiar e não é 'outros'."""
    automatico = (teste["confianca"] >= limiar) & (teste["previsto"] != "outros")
    certos = automatico & teste["acerto"]
    errados = automatico & ~teste["acerto"]
    return {
        "Limiar": f"{limiar:.0%}",
        "Encaminhados sozinho": int(automatico.sum()),
        "% automatizado": f"{automatico.mean():.0%}",
        "Encaminhados certo": int(certos.sum()),
        "Encaminhados errado": int(errados.sum()),
        "Acerto no automático": f"{certos.sum() / max(1, automatico.sum()):.1%}",
        "Para revisão humana": int((~automatico).sum()),
    }


def avaliar(cfg: Config | None = None) -> int:
    cfg = cfg or Config()
    teste = pd.read_csv(RAIZ / "dados" / "teste_rotulado.csv", dtype=str)
    treino = pd.read_csv(cfg.treino, dtype=str)
    repetidos = set(teste["relato"].map(catalogo.normalizar)) & set(treino["relato"].map(catalogo.normalizar))

    modelo = treinar(cfg.treino)
    probabilidades = modelo.predict_proba(teste["relato"])
    teste["previsto"] = modelo.classes_[probabilidades.argmax(axis=1)]
    teste["confianca"] = probabilidades.max(axis=1)
    teste["acerto"] = teste["previsto"] == teste["categoria"]

    regras = [Triagem._por_regras(texto) for texto in teste["relato"]]
    teste["regras"] = [d.categoria for d in regras]
    acerto_regras = (teste["regras"] == teste["categoria"]).mean()
    acerto_modelo = teste["acerto"].mean()

    limiares = pd.DataFrame([_por_limiar(teste, limiar) for limiar in LIMIARES])
    relatorio = classification_report(teste["categoria"], teste["previsto"], digits=2, zero_division=0)
    rotulos = list(catalogo.IDS_CATEGORIAS)
    matriz = pd.DataFrame(confusion_matrix(teste["categoria"], teste["previsto"], labels=rotulos),
                          index=rotulos, columns=rotulos)
    erros = teste[~teste["acerto"]].sort_values("confianca", ascending=False)
    erros_csv = erros[["relato", "categoria", "previsto", "confianca"]].rename(
        columns={"categoria": "correto"}).assign(confianca=lambda d: d["confianca"].round(2))

    no_limiar = _por_limiar(teste, cfg.limiar_confianca)
    linhas = [
        "# Avaliação da IA de triagem",
        "",
        f"- Treino: {len(treino)} relatos sintéticos gerados por combinação de frases (`dados/treino.csv`).",
        f"- Teste: {len(teste)} relatos escritos à mão, {teste['categoria'].nunique()} categorias "
        f"(`dados/teste_rotulado.csv`). Relatos do teste que também estão no treino: {len(repetidos)}.",
        "- Modelo: TF-IDF (palavras e pedaços de palavra) + regressão logística, scikit-learn.",
        "",
        "## Resultado geral",
        "",
        "| Classificador | Acertos | Acurácia |",
        "| --- | --- | --- |",
        f"| Modelo de ML (robô) | {int(teste['acerto'].sum())} de {len(teste)} | {acerto_modelo:.1%} |",
        f"| Regras do aplicativo (referência) | {int((teste['regras'] == teste['categoria']).sum())} de {len(teste)} | {acerto_regras:.1%} |",
        "",
        f"## Efeito do limiar de confiança (em uso: {cfg.limiar_confianca:.0%})",
        "",
        "Abaixo do limiar, ou quando a categoria é \"outros\", o pedido vai para revisão humana.",
        "",
        limiares.to_markdown(index=False),
        "",
        f"Com o limiar de {cfg.limiar_confianca:.0%}: o robô encaminha sozinho {no_limiar['Encaminhados sozinho']} "
        f"de {len(teste)} pedidos ({no_limiar['% automatizado']}), acerta {no_limiar['Encaminhados certo']} e erra "
        f"{no_limiar['Encaminhados errado']}; {no_limiar['Para revisão humana']} vão para uma pessoa.",
        "",
        "## Precisão e recall por categoria (sem limiar)",
        "",
        "```", relatorio.rstrip(), "```",
        "",
        "## Matriz de confusão (linha = correto, coluna = previsto)",
        "",
        matriz.to_markdown(),
        "",
        f"## Erros ({len(erros)})",
        "",
        "Lista completa em `avaliacao_erros.csv`.",
        "",
        erros_csv.to_markdown(index=False),
        "",
    ]
    pasta = RAIZ / "evidencias"
    pasta.mkdir(exist_ok=True)
    (pasta / "avaliacao.md").write_text("\n".join(linhas), encoding="utf-8")
    erros_csv.to_csv(pasta / "avaliacao_erros.csv", index=False)

    print(f"Modelo de ML: {acerto_modelo:.1%} ({int(teste['acerto'].sum())}/{len(teste)}) | "
          f"Regras: {acerto_regras:.1%}")
    print(limiares.to_string(index=False))
    print(f"\nDetalhes em {pasta / 'avaliacao.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(avaliar())
