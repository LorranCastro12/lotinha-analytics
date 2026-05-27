"""Testes do backtester walk-forward — Fase 7."""

from __future__ import annotations

import random
from typing import Any

import pandas as pd
import pytest

from lotinha.analysis.strategies.base import BaseStrategy
from lotinha.core.domain import PredictionResult
from lotinha.core.exceptions import InsufficientDataError


# ---------------------------------------------------------------------------
# Estratégia auxiliar para testes (acertos determinísticos)
# ---------------------------------------------------------------------------

class FixedStrategy(BaseStrategy):
    """Retorna sempre os mesmos números independente do histórico."""

    def __init__(self, numeros: list[int], name_: str = "fixed") -> None:
        self._numeros = numeros
        self._name = name_
        self.reset_count = 0

    @property
    def name(self) -> str:
        return self._name

    def reset(self) -> None:
        self.reset_count += 1

    def predict(self, df: pd.DataFrame, n: int = 23) -> PredictionResult:
        if len(df) == 0:
            raise InsufficientDataError(required=1, available=0)
        scores = {i: 1.0 if i in self._numeros else 0.0 for i in range(1, 26)}
        return PredictionResult(
            numeros=self._numeros,
            scores=scores,
            confidence=1.0,
            strategy_name=self.name,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _synthetic_df(n: int, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = [sorted(rng.sample(range(1, 26), 15)) for _ in range(n)]
    return pd.DataFrame({"numeros": rows})


def _premios_padrao() -> dict[int, float]:
    return {11: 5.0, 12: 20.0, 13: 50.0, 14: 200.0, 15: 1000.0}


# ---------------------------------------------------------------------------
# BacktestResult
# ---------------------------------------------------------------------------

class TestBacktestResult:
    def _make_result(self, **kwargs: Any):
        from lotinha.analysis.backtester import BacktestResult
        defaults: dict[str, Any] = dict(
            strategy_name="fixed",
            n_preditos=23,
            n_draws_tested=20,
            acertos_strategy=list(range(8, 28)),   # 20 valores
            acertos_random=list(range(7, 27)),      # 20 valores
            prizes_strategy=[0.0] * 20,
            prizes_random=[0.0] * 20,
            cost_per_draw=2.0,
            p_value=0.03,
        )
        defaults.update(kwargs)
        return BacktestResult(**defaults)

    def test_beats_random_true_quando_p_baixo(self) -> None:
        r = self._make_result(p_value=0.03)
        assert r.beats_random is True

    def test_beats_random_false_quando_p_alto(self) -> None:
        r = self._make_result(p_value=0.20)
        assert r.beats_random is False

    def test_beats_random_false_quando_p_none(self) -> None:
        r = self._make_result(p_value=None)
        assert r.beats_random is False

    def test_warning_presente_quando_nao_supera(self) -> None:
        r = self._make_result(p_value=0.20)
        assert r.warning is not None
        assert "fixed" in r.warning
        assert "aleatório" in r.warning.lower() or "random" in r.warning.lower() or "aleat" in r.warning.lower()

    def test_warning_none_quando_supera(self) -> None:
        r = self._make_result(p_value=0.03)
        assert r.warning is None

    def test_mean_acertos_strategy(self) -> None:
        r = self._make_result(acertos_strategy=[10, 12, 14], acertos_random=[9, 11, 13],
                               n_draws_tested=3, prizes_strategy=[0.0]*3, prizes_random=[0.0]*3)
        assert r.mean_acertos_strategy == pytest.approx(12.0)

    def test_mean_acertos_random(self) -> None:
        r = self._make_result(acertos_strategy=[10, 12, 14], acertos_random=[9, 11, 13],
                               n_draws_tested=3, prizes_strategy=[0.0]*3, prizes_random=[0.0]*3)
        assert r.mean_acertos_random == pytest.approx(11.0)

    def test_roi_strategy_calculado(self) -> None:
        # 5 draws, custo=2.0, prêmio total=10.0 → roi=(10-10)/10=0
        r = self._make_result(
            n_draws_tested=5,
            acertos_strategy=[9, 9, 9, 9, 9],
            acertos_random=[9, 9, 9, 9, 9],
            prizes_strategy=[0.0, 0.0, 10.0, 0.0, 0.0],
            prizes_random=[0.0] * 5,
            cost_per_draw=2.0,
            p_value=None,
        )
        # total_cost = 5 * 2.0 = 10; total_prize = 10; roi = 0.0
        assert r.roi_strategy == pytest.approx(0.0)

    def test_roi_negativo_sem_premio(self) -> None:
        r = self._make_result(
            n_draws_tested=5,
            acertos_strategy=[9]*5,
            acertos_random=[9]*5,
            prizes_strategy=[0.0]*5,
            prizes_random=[0.0]*5,
            cost_per_draw=2.0,
            p_value=None,
        )
        assert r.roi_strategy == pytest.approx(-1.0)

    def test_p_value_no_resultado(self) -> None:
        r = self._make_result(p_value=0.042)
        assert r.p_value == pytest.approx(0.042)


# ---------------------------------------------------------------------------
# Backtester
# ---------------------------------------------------------------------------

class TestBacktester:
    @pytest.fixture()
    def backtester(self):
        from lotinha.analysis.backtester import Backtester
        return Backtester(premios=_premios_padrao(), custo=2.0, seed=0)

    def test_retorna_backtest_result(self, backtester) -> None:
        from lotinha.analysis.backtester import BacktestResult
        strategy = FixedStrategy(list(range(1, 24)))  # números 1..23
        df = _synthetic_df(30)
        result = backtester.run(df, strategy, n_preditos=23, train_size=20)
        assert isinstance(result, BacktestResult)

    def test_n_draws_tested_correto(self, backtester) -> None:
        strategy = FixedStrategy(list(range(1, 24)))
        df = _synthetic_df(30)
        result = backtester.run(df, strategy, n_preditos=23, train_size=20)
        # test draws = len(df) - train_size = 10
        assert result.n_draws_tested == 10

    def test_acertos_lista_tamanho_correto(self, backtester) -> None:
        strategy = FixedStrategy(list(range(1, 24)))
        df = _synthetic_df(30)
        result = backtester.run(df, strategy, n_preditos=23, train_size=20)
        assert len(result.acertos_strategy) == result.n_draws_tested
        assert len(result.acertos_random) == result.n_draws_tested

    def test_strategy_name_correto(self, backtester) -> None:
        strategy = FixedStrategy(list(range(1, 24)), name_="minha_strat")
        df = _synthetic_df(30)
        result = backtester.run(df, strategy, n_preditos=23, train_size=20)
        assert result.strategy_name == "minha_strat"

    def test_acertos_entre_0_e_15(self, backtester) -> None:
        strategy = FixedStrategy(list(range(1, 24)))
        df = _synthetic_df(30)
        result = backtester.run(df, strategy, train_size=20)
        for a in result.acertos_strategy:
            assert 0 <= a <= 15
        for a in result.acertos_random:
            assert 0 <= a <= 15

    def test_insufficient_data_error_quando_df_pequeno(self, backtester) -> None:
        strategy = FixedStrategy(list(range(1, 23)))
        df = _synthetic_df(10)
        with pytest.raises(InsufficientDataError):
            backtester.run(df, strategy, train_size=20)

    def test_progress_callback_chamado(self, backtester) -> None:
        strategy = FixedStrategy(list(range(1, 24)))
        df = _synthetic_df(30)
        calls: list[tuple[int, int]] = []
        backtester.run(df, strategy, train_size=20,
                       progress_callback=lambda atual, total: calls.append((atual, total)))
        assert len(calls) == 10
        assert calls[0] == (1, 10)
        assert calls[-1] == (10, 10)

    def test_reset_chamado_antes_de_cada_predict(self, backtester) -> None:
        strategy = FixedStrategy(list(range(1, 24)))
        df = _synthetic_df(30)
        backtester.run(df, strategy, train_size=20)
        # reset deve ter sido chamado 10 vezes (uma por draw testado)
        assert strategy.reset_count == 10

    def test_prizes_calculados_com_premios(self) -> None:
        from lotinha.analysis.backtester import Backtester
        # Número fixo: 1..22 — sorteios sempre incluem 1..15 → acertos=15
        premios = {15: 500.0}
        bt = Backtester(premios=premios, custo=1.0, seed=0)
        # Sorteios sempre [1..15]
        df = pd.DataFrame({"numeros": [list(range(1, 16))] * 30})
        strategy = FixedStrategy(list(range(1, 23)))
        result = bt.run(df, strategy, train_size=20)
        assert all(p == 500.0 for p in result.prizes_strategy)

    def test_cost_per_draw_no_resultado(self, backtester) -> None:
        strategy = FixedStrategy(list(range(1, 24)))
        df = _synthetic_df(30)
        result = backtester.run(df, strategy, train_size=20)
        assert result.cost_per_draw == 2.0

    def test_reproducivel_com_mesmo_seed(self) -> None:
        from lotinha.analysis.backtester import Backtester
        strategy1 = FixedStrategy(list(range(1, 23)))
        strategy2 = FixedStrategy(list(range(1, 23)))
        df = _synthetic_df(30)
        bt1 = Backtester(premios={}, custo=1.0, seed=7)
        bt2 = Backtester(premios={}, custo=1.0, seed=7)
        r1 = bt1.run(df, strategy1, train_size=20)
        r2 = bt2.run(df, strategy2, train_size=20)
        assert r1.acertos_random == r2.acertos_random

    def test_seed_diferente_gera_baseline_diferente(self) -> None:
        from lotinha.analysis.backtester import Backtester
        df = _synthetic_df(50)
        bt1 = Backtester(premios={}, custo=1.0, seed=1)
        bt2 = Backtester(premios={}, custo=1.0, seed=2)
        s1 = FixedStrategy(list(range(1, 23)))
        s2 = FixedStrategy(list(range(1, 23)))
        r1 = bt1.run(df, s1, train_size=20)
        r2 = bt2.run(df, s2, train_size=20)
        # Muito improvável serem iguais com seeds diferentes
        assert r1.acertos_random != r2.acertos_random


# ---------------------------------------------------------------------------
# Wilcoxon
# ---------------------------------------------------------------------------

class TestWilcoxon:
    def test_p_value_none_quando_poucos_dados(self) -> None:
        from lotinha.analysis.backtester import Backtester
        bt = Backtester(premios={}, custo=1.0)
        strategy = FixedStrategy(list(range(1, 23)))
        # Apenas 5 draws testados → poucos para Wilcoxon confiável
        df = _synthetic_df(8)
        result = bt.run(df, strategy, train_size=3)
        # Com apenas 5 draws, p_value pode ser None
        # Não quebramos → apenas verificamos que não crashou
        assert result.p_value is None or isinstance(result.p_value, float)

    def test_p_value_float_com_dados_suficientes(self) -> None:
        from lotinha.analysis.backtester import Backtester
        bt = Backtester(premios={}, custo=1.0, seed=0)
        # Estratégia que acerta todos os 15 sempre
        df = pd.DataFrame({"numeros": [list(range(1, 16))] * 50})
        strategy = FixedStrategy(list(range(1, 23)))
        result = bt.run(df, strategy, train_size=10)
        assert isinstance(result.p_value, float)
        assert 0.0 <= result.p_value <= 1.0

    def test_warning_quando_p_alto(self) -> None:
        from lotinha.analysis.backtester import Backtester
        bt = Backtester(premios={}, custo=1.0, seed=42)
        strategy = FixedStrategy(list(range(1, 24)))
        df = _synthetic_df(30)
        result = bt.run(df, strategy, train_size=15)
        # Com dados aleatórios, estratégia fixa não deve bater aleatório
        # Verificamos apenas que warning existe quando p >= 0.05
        if result.p_value is None or result.p_value >= 0.05:
            assert result.warning is not None
            assert result.beats_random is False


# ---------------------------------------------------------------------------
# Reset em estratégias
# ---------------------------------------------------------------------------

class TestStrategyReset:
    def test_base_strategy_reset_noop(self) -> None:
        strategy = FixedStrategy(list(range(1, 23)))
        # reset_count começa em 0, reset() incrementa na nossa implementação de teste
        strategy.reset()
        assert strategy.reset_count == 1

    def test_lgbm_reset_limpa_modelo(self) -> None:
        from lotinha.analysis.strategies import LightGBMStrategy
        strategy = LightGBMStrategy(min_draws=5)
        df = _synthetic_df(10)
        strategy.fit(df)
        assert strategy.is_fitted
        strategy.reset()
        assert not strategy.is_fitted

    def test_frequencia_reset_noop(self) -> None:
        from lotinha.analysis.strategies import FrequenciaStrategy
        s = FrequenciaStrategy()
        s.reset()  # deve funcionar sem erro
