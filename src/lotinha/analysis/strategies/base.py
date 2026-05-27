"""Interface base para estratégias de predição."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from lotinha.core.domain import PredictionResult


class BaseStrategy(ABC):
    """Interface que todas as estratégias de predição devem implementar."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador único da estratégia."""

    @abstractmethod
    def predict(self, df: pd.DataFrame, n: int = 23) -> PredictionResult:
        """Prediz os n números mais prováveis para o próximo sorteio.

        Args:
            df: Histórico de sorteios ordenado cronologicamente,
                com coluna ``numeros`` (list[int]).
            n: Quantidade de números a retornar (17..23).

        Returns:
            PredictionResult com números preditos, scores 1..25 e confiança.

        Raises:
            InsufficientDataError: Histórico insuficiente para a estratégia.
            ValueError: Se n estiver fora de [17, 23].
        """

    def _validate_n(self, n: int) -> None:
        if not (17 <= n <= 23):
            raise ValueError(f"n deve estar entre 17 e 23, recebido {n}")

    def reset(self) -> None:  # noqa: B027
        """Reinicia o estado interno da estratégia (no-op para estratégias sem estado)."""

    def _confidence(self, scores: pd.Series, top_indices: list[int]) -> float:
        """Confiança = média normalizada dos scores dos números preditos."""
        s_min, s_max = float(scores.min()), float(scores.max())
        if s_max <= s_min:
            return 0.5
        top_scores = scores[top_indices]
        normalized = (top_scores - s_min) / (s_max - s_min)
        return float(normalized.mean())


def normalize(series: pd.Series) -> pd.Series:
    """Normaliza uma Series para o intervalo [0, 1]."""
    s_min, s_max = float(series.min()), float(series.max())
    if s_max <= s_min:
        return pd.Series(0.5, index=series.index, dtype=np.float64)
    return (series - s_min) / (s_max - s_min)
