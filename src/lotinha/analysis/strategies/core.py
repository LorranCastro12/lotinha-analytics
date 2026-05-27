"""Estratégias de predição baseadas em frequência, atraso e Markov."""

from __future__ import annotations

import numpy as np
import pandas as pd

from lotinha.analysis.statistics import atraso, frequencia
from lotinha.analysis.strategies.base import BaseStrategy
from lotinha.core.domain import PredictionResult
from lotinha.core.exceptions import InsufficientDataError

_NUMEROS = list(range(1, 26))


class FrequenciaStrategy(BaseStrategy):
    """Prediz números com maior frequência histórica.

    Args:
        janela: Número de sorteios mais recentes a usar (None = todos).
    """

    def __init__(self, janela: int | None = None) -> None:
        self._janela = janela

    @property
    def name(self) -> str:
        return "frequencia"

    def predict(self, df: pd.DataFrame, n: int = 23) -> PredictionResult:
        self._validate_n(n)
        if len(df) == 0:
            raise InsufficientDataError(required=1, available=0)

        scores = frequencia(df, self._janela)
        top = list(scores.nlargest(n).index)
        conf = self._confidence(scores, top)

        return PredictionResult(
            numeros=sorted(top),
            scores=dict(zip(_NUMEROS, (float(v) for v in scores.values), strict=True)),
            confidence=conf,
            strategy_name=self.name,
            metadata={"janela": self._janela},
        )


class AtrasoStrategy(BaseStrategy):
    """Prediz números com maior número de sorteios sem aparecer."""

    @property
    def name(self) -> str:
        return "atraso"

    def predict(self, df: pd.DataFrame, n: int = 23) -> PredictionResult:
        self._validate_n(n)
        if len(df) == 0:
            raise InsufficientDataError(required=1, available=0)

        scores = atraso(df).astype(np.float64)
        top = list(scores.nlargest(n).index)
        conf = self._confidence(scores, top)

        return PredictionResult(
            numeros=sorted(top),
            scores=dict(zip(_NUMEROS, (float(v) for v in scores.values), strict=True)),
            confidence=conf,
            strategy_name=self.name,
            metadata={},
        )


class MarkovStrategy(BaseStrategy):
    """Prediz com base em transições de Markov entre sorteios consecutivos.

    Score de número j = soma das probabilidades de transição de cada
    número do último sorteio para j.
    """

    @property
    def name(self) -> str:
        return "markov"

    def predict(self, df: pd.DataFrame, n: int = 22) -> PredictionResult:
        self._validate_n(n)
        if len(df) < 2:
            raise InsufficientDataError(required=2, available=len(df))

        trans = self._build_transition(df)
        last = df["numeros"].iloc[-1]
        # soma das linhas dos números do último sorteio
        scores = trans.loc[[num for num in last if 1 <= num <= 25]].sum()
        top = list(scores.nlargest(n).index)
        conf = self._confidence(scores, top)

        return PredictionResult(
            numeros=sorted(top),
            scores=dict(zip(_NUMEROS, (float(v) for v in scores.values), strict=True)),
            confidence=conf,
            strategy_name=self.name,
            metadata={},
        )

    def _build_transition(self, df: pd.DataFrame) -> pd.DataFrame:
        """Matriz de transição P[i, j] = P(j em t+1 | i em t)."""
        n = 25
        trans = np.zeros((n, n), dtype=np.float64)
        rows = list(df["numeros"])

        for t in range(len(rows) - 1):
            cur = rows[t]
            nxt = rows[t + 1]
            for i in cur:
                if 1 <= i <= n:
                    for j in nxt:
                        if 1 <= j <= n:
                            trans[i - 1, j - 1] += 1.0

        row_sums = trans.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums == 0, 1.0, row_sums)
        trans = trans / row_sums

        return pd.DataFrame(trans, index=_NUMEROS, columns=_NUMEROS)
