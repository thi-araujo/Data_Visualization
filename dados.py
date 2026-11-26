"""Leitura de planilhas, classificação das colunas e conjunto de dados de exemplo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

MAX_CATEGORIAS = 12  # colunas numéricas com poucos valores distintos viram categorias (ex.: códigos)


class ErroDados(Exception):
    pass


@dataclass
class Colunas:
    numericas: list[str]
    categoricas: list[str]


def carregar(caminho: str | Path) -> pd.DataFrame:
    caminho = Path(caminho)
    sufixo = caminho.suffix.lower()
    try:
        if sufixo in (".xlsx", ".xlsm", ".xls"):
            df = pd.read_excel(caminho)
        elif sufixo in (".csv", ".txt"):
            df = _ler_csv(caminho)
        else:
            raise ErroDados(f"formato não suportado: {sufixo or 'sem extensão'} (use .csv ou .xlsx)")
    except (OSError, ValueError, ImportError) as erro:
        raise ErroDados(f"não foi possível ler {caminho.name}: {erro}") from erro
    return limpar(df)


def _ler_csv(caminho: Path) -> pd.DataFrame:
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            amostra = caminho.read_text(encoding=codificacao)[:4096]
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ErroDados("codificação do CSV não reconhecida")
    primeira = amostra.splitlines()[0] if amostra else ""
    separador = ";" if primeira.count(";") > primeira.count(",") else ","
    decimal = "," if separador == ";" else "."
    return pd.read_csv(caminho, sep=separador, decimal=decimal, encoding=codificacao)


def limpar(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ErroDados("a planilha está vazia")
    # Colunas de índice salvas sem querer ("Unnamed: 0") e colunas totalmente vazias.
    descartar = [c for c in df.columns if str(c).startswith("Unnamed:") or df[c].isna().all()]
    df = df.drop(columns=descartar)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def classificar(df: pd.DataFrame) -> Colunas:
    numericas, categoricas = [], []
    for coluna in df.columns:
        serie = df[coluna]
        if pd.api.types.is_bool_dtype(serie):
            categoricas.append(coluna)
        elif pd.api.types.is_numeric_dtype(serie):
            numericas.append(coluna)
            if serie.nunique(dropna=True) <= MAX_CATEGORIAS:
                categoricas.append(coluna)  # pode servir como número ou como categoria
        elif serie.nunique(dropna=True) <= 60:
            categoricas.append(coluna)
    return Colunas(numericas, categoricas)


def resumo(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por coluna: tipo, valores distintos, vazios, mínimo, média e máximo."""
    linhas = []
    for coluna in df.columns:
        serie = df[coluna]
        numerica = pd.api.types.is_numeric_dtype(serie) and not pd.api.types.is_bool_dtype(serie)
        linhas.append({
            "coluna": coluna,
            "tipo": "número" if numerica else "texto",
            "distintos": int(serie.nunique(dropna=True)),
            "vazios": int(serie.isna().sum()),
            "mínimo": serie.min() if numerica else None,
            "média": serie.mean() if numerica else None,
            "máximo": serie.max() if numerica else None,
        })
    return pd.DataFrame(linhas)


def gerar_exemplo(linhas: int = 1500, semente: int = 7) -> pd.DataFrame:
    """Clientes de cartão de crédito FICTÍCIOS, gerados por código.

    Imita a estrutura da planilha usada na aula original (perfil, limite,
    fatura, pagamento e atrasos), com relações plausíveis entre as colunas
    para os gráficos terem o que mostrar. Não representa pessoas reais.
    """
    rng = np.random.default_rng(semente)
    idade = rng.integers(21, 70, linhas)
    sexo = rng.choice(["Feminino", "Masculino"], linhas, p=[0.55, 0.45])
    estado_civil = rng.choice(["Solteiro(a)", "Casado(a)", "Outro"], linhas, p=[0.5, 0.42, 0.08])
    escolaridade = rng.choice(["Ensino médio", "Graduação", "Pós-graduação"], linhas, p=[0.3, 0.5, 0.2])
    bonus_estudo = pd.Series(escolaridade).map({"Ensino médio": 0.8, "Graduação": 1.0, "Pós-graduação": 1.35})
    renda = np.round(rng.lognormal(8.1, 0.45, linhas) * bonus_estudo.to_numpy() * (1 + (idade - 21) / 120), -1)
    limite = np.round(np.clip(renda * rng.uniform(1.5, 4.0, linhas), 1000, 60000), -2)
    uso = np.clip(rng.beta(2, 3, linhas) + (idade < 30) * 0.08, 0.02, 1.0)
    fatura = np.round(limite * uso, 2)
    risco = 1 / (1 + np.exp(-(-2.6 + 2.4 * uso - (renda / 10000) + (idade < 30) * 0.5)))
    atrasos = rng.binomial(6, np.clip(risco * 0.9, 0, 1))
    pagamento = np.round(fatura * np.clip(rng.normal(1 - atrasos * 0.12, 0.15), 0.05, 1.2), 2)
    inadimplente = np.where(rng.random(linhas) < np.clip(risco + atrasos * 0.05, 0, 0.95), "Sim", "Não")
    return pd.DataFrame({
        "idade": idade, "sexo": sexo, "estado_civil": estado_civil, "escolaridade": escolaridade,
        "renda_mensal": renda, "limite_credito": limite, "fatura_media": fatura,
        "pagamento_medio": pagamento, "meses_em_atraso": atrasos, "inadimplente": inadimplente,
    })
