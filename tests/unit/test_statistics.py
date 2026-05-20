"""Testes das funções estatísticas core — Fase 5."""

from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

from lotinha.analysis.statistics import (
    atraso,
    co_ocorrencias,
    frequencia,
    valor_esperado,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _df(*sorteios: list[int]) -> pd.DataFrame:
    """Cria DataFrame mínimo com coluna 'numeros'."""
    return pd.DataFrame({"numeros": list(sorteios)})


# ---------------------------------------------------------------------------
# frequencia
# ---------------------------------------------------------------------------

class TestFrequencia:
    def test_retorna_series_25_elementos(self) -> None:
        df = _df([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        result = frequencia(df)
        assert len(result) == 25
        assert set(result.index) == set(range(1, 26))

    def test_df_vazio_retorna_zeros(self) -> None:
        df = pd.DataFrame({"numeros": pd.Series([], dtype=object)})
        result = frequencia(df)
        assert (result == 0.0).all()
        assert len(result) == 25

    def test_numero_unico_tem_frequencia_1(self) -> None:
        numeros = list(range(1, 16))  # 1..15
        df = _df(numeros)
        result = frequencia(df)
        for n in numeros:
            assert result[n] == pytest.approx(1.0)
        for n in range(16, 26):
            assert result[n] == pytest.approx(0.0)

    def test_frequencias_normalizado_por_sorteios(self) -> None:
        # 2 sorteios, número 1 aparece em ambos → freq = 1.0
        # número 2 aparece em 1 sorteio → freq = 0.5
        df = _df(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            [1, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 3, 4, 5, 6],
        )
        result = frequencia(df)
        assert result[1] == pytest.approx(1.0)
        assert result[2] == pytest.approx(0.5)
        assert result[16] == pytest.approx(0.5)

    def test_janela_limita_sorteios_recentes(self) -> None:
        # 3 sorteios: o número 1 aparece apenas no mais antigo
        draw_antigo = list(range(1, 16))   # 1..15, inclui 1
        draw_medio  = list(range(2, 17))   # 2..16, sem 1
        draw_recente = list(range(3, 18))  # 3..17, sem 1
        df = _df(draw_antigo, draw_medio, draw_recente)
        result_sem_janela = frequencia(df)
        result_janela2 = frequencia(df, janela=2)
        # sem janela, número 1 aparece 1 vez em 3 sorteios
        assert result_sem_janela[1] == pytest.approx(1 / 3)
        # com janela=2, número 1 não aparece nos últimos 2 sorteios
        assert result_janela2[1] == pytest.approx(0.0)

    def test_janela_maior_que_df_usa_todos(self) -> None:
        df = _df([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        result_sem = frequencia(df)
        result_janela = frequencia(df, janela=1000)
        pd.testing.assert_series_equal(result_sem, result_janela)

    def test_janela_zero_retorna_zeros(self) -> None:
        df = _df([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        result = frequencia(df, janela=0)
        assert (result == 0.0).all()

    def test_valores_entre_0_e_1(self) -> None:
        draws = [[i % 25 + 1 for i in range(k, k + 15)] for k in range(10)]
        df = _df(*draws)
        result = frequencia(df)
        assert (result >= 0.0).all()
        assert (result <= 1.0).all()

    def test_numeros_fora_do_range_ignorados(self) -> None:
        # número 0 e 26 devem ser ignorados (não estão no index 1..25)
        df = _df([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 26])
        result = frequencia(df)
        # número 1 apareceu, 0 e 26 são ignorados
        assert result[1] == pytest.approx(1.0)
        # resultado só tem índice 1..25
        assert 0 not in result.index
        assert 26 not in result.index


# ---------------------------------------------------------------------------
# atraso
# ---------------------------------------------------------------------------

class TestAtraso:
    def test_retorna_series_25_elementos(self) -> None:
        df = _df([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        result = atraso(df)
        assert len(result) == 25
        assert set(result.index) == set(range(1, 26))

    def test_numero_no_ultimo_sorteio_tem_atraso_zero(self) -> None:
        draw = list(range(1, 16))  # 1..15
        df = _df(draw)
        result = atraso(df)
        for n in draw:
            assert result[n] == 0

    def test_numero_nunca_visto_tem_atraso_igual_a_total(self) -> None:
        # 3 sorteios, número 25 nunca aparece
        df = _df(
            list(range(1, 16)),
            list(range(2, 17)),
            list(range(3, 18)),
        )
        result = atraso(df)
        # 25 nunca apareceu → atraso = n_sorteios = 3
        assert result[25] == 3

    def test_atraso_progressivo(self) -> None:
        # sorteio 0: número 1 aparece
        # sorteio 1: não aparece
        # sorteio 2: não aparece
        # atraso de 1 no sorteio 2 = 2
        df = _df(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
            [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        )
        result = atraso(df)
        assert result[1] == 2

    def test_df_vazio_retorna_zeros_com_atraso_n(self) -> None:
        df = pd.DataFrame({"numeros": pd.Series([], dtype=object)})
        result = atraso(df)
        assert len(result) == 25
        # com 0 sorteios, atraso de todos = 0
        assert (result == 0).all()

    def test_valores_nao_negativos(self) -> None:
        draws = [[i % 25 + 1 for i in range(k, k + 15)] for k in range(20)]
        df = _df(*draws)
        result = atraso(df)
        assert (result >= 0).all()

    def test_dtype_inteiro(self) -> None:
        df = _df([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        result = atraso(df)
        assert pd.api.types.is_integer_dtype(result.dtype)


# ---------------------------------------------------------------------------
# co_ocorrencias
# ---------------------------------------------------------------------------

class TestCoOcorrencias:
    def test_retorna_dataframe_25x25(self) -> None:
        df = _df([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        result = co_ocorrencias(df)
        assert result.shape == (25, 25)
        assert list(result.index) == list(range(1, 26))
        assert list(result.columns) == list(range(1, 26))

    def test_df_vazio_retorna_zeros(self) -> None:
        df = pd.DataFrame({"numeros": pd.Series([], dtype=object)})
        result = co_ocorrencias(df)
        assert result.shape == (25, 25)
        assert (result == 0).all().all()

    def test_diagonal_igual_a_contagem_individual(self) -> None:
        # número n sempre aparece com ele mesmo: co_oc[n,n] = num_sorteios em que n aparece
        df = _df(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            [1, 2, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 4, 5, 6],
        )
        result = co_ocorrencias(df)
        # número 1 aparece em ambos os sorteios → diagonal[1] = 2
        assert result.loc[1, 1] == 2
        # número 3 aparece em apenas 1 sorteio → diagonal[3] = 1
        assert result.loc[3, 3] == 1
        # número 16 aparece em 1 sorteio → diagonal[16] = 1
        assert result.loc[16, 16] == 1

    def test_matriz_simetrica(self) -> None:
        draws = [[i % 25 + 1 for i in range(k, k + 15)] for k in range(5)]
        df = _df(*draws)
        result = co_ocorrencias(df)
        np.testing.assert_array_equal(result.values, result.values.T)

    def test_par_co_ocorrente(self) -> None:
        # números 1 e 2 aparecem juntos em 2 de 3 sorteios
        df = _df(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            [1, 2, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 4, 5, 6],
            [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        )
        result = co_ocorrencias(df)
        assert result.loc[1, 2] == 2
        assert result.loc[2, 1] == 2

    def test_par_nunca_co_ocorrente(self) -> None:
        # 1 só aparece no sorteio A, 25 só no sorteio B → co_oc = 0
        df = _df(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 11, 12, 13, 14, 15],
        )
        result = co_ocorrencias(df)
        assert result.loc[1, 25] == 0

    def test_valores_nao_negativos(self) -> None:
        draws = [[i % 25 + 1 for i in range(k, k + 15)] for k in range(10)]
        df = _df(*draws)
        result = co_ocorrencias(df)
        assert (result >= 0).all().all()


# ---------------------------------------------------------------------------
# valor_esperado
# ---------------------------------------------------------------------------

class TestValorEsperado:
    def test_sem_premios_retorna_negativo_custo(self) -> None:
        # sem premiação → ev = -custo
        result = valor_esperado(
            n_preditos=22,
            n_sorteados=15,
            n_total=25,
            premios={},
            custo=2.50,
        )
        assert result == pytest.approx(-2.50)

    def test_custo_zero_sem_premio_retorna_zero(self) -> None:
        result = valor_esperado(
            n_preditos=22,
            n_sorteados=15,
            n_total=25,
            premios={},
            custo=0.0,
        )
        assert result == pytest.approx(0.0)

    def test_resultado_e_float(self) -> None:
        result = valor_esperado(
            n_preditos=22,
            n_sorteados=15,
            n_total=25,
            premios={15: 100.0},
            custo=1.0,
        )
        assert isinstance(result, float)

    def test_prob_acumula_corretamente(self) -> None:
        # com prêmio em todas as faixas, ev > -custo
        premios = {k: 10.0 for k in range(11, 16)}
        result = valor_esperado(
            n_preditos=22,
            n_sorteados=15,
            n_total=25,
            premios=premios,
            custo=2.50,
        )
        # a soma de probabilidades × prêmio deve ser positiva
        # portanto ev > -2.50
        assert result > -2.50

    def test_grande_premio_15_acertos(self) -> None:
        # probabilidade de acertar todos os 15 com 22 preditos
        # hypergeom.pmf(15, 25, 15, 22) deve ser > 0
        from scipy.stats import hypergeom
        p = float(hypergeom.pmf(15, 25, 15, 22))
        assert p > 0
        result = valor_esperado(
            n_preditos=22,
            n_sorteados=15,
            n_total=25,
            premios={15: 1_000_000.0},
            custo=0.0,
        )
        assert result == pytest.approx(p * 1_000_000.0)

    def test_premio_em_faixa_invalida_sem_efeito(self) -> None:
        # acertos > n_preditos é impossível → prob = 0
        result_sem = valor_esperado(22, 15, 25, {}, 1.0)
        result_com = valor_esperado(22, 15, 25, {99: 999_999.0}, 1.0)
        assert result_sem == pytest.approx(result_com)

    def test_diferentes_configuracoes_retornam_float(self) -> None:
        configs = [
            (17, 15, 25, {11: 5.0, 12: 20.0, 13: 50.0, 14: 200.0, 15: 1000.0}, 1.0),
            (20, 15, 25, {12: 10.0, 15: 500.0}, 2.0),
            (22, 15, 25, {15: 100_000.0}, 5.0),
        ]
        for args in configs:
            result = valor_esperado(*args)
            assert isinstance(result, float)
