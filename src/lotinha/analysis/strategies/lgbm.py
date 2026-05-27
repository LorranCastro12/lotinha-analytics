"""Estratégia de predição baseada em LightGBM."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from lotinha.analysis.statistics import atraso, frequencia
from lotinha.analysis.strategies.base import BaseStrategy
from lotinha.core.domain import PredictionResult
from lotinha.core.exceptions import InsufficientDataError

if TYPE_CHECKING:
    pass

_NUMEROS = list(range(1, 26))
_DEFAULT_MIN_DRAWS = 90


class LightGBMStrategy(BaseStrategy):
    """Prediz usando um classificador LightGBM treinado em features históricas.

    Features por número por sorteio:
        - freq_10, freq_30, freq_60: frequência nas últimas 10/30/60 extrações
        - atraso: sorteios desde última aparição
        - trend: freq_10 - freq_30 (positivo = em alta)
        - in_last: apareceu no sorteio anterior (0/1)

    Args:
        min_draws: Mínimo de sorteios históricos exigidos para treinar.
    """

    def __init__(self, min_draws: int = _DEFAULT_MIN_DRAWS) -> None:
        self._min_draws = min_draws
        self._model: Any = None

    @property
    def name(self) -> str:
        return "lgbm"

    @property
    def is_fitted(self) -> bool:
        return self._model is not None

    def reset(self) -> None:
        """Descarta o modelo treinado para forçar refit no próximo predict."""
        self._model = None

    def fit(self, df: pd.DataFrame) -> None:
        """Treina o modelo com o histórico completo fornecido."""
        import lightgbm as lgb

        X_parts: list[pd.DataFrame] = []
        y_parts: list[pd.Series] = []

        for idx in range(self._min_draws, len(df)):
            history = df.iloc[:idx]
            feats = self._build_features(history, df["numeros"].iloc[idx - 1])
            target_set = set(df["numeros"].iloc[idx])
            targets = pd.Series(
                [1 if num in target_set else 0 for num in _NUMEROS],
                dtype=np.int8,
            )
            X_parts.append(feats)
            y_parts.append(targets)

        if not X_parts:
            raise InsufficientDataError(required=self._min_draws + 1, available=len(df))

        X = pd.concat(X_parts, ignore_index=True)
        y = pd.concat(y_parts, ignore_index=True)

        model = lgb.LGBMClassifier(
            n_estimators=50,
            num_leaves=15,
            learning_rate=0.1,
            verbosity=-1,
            random_state=42,
        )
        model.fit(X, y)
        self._model = model

    def predict(self, df: pd.DataFrame, n: int = 23) -> PredictionResult:
        self._validate_n(n)
        if len(df) < self._min_draws:
            raise InsufficientDataError(required=self._min_draws, available=len(df))

        if not self.is_fitted:
            self.fit(df)

        last_draw = df["numeros"].iloc[-1]
        feats = self._build_features(df, last_draw)
        probs = self._model.predict_proba(feats)
        # LGB retorna [[p_class0, p_class1], ...] — queremos class1
        if probs.shape[1] == 2:
            raw_scores = probs[:, 1].astype(np.float64)
        else:
            raw_scores = probs[:, 0].astype(np.float64)

        scores = pd.Series(raw_scores, index=_NUMEROS)
        top = list(scores.nlargest(n).index)
        conf = float(scores[top].mean())

        return PredictionResult(
            numeros=sorted(top),
            scores=dict(zip(_NUMEROS, (float(v) for v in scores.values), strict=True)),
            confidence=conf,
            strategy_name=self.name,
            metadata={"min_draws": self._min_draws},
        )

    def _build_features(self, history: pd.DataFrame, last_draw: list[int]) -> pd.DataFrame:
        """Constrói matriz de features para os 25 números."""
        freq10 = frequencia(history, 10)
        freq30 = frequencia(history, 30)
        freq60 = frequencia(history, 60)
        atr = atraso(history).astype(np.float64)
        last_set = set(last_draw)
        in_last = pd.Series(
            [1.0 if num in last_set else 0.0 for num in _NUMEROS],
            index=_NUMEROS,
        )
        trend = freq10 - freq30

        return pd.DataFrame({
            "freq10": freq10.values,
            "freq30": freq30.values,
            "freq60": freq60.values,
            "atraso": atr.values,
            "trend": trend.values,
            "in_last": in_last.values,
        })
