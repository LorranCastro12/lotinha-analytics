"""Testes das estratégias de predição — Fase 6."""

from __future__ import annotations

import random
from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from lotinha.core.domain import PredictionResult
from lotinha.core.exceptions import InsufficientDataError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _df(*sorteios: list[int]) -> pd.DataFrame:
    return pd.DataFrame({"numeros": list(sorteios)})


def _synthetic_df(n: int, seed: int = 42) -> pd.DataFrame:
    """Gera n sorteios sintéticos (15 números únicos de 1..25)."""
    rng = random.Random(seed)
    rows = [sorted(rng.sample(range(1, 26), 15)) for _ in range(n)]
    return pd.DataFrame({"numeros": rows})


def _assert_valid_result(result: PredictionResult, expected_n: int) -> None:
    assert len(result.numeros) == expected_n
    assert len(set(result.numeros)) == expected_n
    assert all(1 <= x <= 25 for x in result.numeros)
    assert len(result.scores) == 25
    assert all(1 <= k <= 25 for k in result.scores)
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.strategy_name, str)


# ---------------------------------------------------------------------------
# FrequenciaStrategy
# ---------------------------------------------------------------------------

class TestFrequenciaStrategy:
    @pytest.fixture()
    def strategy(self):
        from lotinha.analysis.strategies import FrequenciaStrategy
        return FrequenciaStrategy()

    def test_retorna_n_numeros(self, strategy) -> None:
        df = _synthetic_df(10)
        result = strategy.predict(df, n=22)
        _assert_valid_result(result, 22)

    def test_n_variavel(self, strategy) -> None:
        df = _synthetic_df(10)
        for n in [17, 18, 19, 20, 21, 22]:
            result = strategy.predict(df, n=n)
            assert len(result.numeros) == n

    def test_nome_correto(self, strategy) -> None:
        df = _synthetic_df(5)
        result = strategy.predict(df)
        assert result.strategy_name == "frequencia"

    def test_numero_mais_frequente_esta_no_topo(self, strategy) -> None:
        # número 1 aparece em todos os sorteios → deve estar nos top preditos
        sorteios = [list(range(1, 16))] * 10  # sempre 1..15
        df = _df(*sorteios)
        result = strategy.predict(df, n=17)
        assert 1 in result.numeros
        assert 25 not in result.numeros

    def test_scores_cobre_todos_25_numeros(self, strategy) -> None:
        df = _synthetic_df(10)
        result = strategy.predict(df)
        assert set(result.scores.keys()) == set(range(1, 26))

    def test_janela_parametro(self) -> None:
        from lotinha.analysis.strategies import FrequenciaStrategy
        strategy_janela = FrequenciaStrategy(janela=5)
        df = _synthetic_df(20)
        result = strategy_janela.predict(df)
        _assert_valid_result(result, 22)

    def test_insufficient_data(self, strategy) -> None:
        df = pd.DataFrame({"numeros": pd.Series([], dtype=object)})
        with pytest.raises(InsufficientDataError):
            strategy.predict(df)

    def test_n_invalido(self, strategy) -> None:
        df = _synthetic_df(5)
        with pytest.raises(ValueError):
            strategy.predict(df, n=16)
        with pytest.raises(ValueError):
            strategy.predict(df, n=23)


# ---------------------------------------------------------------------------
# AtrasoStrategy
# ---------------------------------------------------------------------------

class TestAtrasoStrategy:
    @pytest.fixture()
    def strategy(self):
        from lotinha.analysis.strategies import AtrasoStrategy
        return AtrasoStrategy()

    def test_retorna_n_numeros(self, strategy) -> None:
        df = _synthetic_df(10)
        result = strategy.predict(df, n=22)
        _assert_valid_result(result, 22)

    def test_nome_correto(self, strategy) -> None:
        df = _synthetic_df(5)
        result = strategy.predict(df)
        assert result.strategy_name == "atraso"

    def test_numero_mais_atrasado_incluido(self, strategy) -> None:
        # número 25 nunca aparece em nenhum sorteio → atraso máximo
        sorteios = [list(range(1, 16))] * 10  # nunca inclui 25
        df = _df(*sorteios)
        result = strategy.predict(df, n=17)
        assert 25 in result.numeros

    def test_scores_cobre_todos_25(self, strategy) -> None:
        df = _synthetic_df(10)
        result = strategy.predict(df)
        assert set(result.scores.keys()) == set(range(1, 26))

    def test_insufficient_data(self, strategy) -> None:
        df = pd.DataFrame({"numeros": pd.Series([], dtype=object)})
        with pytest.raises(InsufficientDataError):
            strategy.predict(df)

    def test_n_invalido(self, strategy) -> None:
        df = _synthetic_df(5)
        with pytest.raises(ValueError):
            strategy.predict(df, n=16)

    def test_n_variavel(self, strategy) -> None:
        df = _synthetic_df(10)
        for n in [17, 19, 22]:
            result = strategy.predict(df, n=n)
            assert len(result.numeros) == n


# ---------------------------------------------------------------------------
# MarkovStrategy
# ---------------------------------------------------------------------------

class TestMarkovStrategy:
    @pytest.fixture()
    def strategy(self):
        from lotinha.analysis.strategies import MarkovStrategy
        return MarkovStrategy()

    def test_retorna_n_numeros(self, strategy) -> None:
        df = _synthetic_df(15)
        result = strategy.predict(df, n=22)
        _assert_valid_result(result, 22)

    def test_nome_correto(self, strategy) -> None:
        df = _synthetic_df(5)
        result = strategy.predict(df)
        assert result.strategy_name == "markov"

    def test_insuficiente_com_1_sorteio(self, strategy) -> None:
        df = _df([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        with pytest.raises(InsufficientDataError):
            strategy.predict(df)

    def test_ok_com_2_sorteios(self, strategy) -> None:
        df = _df(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        )
        result = strategy.predict(df, n=22)
        _assert_valid_result(result, 22)

    def test_scores_cobre_todos_25(self, strategy) -> None:
        df = _synthetic_df(10)
        result = strategy.predict(df)
        assert set(result.scores.keys()) == set(range(1, 26))

    def test_numeros_preditos_sorted(self, strategy) -> None:
        df = _synthetic_df(10)
        result = strategy.predict(df)
        assert result.numeros == sorted(result.numeros)

    def test_n_invalido(self, strategy) -> None:
        df = _synthetic_df(5)
        with pytest.raises(ValueError):
            strategy.predict(df, n=23)


# ---------------------------------------------------------------------------
# LightGBMStrategy
# ---------------------------------------------------------------------------

class TestLightGBMStrategy:
    @pytest.fixture()
    def strategy_min5(self):
        from lotinha.analysis.strategies import LightGBMStrategy
        return LightGBMStrategy(min_draws=5)

    def test_insuficiente_data_error(self) -> None:
        from lotinha.analysis.strategies import LightGBMStrategy
        strategy = LightGBMStrategy(min_draws=20)
        df = _synthetic_df(10)
        with pytest.raises(InsufficientDataError):
            strategy.predict(df)

    def test_predict_com_dados_suficientes(self, strategy_min5) -> None:
        df = _synthetic_df(10)  # > min_draws=5
        result = strategy_min5.predict(df, n=22)
        _assert_valid_result(result, 22)

    def test_nome_correto(self, strategy_min5) -> None:
        df = _synthetic_df(10)
        result = strategy_min5.predict(df)
        assert result.strategy_name == "lgbm"

    def test_segunda_chamada_usa_modelo_ja_treinado(self, strategy_min5) -> None:
        df = _synthetic_df(10)
        strategy_min5.predict(df)
        assert strategy_min5.is_fitted
        # Segunda chamada não deve falhar
        result2 = strategy_min5.predict(df)
        _assert_valid_result(result2, 22)

    def test_fit_explicito(self, strategy_min5) -> None:
        df = _synthetic_df(10)
        assert not strategy_min5.is_fitted
        strategy_min5.fit(df)
        assert strategy_min5.is_fitted

    def test_scores_cobre_todos_25(self, strategy_min5) -> None:
        df = _synthetic_df(10)
        result = strategy_min5.predict(df)
        assert set(result.scores.keys()) == set(range(1, 26))

    def test_n_variavel(self, strategy_min5) -> None:
        df = _synthetic_df(10)
        for n in [17, 20, 22]:
            result = strategy_min5.predict(df, n=n)
            assert len(result.numeros) == n

    @pytest.mark.slow
    def test_com_dados_reais_min_90(self) -> None:
        from lotinha.analysis.strategies import LightGBMStrategy
        strategy = LightGBMStrategy()  # default min_draws=90
        df = _synthetic_df(100)
        result = strategy.predict(df, n=22)
        _assert_valid_result(result, 22)


# ---------------------------------------------------------------------------
# EnsembleStrategy
# ---------------------------------------------------------------------------

class TestEnsembleStrategy:
    @pytest.fixture()
    def components(self):
        from lotinha.analysis.strategies import AtrasoStrategy, FrequenciaStrategy
        return [FrequenciaStrategy(), AtrasoStrategy()]

    @pytest.fixture()
    def ensemble(self, components):
        from lotinha.analysis.strategies import EnsembleStrategy
        return EnsembleStrategy(strategies=components)

    def test_retorna_n_numeros(self, ensemble) -> None:
        df = _synthetic_df(10)
        result = ensemble.predict(df, n=22)
        _assert_valid_result(result, 22)

    def test_nome_correto(self, ensemble) -> None:
        df = _synthetic_df(10)
        result = ensemble.predict(df)
        assert result.strategy_name == "ensemble"

    def test_scores_cobre_todos_25(self, ensemble) -> None:
        df = _synthetic_df(10)
        result = ensemble.predict(df)
        assert set(result.scores.keys()) == set(range(1, 26))

    def test_pesos_customizados(self) -> None:
        from lotinha.analysis.strategies import (
            AtrasoStrategy,
            EnsembleStrategy,
            FrequenciaStrategy,
        )
        ensemble = EnsembleStrategy(
            strategies=[FrequenciaStrategy(), AtrasoStrategy()],
            weights=[0.8, 0.2],
        )
        df = _synthetic_df(10)
        result = ensemble.predict(df, n=22)
        _assert_valid_result(result, 22)

    def test_pesos_uniformes_por_default(self, components) -> None:
        from lotinha.analysis.strategies import EnsembleStrategy
        ensemble = EnsembleStrategy(strategies=components)
        assert ensemble.weights == [1.0, 1.0]

    def test_propaga_insufficient_data(self, ensemble) -> None:
        df = pd.DataFrame({"numeros": pd.Series([], dtype=object)})
        with pytest.raises(InsufficientDataError):
            ensemble.predict(df)

    def test_n_variavel(self, ensemble) -> None:
        df = _synthetic_df(10)
        for n in [17, 19, 22]:
            result = ensemble.predict(df, n=n)
            assert len(result.numeros) == n

    def test_metadata_inclui_estrategias(self, ensemble) -> None:
        df = _synthetic_df(10)
        result = ensemble.predict(df)
        assert "strategies" in result.metadata

    def test_scores_normalizados_entre_0_e_1(self, ensemble) -> None:
        df = _synthetic_df(10)
        result = ensemble.predict(df)
        for v in result.scores.values():
            assert 0.0 <= v <= 1.0 + 1e-9  # tolerância float

    def test_ensemble_com_tres_estrategias(self) -> None:
        from lotinha.analysis.strategies import (
            AtrasoStrategy,
            EnsembleStrategy,
            FrequenciaStrategy,
            MarkovStrategy,
        )
        ensemble = EnsembleStrategy(
            strategies=[FrequenciaStrategy(), AtrasoStrategy(), MarkovStrategy()],
            weights=[0.5, 0.3, 0.2],
        )
        df = _synthetic_df(10)
        result = ensemble.predict(df, n=22)
        _assert_valid_result(result, 22)
