"""Estratégia ensemble: combina múltiplas estratégias com pesos."""

from __future__ import annotations

import pandas as pd

from lotinha.analysis.strategies.base import BaseStrategy, normalize
from lotinha.core.domain import PredictionResult

_NUMEROS = list(range(1, 26))


class EnsembleStrategy(BaseStrategy):
    """Combina scores de várias estratégias com pesos ajustáveis.

    Os scores de cada estratégia são normalizados para [0, 1] antes de
    serem combinados, garantindo que escalas diferentes não dominem o
    resultado final.

    Args:
        strategies: Lista de estratégias a combinar.
        weights: Pesos de cada estratégia (padrão: todos iguais a 1.0).
    """

    def __init__(
        self,
        strategies: list[BaseStrategy],
        weights: list[float] | None = None,
    ) -> None:
        if not strategies:
            raise ValueError("EnsembleStrategy precisa de ao menos uma estratégia")
        self._strategies = strategies
        self._weights = weights if weights is not None else [1.0] * len(strategies)

    @property
    def name(self) -> str:
        return "ensemble"

    @property
    def weights(self) -> list[float]:
        return list(self._weights)

    def predict(self, df: pd.DataFrame, n: int = 23) -> PredictionResult:
        self._validate_n(n)

        total_weight = sum(self._weights)
        combined = pd.Series(0.0, index=_NUMEROS)

        for strategy, weight in zip(self._strategies, self._weights, strict=True):
            # Pede todos os 25 scores para normalizar adequadamente
            result = strategy.predict(df, n=23)
            raw = pd.Series(result.scores)
            normed = normalize(raw)
            combined += (weight / total_weight) * normed

        top = list(combined.nlargest(n).index)
        conf = float(combined[top].mean())

        return PredictionResult(
            numeros=sorted(top),
            scores=dict(zip(_NUMEROS, (float(v) for v in combined.values), strict=True)),
            confidence=conf,
            strategy_name=self.name,
            metadata={
                "strategies": [s.name for s in self._strategies],
                "weights": list(self._weights),
            },
        )
