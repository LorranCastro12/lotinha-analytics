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

    Args:
        alpha: Parâmetro de suavização de Laplace (add-alpha). Evita
            probabilidades zero em matrizes esparsas (poucos sorteios
            por hora). Default 0.5 é adequado para datasets < 50 amostras.
    """

    def __init__(self, alpha: float = 0.5) -> None:
        self._alpha = alpha

    @property
    def name(self) -> str:
        return "markov"

    def predict(
        self,
        df: pd.DataFrame,
        n: int = 22,
        df_global: pd.DataFrame | None = None,
        blend: float = 0.35,
    ) -> PredictionResult:
        """Prediz os n números mais prováveis.

        Args:
            df: Histórico hora-específico (banca + hora filtrados).
            n: Quantidade de números a retornar.
            df_global: Histórico banca-wide (sem filtro de hora). Quando
                fornecido, a matriz local é mesclada com a global para
                compensar a escassez de dados por hora (~17 amostras).
            blend: Peso dado à matriz hora-específica na mescla
                (0 = só global, 1 = só hora). Default 0.35.
        """
        self._validate_n(n)
        if len(df) < 2:
            raise InsufficientDataError(required=2, available=len(df))

        trans = self._build_transition(df)
        if df_global is not None and len(df_global) >= 30:
            trans_global = self._build_transition(df_global)
            trans_arr = blend * trans.values + (1 - blend) * trans_global.values
            trans = pd.DataFrame(trans_arr, index=_NUMEROS, columns=_NUMEROS)

        last = df["numeros"].iloc[-1]
        scores = trans.loc[[num for num in last if 1 <= num <= 25]].sum()
        top = list(scores.nlargest(n).index)
        conf = self._confidence(scores, top)

        return PredictionResult(
            numeros=sorted(top),
            scores=dict(zip(_NUMEROS, (float(v) for v in scores.values), strict=True)),
            confidence=conf,
            strategy_name=self.name,
            metadata={"alpha": self._alpha, "blend": blend if df_global is not None else None},
        )

    def _build_transition(self, df: pd.DataFrame) -> pd.DataFrame:
        """Matriz de transição P[i, j] = P(j em t+1 | i em t) com suavização de Laplace."""
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

        trans += self._alpha  # Laplace smoothing: evita zeros em datasets pequenos
        row_sums = trans.sum(axis=1, keepdims=True)
        trans = trans / row_sums

        return pd.DataFrame(trans, index=_NUMEROS, columns=_NUMEROS)


class HybridMarkovWrapper(BaseStrategy):
    """MarkovStrategy com blend automático usando histórico banca-wide.

    Armazena df_global internamente para expor a interface padrão
    ``predict(df, n)`` e ser compatível com EnsembleStrategy.

    Args:
        df_global: Histórico banca-wide (sem filtro de hora).
        alpha: Suavização de Laplace repassada ao MarkovStrategy.
        blend: Peso hora-específico na mescla (0 = só global, 1 = só hora).
    """

    def __init__(
        self,
        df_global: pd.DataFrame,
        alpha: float = 0.5,
        blend: float = 0.35,
    ) -> None:
        self._markov = MarkovStrategy(alpha=alpha)
        self._df_global = df_global
        self._blend = blend

    @property
    def name(self) -> str:
        return "markov_hybrid"

    def predict(self, df: pd.DataFrame, n: int = 22) -> PredictionResult:
        return self._markov.predict(df, n=n, df_global=self._df_global, blend=self._blend)


class BancaAwareLGBMWrapper(BaseStrategy):
    """LightGBMStrategy que usa dados banca-wide em vez dos hora-específicos.

    Necessário porque o LightGBM requer ≥50 amostras por treino, mas dados
    filtrados por (banca, hora) têm apenas ~17 amostras. Este wrapper
    armazena df_banca e hora internamente, ignorando o df hora-específico
    recebido em predict() — compatível com EnsembleStrategy.

    Args:
        df_banca: Histórico completo da banca (sem filtro de hora).
        hora: Hora alvo para features temporais (hora_norm/sin/cos).
        min_draws: Mínimo de sorteios para treinar o LightGBM.
    """

    def __init__(
        self,
        df_banca: pd.DataFrame,
        hora: int,
        min_draws: int = 50,
    ) -> None:
        from lotinha.analysis.strategies.lgbm import LightGBMStrategy

        self._lgbm = LightGBMStrategy(min_draws=min_draws)
        self._df_banca = df_banca
        self._hora = hora

    @property
    def name(self) -> str:
        return "lgbm"

    def predict(self, df: pd.DataFrame, n: int = 23) -> PredictionResult:
        # df hora-específico é ignorado; usa df_banca com hora como feature
        return self._lgbm.predict(self._df_banca, n=n, hora=self._hora)

    def reset(self) -> None:
        self._lgbm.reset()
