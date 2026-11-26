"""Desenho dos gráficos com Matplotlib, seguindo regras de legibilidade:

- Cores categóricas numa ordem fixa, validada para daltonismo contra o fundo
  do aplicativo. A cor segue a categoria, nunca a posição.
- Dispersão aceita no máximo 3 cores (o limite em que todos os pares continuam
  distinguíveis); barras, linhas e caixas aceitam até 8. O que passar disso
  vira "Outros", em cinza.
- Correlação usa escala divergente azul ↔ vermelho com cinza no zero.
- Linhas de 2 px, grade discreta, um único eixo Y e legenda quando há 2+ séries.
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

matplotlib.rcParams["svg.fonttype"] = "none"

TEMA = {
    "fundo": "#1e293b",
    "texto": "#e2e8f0",
    "texto_suave": "#94a3b8",
    "grade": "#334155",
    "outros": "#64748b",
}
# Paleta categórica (modo escuro), validada contra o fundo #1e293b:
# todos os pares vizinhos passam no teste de daltonismo; os 3 primeiros passam em todos os pares.
CATEGORICAS = ["#338ced", "#e76624", "#00a888", "#d28e05", "#e24d8b", "#0aac23", "#9887ef", "#eb6263"]
LIMITE_DISPERSAO = 3
LIMITE_CATEGORIAS = 8
SEQUENCIAL = "#338ced"
DIVERGENTE = LinearSegmentedColormap.from_list("azul_cinza_vermelho", ["#1757ac", "#519ced", "#383838",
                                                                       "#eb6263", "#b3261e"])


class ErroGrafico(ValueError):
    pass


@dataclass(frozen=True)
class TipoGrafico:
    nome: str
    precisa_x: str | None   # "numerica", "categorica" ou None (não usa)
    precisa_y: str | None
    usa_cor: bool
    y_opcional: bool = False
    dica: str = ""


TIPOS = {
    "Dispersão": TipoGrafico("Dispersão", "numerica", "numerica", True,
                             dica="Relação entre duas medidas. Cor: até 3 grupos."),
    "Linha": TipoGrafico("Linha", "numerica", "numerica", True,
                         dica="Média de Y para cada valor de X, em ordem."),
    "Histograma": TipoGrafico("Histograma", "numerica", None, True,
                              dica="Distribuição de uma medida."),
    "Barras": TipoGrafico("Barras", "categorica", "numerica", False, y_opcional=True,
                          dica="Média de Y por categoria (sem Y: contagem)."),
    "Caixa (boxplot)": TipoGrafico("Caixa (boxplot)", "categorica", "numerica", False, y_opcional=False,
                                   dica="Mediana, quartis e valores atípicos de Y por grupo."),
    "Violino": TipoGrafico("Violino", "categorica", "numerica", False,
                           dica="Distribuição de Y por grupo (histograma + caixa)."),
    "Correlação": TipoGrafico("Correlação", None, None, False,
                              dica="Correlação entre todas as colunas numéricas."),
}


def novo_eixo(figura: Figure):
    figura.clear()
    figura.set_facecolor(TEMA["fundo"])
    eixo = figura.add_subplot(111)
    eixo.set_facecolor(TEMA["fundo"])
    for lado in ("top", "right"):
        eixo.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        eixo.spines[lado].set_color(TEMA["grade"])
    eixo.tick_params(colors=TEMA["texto_suave"], labelsize=9)
    eixo.grid(True, color=TEMA["grade"], linewidth=0.6, alpha=0.6)
    eixo.set_axisbelow(True)
    return eixo


def _titulos(eixo, titulo: str, x: str | None, y: str | None) -> None:
    eixo.set_title(titulo, color=TEMA["texto"], fontsize=13, fontweight="bold", loc="left", pad=12)
    if x:
        eixo.set_xlabel(x, color=TEMA["texto_suave"], fontsize=10)
    if y:
        eixo.set_ylabel(y, color=TEMA["texto_suave"], fontsize=10)


def _legenda(eixo, titulo: str | None = None) -> None:
    legenda = eixo.legend(title=titulo, frameon=False, fontsize=9, title_fontsize=9, labelcolor=TEMA["texto"])
    if legenda and legenda.get_title():
        legenda.get_title().set_color(TEMA["texto_suave"])


def agrupar_categorias(serie: pd.Series, limite: int) -> tuple[pd.Series, dict[str, str]]:
    """Mantém as `limite` categorias mais frequentes e junta o resto em "Outros".

    Devolve a série ajustada e o mapa categoria -> cor. A cor depende da posição
    da categoria em ordem alfabética entre as mantidas, então não muda quando o
    usuário filtra ou troca de gráfico.
    """
    texto = serie.astype(str).where(serie.notna(), "(vazio)")
    frequentes = texto.value_counts()
    if len(frequentes) > limite:
        manter = set(frequentes.index[:limite - 1])
        texto = texto.where(texto.isin(manter), "Outros")
    nomes = sorted(c for c in texto.unique() if c != "Outros")
    cores = {nome: CATEGORICAS[i] for i, nome in enumerate(nomes)}
    if "Outros" in set(texto):
        cores["Outros"] = TEMA["outros"]
    return texto, cores


def _numerica(df: pd.DataFrame, coluna: str) -> pd.Series:
    if coluna not in df.columns:
        raise ErroGrafico(f"coluna \"{coluna}\" não existe")
    serie = pd.to_numeric(df[coluna], errors="coerce")
    if serie.notna().sum() == 0:
        raise ErroGrafico(f"a coluna \"{coluna}\" não tem números")
    return serie


def desenhar(figura: Figure, df: pd.DataFrame, tipo: str, x: str | None = None, y: str | None = None,
             cor: str | None = None, titulo: str = "") -> str:
    """Desenha o gráfico e devolve uma frase curta descrevendo o que foi feito."""
    if tipo not in TIPOS:
        raise ErroGrafico(f"tipo de gráfico desconhecido: {tipo}")
    especificacao = TIPOS[tipo]
    if especificacao.precisa_x and not x:
        raise ErroGrafico("escolha a coluna do eixo X")
    if especificacao.precisa_y and not y and not especificacao.y_opcional:
        raise ErroGrafico("escolha a coluna do eixo Y")
    eixo = novo_eixo(figura)
    titulo = titulo or _titulo_padrao(tipo, x, y, cor)

    if tipo == "Dispersão":
        nota = _dispersao(eixo, df, x, y, cor)
    elif tipo == "Linha":
        nota = _linha(eixo, df, x, y, cor)
    elif tipo == "Histograma":
        nota = _histograma(eixo, df, x, cor)
    elif tipo == "Barras":
        nota = _barras(eixo, df, x, y)
    elif tipo in ("Caixa (boxplot)", "Violino"):
        nota = _distribuicao(eixo, df, x, y, violino=tipo == "Violino")
    else:
        nota = _correlacao(figura, eixo, df)
        x = y = None
    if tipo == "Barras":  # barras horizontais: categorias no eixo vertical
        _titulos(eixo, titulo, y or "Quantidade", x)
    elif tipo == "Correlação":
        _titulos(eixo, titulo, None, None)
    else:
        _titulos(eixo, titulo, x, y or ("Quantidade" if tipo == "Histograma" else None))
    figura.tight_layout()
    return nota


def _titulo_padrao(tipo, x, y, cor) -> str:
    if tipo == "Correlação":
        return "Correlação entre as colunas numéricas"
    if tipo == "Histograma":
        base = f"Distribuição de {x}"
    elif tipo == "Barras" and not y:
        base = f"Quantidade por {x}"
    elif tipo == "Barras":
        base = f"{y} médio(a) por {x}"
    elif tipo in ("Caixa (boxplot)", "Violino"):
        base = f"{y} por {x}" if x else f"Distribuição de {y}"
    else:
        base = f"{y} × {x}"
    return f"{base}, por {cor}" if cor else base


def _dispersao(eixo, df, x, y, cor) -> str:
    dados = pd.DataFrame({"x": _numerica(df, x), "y": _numerica(df, y)})
    if cor:
        dados["grupo"], cores = agrupar_categorias(df[cor], LIMITE_DISPERSAO)
    dados = dados.dropna(subset=["x", "y"])
    amostra = dados.sample(5000, random_state=1) if len(dados) > 5000 else dados
    if cor:
        for nome, cor_grupo in cores.items():
            parte = amostra[amostra["grupo"] == nome]
            eixo.scatter(parte["x"], parte["y"], s=36, color=cor_grupo, alpha=0.75, label=nome,
                         edgecolors=TEMA["fundo"], linewidths=0.6)
        _legenda(eixo, cor)
    else:
        eixo.scatter(amostra["x"], amostra["y"], s=36, color=SEQUENCIAL, alpha=0.7,
                     edgecolors=TEMA["fundo"], linewidths=0.6)
    extra = f" (amostra de 5000 de {len(dados)})" if len(dados) > 5000 else ""
    return f"{len(amostra)} pontos{extra}"


def _linha(eixo, df, x, y, cor) -> str:
    dados = pd.DataFrame({"x": _numerica(df, x), "y": _numerica(df, y)})
    grupos = {"": SEQUENCIAL}
    if cor:
        dados["grupo"], grupos = agrupar_categorias(df[cor], LIMITE_CATEGORIAS)
    else:
        dados["grupo"] = ""
    dados = dados.dropna(subset=["x", "y"])
    for nome, cor_grupo in grupos.items():
        serie = dados[dados["grupo"] == nome].groupby("x")["y"].mean().sort_index()
        eixo.plot(serie.index, serie.to_numpy(), color=cor_grupo, linewidth=2, label=nome or None)
    if cor:
        _legenda(eixo, cor)
    return f"média de {y} para {dados['x'].nunique()} valores de {x}"


def _histograma(eixo, df, x, cor) -> str:
    valores = _numerica(df, x)
    limites = np.histogram_bin_edges(valores.dropna(), bins="auto")
    if len(limites) > 41:
        limites = np.histogram_bin_edges(valores.dropna(), bins=40)
    if cor:
        grupos, cores = agrupar_categorias(df[cor], LIMITE_CATEGORIAS)
        for nome, cor_grupo in cores.items():
            eixo.hist(valores[grupos == nome].dropna(), bins=limites, histtype="step", linewidth=2,
                      color=cor_grupo, label=nome)
        _legenda(eixo, cor)
    else:
        eixo.hist(valores.dropna(), bins=limites, color=SEQUENCIAL, edgecolor=TEMA["fundo"], linewidth=1.5)
    return f"{valores.notna().sum()} valores em {len(limites) - 1} faixas"


def _barras(eixo, df, x, y) -> str:
    grupos, _ = agrupar_categorias(df[x], 15)
    if y:
        valores = _numerica(df, y).groupby(grupos).mean()
        nota = f"média de {y}"
    else:
        valores = grupos.value_counts()
        nota = "contagem de linhas"
    valores = valores.sort_values()
    rotulos = [str(i) for i in valores.index]
    cores = [TEMA["outros"] if r == "Outros" else SEQUENCIAL for r in rotulos]
    barras = eixo.barh(rotulos, valores.to_numpy(), color=cores, height=0.7, edgecolor=TEMA["fundo"], linewidth=2)
    eixo.grid(axis="y", visible=False)
    eixo.bar_label(barras, labels=[_curto(v) for v in valores.to_numpy()], padding=4, color=TEMA["texto"],
                   fontsize=9)
    eixo.set_xmargin(0.12)
    return f"{nota} em {len(valores)} categorias"


def _distribuicao(eixo, df, x, y, violino: bool) -> str:
    valores = _numerica(df, y)
    if x:
        grupos, _ = agrupar_categorias(df[x], LIMITE_CATEGORIAS)
        nomes = sorted(grupos.unique(), key=lambda n: (n == "Outros", n))
        series = [valores[grupos == n].dropna().to_numpy() for n in nomes]
    else:
        nomes, series = [y], [valores.dropna().to_numpy()]
    nomes_validos = [n for n, s in zip(nomes, series) if len(s)]
    series = [s for s in series if len(s)]
    posicoes = np.arange(1, len(series) + 1)
    if violino:
        partes = eixo.violinplot(series, positions=posicoes, showmedians=True, widths=0.8)
        for corpo in partes["bodies"]:
            corpo.set_facecolor(SEQUENCIAL)
            corpo.set_edgecolor(SEQUENCIAL)
            corpo.set_alpha(0.45)
        for chave in ("cmedians", "cmins", "cmaxes", "cbars"):
            partes[chave].set_color(TEMA["texto"])
            partes[chave].set_linewidth(1.5)
    else:
        caixas = eixo.boxplot(series, positions=posicoes, widths=0.55, patch_artist=True,
                              flierprops={"marker": "o", "markersize": 4, "markerfacecolor": TEMA["texto_suave"],
                                          "markeredgecolor": "none", "alpha": 0.5})
        for caixa in caixas["boxes"]:
            caixa.set(facecolor=SEQUENCIAL, alpha=0.55, edgecolor=SEQUENCIAL, linewidth=1.5)
        for chave in ("medians", "whiskers", "caps"):
            for linha in caixas[chave]:
                linha.set(color=TEMA["texto"], linewidth=1.5)
    eixo.set_xticks(posicoes, nomes_validos)
    eixo.grid(axis="x", visible=False)
    return f"{sum(len(s) for s in series)} valores em {len(series)} grupo(s)"


def _correlacao(figura, eixo, df) -> str:
    numericas = df.select_dtypes("number")
    numericas = numericas.loc[:, numericas.nunique() > 1]
    if numericas.shape[1] < 2:
        raise ErroGrafico("são necessárias pelo menos duas colunas numéricas")
    matriz = numericas.corr()
    n = len(matriz)
    imagem = eixo.imshow(matriz.to_numpy(), cmap=DIVERGENTE, vmin=-1, vmax=1)
    eixo.grid(False)
    for lado in ("left", "bottom"):
        eixo.spines[lado].set_visible(False)
    eixo.set_xticks(range(n), matriz.columns, rotation=40, ha="right")
    eixo.set_yticks(range(n), matriz.columns)
    if n <= 14:
        for i in range(n):
            for j in range(n):
                valor = matriz.iat[i, j]
                eixo.text(j, i, f"{valor:.2f}".replace(".", ","), ha="center", va="center", fontsize=8,
                          color="#ffffff" if abs(valor) > 0.45 else TEMA["texto"])
    barra = figura.colorbar(imagem, ax=eixo, fraction=0.04, pad=0.03)
    barra.outline.set_visible(False)
    barra.ax.tick_params(colors=TEMA["texto_suave"], labelsize=8)
    return f"{n} colunas numéricas · azul = correlação negativa, vermelho = positiva"


def _curto(valor: float) -> str:
    if abs(valor) >= 1e6:
        return f"{valor / 1e6:.1f} mi".replace(".", ",")
    if abs(valor) >= 1e4:
        return f"{valor / 1e3:.1f} mil".replace(".", ",")
    if float(valor).is_integer():
        return f"{int(valor)}"
    return f"{valor:.2f}".replace(".", ",")


def desenhar_funcoes(figura: Figure, curvas: list[tuple[str, np.ndarray, np.ndarray]], titulo: str = "") -> None:
    eixo = novo_eixo(figura)
    for i, (rotulo, x, y) in enumerate(curvas):
        eixo.plot(x, y, color=CATEGORICAS[i % LIMITE_CATEGORIAS], linewidth=2, label=f"f{i + 1}(x) = {rotulo}")
    eixo.axhline(0, color=TEMA["texto_suave"], linewidth=0.8)
    eixo.axvline(0, color=TEMA["texto_suave"], linewidth=0.8)
    if len(curvas) > 1:
        _legenda(eixo)
    elif curvas:
        titulo = titulo or f"f(x) = {curvas[0][0]}"
    _titulos(eixo, titulo or "Funções", "x", "f(x)")
    figura.tight_layout()
