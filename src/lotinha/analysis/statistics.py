"""Funções estatísticas core para análise de sorteios da Lotinha."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import hypergeom

_NUMEROS = list(range(1, 26))  # 1..25
_N = 25  # total de números possíveis


def frequencia(df: pd.DataFrame, janela: int | None = None) -> pd.Series:
    """Frequência relativa de cada número nos últimos `janela` sorteios.

    Args:
        df: DataFrame com coluna ``numeros`` (list[int] por linha).
        janela: Número de sorteios mais recentes a considerar.
            ``None`` usa todos; ``0`` retorna zeros.

    Returns:
        Series indexada 1..25 com frequências relativas (0.0 a 1.0).
    """
    if df.empty or janela == 0:
        return pd.Series(0.0, index=_NUMEROS, dtype=np.float64)

    data = df.tail(janela) if janela is not None else df
    n = len(data)
    if n == 0:
        return pd.Series(0.0, index=_NUMEROS, dtype=np.float64)

    contagens = np.zeros(_N, dtype=np.float64)
    for nums in data["numeros"]:
        for num in nums:
            if 1 <= num <= _N:
                contagens[num - 1] += 1

    return pd.Series(contagens / n, index=_NUMEROS)


def atraso(df: pd.DataFrame) -> pd.Series:
    """Número de sorteios desde a última aparição de cada número.

    Args:
        df: DataFrame com coluna ``numeros``, ordenado cronologicamente.

    Returns:
        Series indexada 1..25 com atraso inteiro (0 = apareceu no último
        sorteio; igual ao total de sorteios = nunca apareceu).
    """
    n = len(df)
    if n == 0:
        return pd.Series(0, index=_NUMEROS, dtype=np.int64)

    # Última posição (índice 0-based) em que cada número apareceu (-1 = nunca)
    ultima_pos = np.full(_N, -1, dtype=np.int64)
    for idx, nums in enumerate(df["numeros"]):
        for num in nums:
            if 1 <= num <= _N:
                ultima_pos[num - 1] = idx

    atrasos = np.where(ultima_pos >= 0, n - 1 - ultima_pos, n)
    return pd.Series(atrasos, index=_NUMEROS, dtype=np.int64)


def co_ocorrencias(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz de co-ocorrência entre os 25 números.

    Args:
        df: DataFrame com coluna ``numeros``.

    Returns:
        DataFrame 25x25 (index e columns = 1..25) onde ``[i, j]`` é o
        número de sorteios em que os números ``i`` e ``j`` apareceram juntos.
        A diagonal contém a contagem individual de cada número.
    """
    acum = np.zeros((_N, _N), dtype=np.int64)

    for nums in df["numeros"]:
        indicador = np.zeros(_N, dtype=np.int64)
        for num in nums:
            if 1 <= num <= _N:
                indicador[num - 1] = 1
        acum += np.outer(indicador, indicador)

    return pd.DataFrame(acum, index=_NUMEROS, columns=_NUMEROS)


def valor_esperado(
    n_preditos: int,
    n_sorteados: int,
    n_total: int,
    premios: dict[int, float],
    custo: float,
) -> float:
    """Valor esperado analítico de uma aposta usando distribuição hipergeométrica.

    Assume que todos os números têm probabilidade igual de serem sorteados.

    Args:
        n_preditos: Quantidade de números apostados (ex: 22).
        n_sorteados: Quantidade de números sorteados por extração (ex: 15).
        n_total: Total de números no universo do jogo (ex: 25).
        premios: Mapeamento ``{acertos: valor_premio}``.
        custo: Custo da aposta.

    Returns:
        Valor esperado (positivo = lucrativo em média estatística).
    """
    ev = 0.0
    for acertos, premio in premios.items():
        p = float(hypergeom.pmf(acertos, n_total, n_sorteados, n_preditos))
        ev += p * premio
    return ev - custo
