"""Base de conhecimento da triagem: categorias, órgãos, prazos e sinais de prioridade.

É o mesmo catálogo do front-end da Zela (src/data/categorias.js e src/services/ia.js),
para que o cidadão e a central de atendimento vejam a mesma classificação.

Órgãos, prazos e e-mails são ILUSTRATIVOS: representam uma prefeitura fictícia.
O domínio "prefeitura.example" é reservado para exemplos e não entrega mensagens.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Categoria:
    id: str
    nome: str
    orgao: str
    email: str
    prazo_base: int
    prioridade_base: int
    termos: tuple = field(default_factory=tuple)


CATEGORIAS: tuple[Categoria, ...] = (
    Categoria(
        "iluminacao", "Iluminação e rede elétrica", "Departamento de Iluminação Pública",
        "iluminacao@prefeitura.example", 5, 1,
        (("iluminacao", 3), ("luz apagada", 3), ("luz queimada", 3), ("poste", 2),
         ("lampada", 2), ("luminaria", 2), ("sem luz", 2), ("fio", 2), ("fiacao", 2),
         ("faisca*", 2), ("apagad*", 1), ("escur*", 1)),
    ),
    Categoria(
        "vias", "Ruas e calçadas", "Secretaria de Obras e Vias Públicas",
        "obras@prefeitura.example", 10, 1,
        (("buraco", 3), ("cratera", 3), ("asfalto", 2), ("paviment*", 2), ("calcada", 2),
         ("meio fio", 3), ("afund*", 2), ("recape*", 2), ("paralelepipedo", 2),
         ("tampa solta", 2), ("desnivel", 1)),
    ),
    Categoria(
        "residuos", "Lixo e limpeza urbana", "Serviço de Limpeza Urbana",
        "limpeza@prefeitura.example", 4, 1,
        (("lixo", 3), ("entulho", 3), ("mato alto", 3), ("coleta", 2), ("descarte", 2),
         ("sujeira", 2), ("terreno baldio", 2), ("lixeira", 2), ("cacamba", 2),
         ("varricao", 2), ("capina", 2), ("moveis velhos", 2), ("sofa", 1)),
    ),
    Categoria(
        "agua", "Água, esgoto e drenagem", "Companhia de Saneamento e Drenagem",
        "saneamento@prefeitura.example", 3, 2,
        (("vazamento", 3), ("esgoto", 3), ("bueiro", 3), ("boca de lobo", 3), ("alag*", 3),
         ("enchente", 3), ("falta de agua", 3), ("sem agua", 3), ("cano", 2),
         ("agua suja", 2), ("entupid*", 2), ("transbord*", 2)),
    ),
    Categoria(
        "arvores", "Árvores e áreas verdes", "Secretaria do Verde e Meio Ambiente",
        "verde@prefeitura.example", 12, 1,
        (("arvore", 3), ("galho", 3), ("poda", 3), ("raiz", 2), ("tronco", 2),
         ("praca", 2), ("parque", 1), ("jardim", 1)),
    ),
    Categoria(
        "transito", "Trânsito e sinalização", "Departamento de Trânsito e Sinalização",
        "transito@prefeitura.example", 5, 2,
        (("semaforo", 3), ("sinal quebrado", 3), ("sinal apagado", 3), ("sinalizacao", 3),
         ("faixa de pedestre", 3), ("placa", 2), ("lombada", 2), ("quebra molas", 2),
         ("cruzamento", 2), ("transito", 1), ("farol", 1)),
    ),
    Categoria(
        "transporte", "Transporte público", "Secretaria de Mobilidade e Transportes",
        "transportes@prefeitura.example", 7, 1,
        (("onibus", 3), ("ponto de onibus", 2), ("motorista", 2), ("atras*", 2),
         ("terminal", 2), ("estacao", 2), ("trem", 2), ("linha", 1), ("lotad*", 1),
         ("tarifa", 1), ("bilhete", 1)),
    ),
    Categoria(
        "saude", "Saúde ambiental e zoonoses", "Vigilância em Saúde Ambiental",
        "vigilancia@prefeitura.example", 3, 2,
        (("dengue", 3), ("agua parada", 3), ("mosquito", 3), ("rato", 3), ("escorpi*", 3),
         ("animal morto", 3), ("barata", 2), ("caramujo", 2), ("carrapato", 2),
         ("foco", 1), ("pombo", 1)),
    ),
    Categoria(
        "acessibilidade", "Acessibilidade",
        "Secretaria da Pessoa com Deficiência e Acessibilidade",
        "acessibilidade@prefeitura.example", 10, 2,
        (("acessibilidade", 3), ("rampa", 3), ("cadeira de rodas", 3), ("piso tatil", 3),
         ("guia rebaixada", 3), ("cadeirante", 2), ("degrau", 2), ("elevador", 2),
         ("deficien*", 1)),
    ),
    Categoria(
        "barulho", "Barulho e perturbação do sossego", "Fiscalização de Posturas Municipais",
        "posturas@prefeitura.example", 7, 0,
        (("barulho", 3), ("som alto", 3), ("musica alta", 3), ("ruido", 2), ("baile", 2),
         ("paredao", 2), ("festa", 1)),
    ),
    Categoria(
        "outros", "Outros assuntos", "Central de Atendimento ao Cidadão",
        "central@prefeitura.example", 7, 1, (),
    ),
)

_POR_ID = {c.id: c for c in CATEGORIAS}
IDS_CATEGORIAS = tuple(_POR_ID)
CENTRAL = _POR_ID["outros"]


def buscar_categoria(categoria_id: str) -> Categoria:
    return _POR_ID.get(categoria_id, CENTRAL)


ROTULO_PRIORIDADE = {"urgente": "Urgente", "alta": "Alta", "media": "Média", "baixa": "Baixa"}
ORDEM_PRIORIDADE = {"urgente": 0, "alta": 1, "media": 2, "baixa": 3}

# Sinais que aumentam a prioridade: (id, motivo em linguagem simples, peso, termos).
SINAIS = (
    ("risco", "há sinais de risco imediato para as pessoas", 3,
     ("fio solto", "fio caido", "fio exposto", "choque", "curto circuito", "faisca*",
      "incendio", "fogo", "desab*", "desliz*", "explos*", "gas", "ferid*", "machuc*",
      "acidente", "afog*", "risco de vida", "risco de morte", "bueiro aberto",
      "sem tampa", "cratera", "caiu", "cair*", "queda")),
    ("vulneraveis", "afeta pessoas mais vulneráveis ou um local sensível", 2,
     ("crianca", "idos*", "escola", "creche", "hospital", "ubs", "posto de saude",
      "cadeirante", "deficien*", "gestante", "gravida", "bebe")),
    ("perigo", "o relato menciona perigo", 2,
     ("perig*", "risco", "assalt*", "inseguranca", "urgente", "urgencia", "emergencia")),
    ("alcance", "afeta muita gente ou a circulação", 1,
     ("rua inteira", "rua toda", "bairro inteiro", "bairro todo", "todo mundo",
      "varios moradores", "muitos moradores", "interdit*", "bloque*", "transito parado",
      "enorme", "gigante", "alag*", "enchente")),
    ("duracao", "o problema já dura bastante tempo ou se repete", 1,
     (re.compile(r"\bha (?:mais de )?(?:\w+ )?(?:dias|semanas?|mes|meses|anos?)\b"),
      re.compile(r"\bfaz (?:\w+ )?(?:tempo|dias|semanas|meses|anos)\b"),
      "toda noite", "todo dia", "todos os dias", "toda vez", "de novo", "novamente",
      "outra vez", "ja reclamei", "ja abri")),
)

# Categorias cujo risco cresce com chuva forte (usado com a previsão do tempo).
CATEGORIAS_SENSIVEIS_A_CHUVA = ("agua", "arvores")


def normalizar(texto: object) -> str:
    """Minúsculas e sem acento, para comparar o texto do cidadão com os termos."""
    sem_acento = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in sem_acento if unicodedata.category(c) != "Mn").lower()


def _padrao(termo) -> re.Pattern:
    if isinstance(termo, re.Pattern):
        return termo
    aceita_terminacao = termo.endswith("*")
    palavras = termo.rstrip("*").split(" ")
    partes = []
    for indice, palavra in enumerate(palavras):
        ultima = indice == len(palavras) - 1
        sufixo = r"\w*" if (ultima and aceita_terminacao) else r"(?:s|es)?"
        partes.append(re.escape(palavra) + sufixo)
    return re.compile(r"\b" + r"[\s-]+".join(partes) + r"\b")


_TERMOS = {c.id: tuple((_padrao(t), peso) for t, peso in c.termos) for c in CATEGORIAS}
_SINAIS = tuple((sid, motivo, peso, tuple(_padrao(t) for t in termos))
                for sid, motivo, peso, termos in SINAIS)


def pontuar_categorias(texto: str) -> list[tuple[str, int]]:
    """Classificador por regras (o mesmo do front-end). Devolve [(categoria, pontos)]."""
    normal = normalizar(texto)
    ranking = []
    for categoria in CATEGORIAS:
        if not categoria.termos:
            continue
        pontos = sum(peso for padrao, peso in _TERMOS[categoria.id] if padrao.search(normal))
        ranking.append((categoria.id, pontos))
    return sorted(ranking, key=lambda item: -item[1])


def detectar_sinais(texto: str) -> list[tuple[str, str, int]]:
    normal = normalizar(texto)
    return [(sid, motivo, peso) for sid, motivo, peso, padroes in _SINAIS
            if any(p.search(normal) for p in padroes)]


def definir_prioridade(categoria: Categoria, sinais, pontos_extra: int = 0) -> tuple[str, int, bool]:
    pontos = categoria.prioridade_base + sum(peso for _, _, peso in sinais) + pontos_extra
    ha_risco = any(sid == "risco" for sid, _, _ in sinais)
    if (ha_risco and pontos >= 5) or pontos >= 8:
        nivel = "urgente"
    elif ha_risco or pontos >= 4:
        nivel = "alta"
    elif pontos >= 2:
        nivel = "media"
    else:
        nivel = "baixa"
    return nivel, pontos, ha_risco


def calcular_prazo(categoria: Categoria, nivel: str) -> int:
    """Prazo estimado em dias úteis."""
    return {
        "urgente": 1,
        "alta": max(1, math.ceil(categoria.prazo_base * 0.4)),
        "media": categoria.prazo_base,
        "baixa": math.ceil(categoria.prazo_base * 1.5),
    }[nivel]
