"""Avaliador seguro de funções matemáticas de x, para desenhar gráficos.

Como na calculadora científica deste portfólio, não usa eval(): a expressão
vira uma árvore sintática e só números, x, constantes, operadores e funções
da lista permitida são aceitos. O cálculo é feito com NumPy sobre um vetor de
valores de x.

Exemplos: sen(pi*x)   x^2 - 3x + 2   exp(-x)*cos(2pi x)   raiz(x)   abs(x)
"""

from __future__ import annotations

import ast
import operator
import re

import numpy as np


class ErroFuncao(ValueError):
    pass


FUNCOES = {
    "sen": np.sin, "sin": np.sin, "cos": np.cos, "tan": np.tan, "tg": np.tan,
    "exp": np.exp, "ln": np.log, "log": np.log10, "raiz": np.sqrt, "sqrt": np.sqrt, "abs": np.abs,
}
CONSTANTES = {"pi": np.pi, "e": np.e}
OPERADORES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.Pow: operator.pow}


_NOMES = sorted([*FUNCOES, *CONSTANTES, "x"], key=len, reverse=True)


def _separar_nomes(achado: re.Match) -> str:
    """Quebra sequências de letras em nomes conhecidos: "xsen" -> "x*sen", "pix" -> "pi*x"."""
    palavra, partes = achado.group(), []
    while palavra:
        nome = next((n for n in _NOMES if palavra.startswith(n)), None)
        if nome is None:
            return achado.group()  # nome desconhecido: deixa como está para dar erro claro depois
        partes.append(nome)
        palavra = palavra[len(nome):]
    return "*".join(partes)


def normalizar(texto: str) -> str:
    t = texto.strip().lower().replace("π", "pi").replace("^", "**").replace("×", "*").replace("−", "-")
    t = t.replace("√", "raiz").replace(",", ".")
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"[a-z]+", _separar_nomes, t)
    t = re.sub(r"(\d|\))(?=[a-z(])", r"\1*", t)       # 2x, 2pi, 3(x+1), )(
    t = re.sub(r"\b(x|pi|e)(?=[(\d])", r"\1*", t)     # x(…), pi(…), x2
    t = re.sub(r"\)(?=\d)", r")*", t)
    return t


def compilar(texto: str) -> ast.Expression:
    if not texto.strip():
        raise ErroFuncao("função vazia")
    try:
        arvore = ast.parse(normalizar(texto), mode="eval")
    except SyntaxError:
        raise ErroFuncao(f"\"{texto}\" está incompleta ou mal escrita") from None
    for no in ast.walk(arvore):
        permitido = isinstance(no, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.USub, ast.UAdd, ast.Load,
                                    *OPERADORES)) \
            or (isinstance(no, ast.Constant) and isinstance(no.value, (int, float)) and not isinstance(no.value, bool)) \
            or (isinstance(no, ast.Name) and (no.id == "x" or no.id in CONSTANTES or no.id in FUNCOES)) \
            or (isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in FUNCOES
                and len(no.args) == 1 and not no.keywords)
        if not permitido:
            nome = getattr(no, "id", None)
            raise ErroFuncao(f"\"{nome}\" não é permitido" if nome else f"operação não permitida em \"{texto}\"")
    return arvore


def avaliar(texto: str, x: np.ndarray) -> np.ndarray:
    """Calcula a função para cada valor de x. Pontos fora do domínio viram NaN (lacuna no gráfico)."""
    arvore = compilar(texto)

    def calcular(no):
        if isinstance(no, ast.Expression):
            return calcular(no.body)
        if isinstance(no, ast.Constant):
            return float(no.value)
        if isinstance(no, ast.Name):
            return x if no.id == "x" else CONSTANTES[no.id]
        if isinstance(no, ast.UnaryOp):
            valor = calcular(no.operand)
            return -valor if isinstance(no.op, ast.USub) else valor
        if isinstance(no, ast.BinOp):
            direita = calcular(no.right)
            if isinstance(no.op, ast.Pow) and np.max(np.abs(direita)) > 1000:
                raise ErroFuncao("expoente grande demais")
            return OPERADORES[type(no.op)](calcular(no.left), direita)
        return FUNCOES[no.func.id](calcular(no.args[0]))

    with np.errstate(all="ignore"):
        resultado = np.broadcast_to(np.asarray(calcular(arvore), dtype=float), x.shape).copy()
    resultado[~np.isfinite(resultado)] = np.nan
    return resultado
