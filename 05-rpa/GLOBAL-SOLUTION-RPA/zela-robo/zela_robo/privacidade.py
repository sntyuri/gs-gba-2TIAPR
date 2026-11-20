"""Proteção de dados (LGPD): remove CPF, telefone e e-mail do relato antes de
classificar, gravar em planilha ou enviar por e-mail (minimização de dados).

Mesma lógica do front-end (src/services/privacidade.js).
"""

from __future__ import annotations

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CPF_PONTUADO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-?\d{2}\b")
_ONZE_DIGITOS = re.compile(r"\b\d{11}\b")
_TELEFONE = re.compile(r"(?:\+?55[\s-]?)?(?:\(\d{2}\)|\b\d{2})?[\s-]?\b9?\d{4}[\s-]?\d{4}\b")


def cpf_valido(valor: str) -> bool:
    d = re.sub(r"\D", "", str(valor))
    if len(d) != 11 or d == d[0] * 11:
        return False

    def digito(tamanho: int) -> int:
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        resto = (soma * 10) % 11
        return 0 if resto == 10 else resto

    return digito(9) == int(d[9]) and digito(10) == int(d[10])


def mascarar(texto: object) -> tuple[str, int]:
    """Devolve (texto sem dados pessoais, quantidade de dados removidos)."""
    total = 0

    def trocar(rotulo: str):
        def _troca(_achado):
            nonlocal total
            total += 1
            return f"[{rotulo} removido]"
        return _troca

    saida = _EMAIL.sub(trocar("e-mail"), str(texto or ""))
    saida = _CPF_PONTUADO.sub(trocar("CPF"), saida)

    def onze(achado):
        # 11 dígitos seguidos: CPF ou celular com DDD. Decide pelo dígito verificador.
        return trocar("CPF" if cpf_valido(achado.group()) else "telefone")(achado)

    saida = _ONZE_DIGITOS.sub(onze, saida)

    def telefone(achado):
        nonlocal total
        trecho = achado.group()
        if len(re.sub(r"\D", "", trecho)) < 8:  # número de casa, ano, linha de ônibus
            return trecho
        total += 1
        espaco = re.match(r"\s*", trecho).group()
        return f"{espaco}[telefone removido]"

    saida = _TELEFONE.sub(telefone, saida)
    return saida, total
