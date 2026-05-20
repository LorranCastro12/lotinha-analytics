"""Backtester walk-forward com teste de Wilcoxon vs baseline aleatório."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
from scipy.stats import wilcoxon as sp_wilcoxon

from lotinha.analysis.strategies.base import BaseStrategy
from lotinha.core.exceptions import InsufficientDataError

# Mínimo de draws testados para o teste de Wilcoxon ser confiável
_WILCOXON_MIN_SAMPLES = 10


@dataclass
class BacktestResult:
    """Resultado completo de um backtest walk-forward.

    Attributes:
        strategy_name: Nome da estratégia avaliada.
        n_preditos: Quantidade de números apostados.
        n_draws_tested: Total de sorteios no conjunto de teste.
        acertos_strategy: Lista de acertos por sorteio (estratégia).
        acertos_random: Lista de acertos por sorteio (baseline aleatório).
        prizes_strategy: Lista de prêmios por sorteio (estratégia).
        prizes_random: Lista de prêmios por sorteio (baseline).
        cost_per_draw: Custo por aposta.
        p_value: p-value do teste de Wilcoxon (None se amostras insuficientes).
    """

    strategy_name: str
    n_preditos: int
    n_draws_tested: int
    acertos_strategy: list[int]
    acertos_random: list[int]
    prizes_strategy: list[float]
    prizes_random: list[float]
    cost_per_draw: float
    p_value: float | None

    @property
    def mean_acertos_strategy(self) -> float:
        if not self.acertos_strategy:
            return 0.0
        return sum(self.acertos_strategy) / len(self.acertos_strategy)

    @property
    def mean_acertos_random(self) -> float:
        if not self.acertos_random:
            return 0.0
        return sum(self.acertos_random) / len(self.acertos_random)

    @property
    def roi_strategy(self) -> float:
        """ROI da estratégia: (prêmios - custos) / custos."""
        total_cost = self.n_draws_tested * self.cost_per_draw
        if total_cost == 0.0:
            return 0.0
        return (sum(self.prizes_strategy) - total_cost) / total_cost

    @property
    def roi_random(self) -> float:
        """ROI do baseline aleatório."""
        total_cost = self.n_draws_tested * self.cost_per_draw
        if total_cost == 0.0:
            return 0.0
        return (sum(self.prizes_random) - total_cost) / total_cost

    @property
    def beats_random(self) -> bool:
        """True se estratégia supera baseline (p < 0.05)."""
        return self.p_value is not None and self.p_value < 0.05

    @property
    def warning(self) -> str | None:
        """Aviso honesto quando estratégia não supera aleatório."""
        if self.beats_random:
            return None
        p_str = f"{self.p_value:.3f}" if self.p_value is not None else "N/A (amostras insuf.)"
        return (
            f"AVISO: '{self.strategy_name}' nao supera o baseline aleatorio "
            f"(p={p_str}, a=0.05). Nenhum edge estatistico detectado."
        )


class Backtester:
    """Avalia estratégias por walk-forward e compara com baseline aleatório.

    Para cada draw do conjunto de teste (índices train_size..len-1):
        1. Treina a estratégia no histórico até aquele ponto.
        2. Prediz n_preditos números para o próximo sorteio.
        3. Conta acertos contra o sorteio real.
        4. Gera baseline aleatório com os mesmos parâmetros.

    Ao final, aplica o teste de Wilcoxon signed-rank (unilateral, strategy > random)
    e emite aviso explícito se não houver evidência estatística de edge.

    Args:
        premios: Mapeamento {acertos: prêmio} (acertos < limiar retornam 0).
        custo: Custo fixo por aposta.
        seed: Semente para o baseline aleatório (reprodutibilidade).
    """

    def __init__(
        self,
        premios: dict[int, float],
        custo: float,
        seed: int = 42,
    ) -> None:
        self._premios = premios
        self._custo = custo
        self._rng = random.Random(seed)

    def run(
        self,
        df: pd.DataFrame,
        strategy: BaseStrategy,
        n_preditos: int = 22,
        train_size: int = 60,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> BacktestResult:
        """Executa o backtest walk-forward.

        Args:
            df: Histórico de sorteios ordenado cronologicamente.
            strategy: Estratégia a avaliar.
            n_preditos: Números apostados por draw (17..22).
            train_size: Mínimo de draws usados como histórico inicial.
            progress_callback: Chamado com (atual, total) a cada draw testado.

        Returns:
            BacktestResult completo com estatísticas e p-value.

        Raises:
            InsufficientDataError: Se len(df) <= train_size.
        """
        if len(df) <= train_size:
            raise InsufficientDataError(required=train_size + 1, available=len(df))

        acertos_strat: list[int] = []
        acertos_rand: list[int] = []
        prizes_strat: list[float] = []
        prizes_rand: list[float] = []

        test_indices = list(range(train_size, len(df)))
        total = len(test_indices)

        for step, t in enumerate(test_indices, start=1):
            history = df.iloc[:t]
            strategy.reset()

            try:
                pred_result = strategy.predict(history, n=n_preditos)
            except InsufficientDataError:
                continue

            pred_set = set(pred_result.numeros)
            actual = set(df["numeros"].iloc[t])

            # Estratégia
            a_strat = len(pred_set & actual)
            acertos_strat.append(a_strat)
            prizes_strat.append(self._premios.get(a_strat, 0.0))

            # Baseline aleatório
            rand_sample = self._rng.sample(range(1, 26), n_preditos)
            a_rand = len(set(rand_sample) & actual)
            acertos_rand.append(a_rand)
            prizes_rand.append(self._premios.get(a_rand, 0.0))

            if progress_callback:
                progress_callback(step, total)

        p_value = self._wilcoxon_p(acertos_strat, acertos_rand)

        return BacktestResult(
            strategy_name=strategy.name,
            n_preditos=n_preditos,
            n_draws_tested=len(acertos_strat),
            acertos_strategy=acertos_strat,
            acertos_random=acertos_rand,
            prizes_strategy=prizes_strat,
            prizes_random=prizes_rand,
            cost_per_draw=self._custo,
            p_value=p_value,
        )

    # ── Internals ──────────────────────────────────────────────────────────────

    def _wilcoxon_p(self, a: list[int], b: list[int]) -> float | None:
        """Teste de Wilcoxon signed-rank unilateral (H1: estratégia > aleatório)."""
        if len(a) < _WILCOXON_MIN_SAMPLES:
            return None

        diffs = [x - y for x, y in zip(a, b, strict=True)]
        if all(d == 0 for d in diffs):
            return 1.0

        try:
            _, p = sp_wilcoxon(a, b, alternative="greater", zero_method="zsplit")
            return float(p)
        except ValueError:
            return 1.0
