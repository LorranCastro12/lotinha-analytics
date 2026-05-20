"""Testes da Fase 2: extraction/api_client.py (todos os requests mockados com respx)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import call

import httpx
import pytest
import respx

from lotinha.core.exceptions import (
    ApiServerError,
    DateNotFoundError,
    RateLimitExceededError,
)
from lotinha.extraction.api_client import ApiClient

FIXTURE_PATH = Path("tests/fixtures/api_response_2025-05-16.json")
API_URL = "https://api.pontodobicho.com/numeric-games/results/list"


@pytest.fixture
def fixture_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def client(tmp_path: Path) -> ApiClient:
    """Cliente sem rate-limit para testes rápidos."""
    return ApiClient(
        base_url="https://api.pontodobicho.com",
        rate_limit=0.0,
        cache_dir=tmp_path / "cache",
        http_client=httpx.Client(),
        max_attempts=5,
    )


# ── Sucesso ────────────────────────────────────────────────────────────────────

class TestFetchDaySuccess:
    @respx.mock
    def test_retorna_lista_de_sorteios(self, client: ApiClient, fixture_payload: dict) -> None:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        result = client.fetch_day(date(2025, 5, 16))
        assert len(result) == 18

    @respx.mock
    def test_sorteios_tem_banca_e_hora_corretos(
        self, client: ApiClient, fixture_payload: dict
    ) -> None:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        result = client.fetch_day(date(2025, 5, 16))
        bancas = {s.banca for s in result}
        assert "LOTINHA PONTO" in bancas

    @respx.mock
    def test_request_usa_params_corretos(
        self, client: ApiClient, fixture_payload: dict
    ) -> None:
        route = respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        client.fetch_day(date(2025, 5, 16))
        assert route.called
        req = route.calls[0].request
        assert "date=2025-05-16" in str(req.url)
        assert "gameType=lotinha" in str(req.url)


# ── Cache ──────────────────────────────────────────────────────────────────────

class TestCache:
    @respx.mock
    def test_primeira_chamada_cria_cache(
        self, client: ApiClient, fixture_payload: dict, tmp_path: Path
    ) -> None:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        client.fetch_day(date(2025, 5, 16))
        cache_file = tmp_path / "cache" / "2025-05-16.json"
        assert cache_file.exists()

    @respx.mock
    def test_segunda_chamada_usa_cache_sem_request(
        self, client: ApiClient, fixture_payload: dict
    ) -> None:
        route = respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        client.fetch_day(date(2025, 5, 16))
        client.fetch_day(date(2025, 5, 16))   # segunda chamada — deve usar cache
        assert route.call_count == 1           # apenas 1 request feito

    @respx.mock
    def test_cache_preserva_dados(
        self, client: ApiClient, fixture_payload: dict
    ) -> None:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        r1 = client.fetch_day(date(2025, 5, 16))
        r2 = client.fetch_day(date(2025, 5, 16))
        assert len(r1) == len(r2)
        assert {s.hora for s in r1} == {s.hora for s in r2}

    def test_cache_corrompido_e_ignorado(
        self, client: ApiClient, fixture_payload: dict, tmp_path: Path
    ) -> None:
        cache_file = tmp_path / "cache" / "2025-05-16.json"
        cache_file.parent.mkdir(parents=True)
        cache_file.write_text("{ INVALID JSON }", encoding="utf-8")
        with respx.mock:
            respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
            result = client.fetch_day(date(2025, 5, 16))
        assert len(result) == 18


# ── Tratamento de erros HTTP ───────────────────────────────────────────────────

class TestRetryBehavior:
    @respx.mock
    def test_429_com_retry_after_e_sucesso(
        self,
        client: ApiClient,
        fixture_payload: dict,
        mocker: pytest.MonkeyPatch,
    ) -> None:
        sleep_mock = mocker.patch("lotinha.extraction.api_client.time.sleep")
        respx.get(API_URL).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "3"}),
                httpx.Response(200, json=fixture_payload),
            ]
        )
        result = client.fetch_day(date(2025, 5, 16))
        assert len(result) == 18
        # deve ter dormido 3 segundos após o 429
        sleep_calls = [c for c in sleep_mock.call_args_list if c.args[0] == 3]
        assert len(sleep_calls) >= 1

    @respx.mock
    def test_429_esgota_tentativas(
        self,
        client: ApiClient,
        mocker: pytest.MonkeyPatch,
    ) -> None:
        mocker.patch("lotinha.extraction.api_client.time.sleep")
        respx.get(API_URL).mock(
            return_value=httpx.Response(429, headers={"Retry-After": "1"})
        )
        with pytest.raises(RateLimitExceededError):
            client.fetch_day(date(2025, 5, 16))

    @respx.mock
    def test_500_retry_e_sucesso(
        self,
        client: ApiClient,
        fixture_payload: dict,
        mocker: pytest.MonkeyPatch,
    ) -> None:
        mocker.patch("lotinha.extraction.api_client.time.sleep")
        respx.get(API_URL).mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(500),
                httpx.Response(200, json=fixture_payload),
            ]
        )
        result = client.fetch_day(date(2025, 5, 16))
        assert len(result) == 18

    @respx.mock
    def test_500_esgota_tentativas(
        self,
        client: ApiClient,
        mocker: pytest.MonkeyPatch,
    ) -> None:
        mocker.patch("lotinha.extraction.api_client.time.sleep")
        respx.get(API_URL).mock(return_value=httpx.Response(500))
        with pytest.raises(ApiServerError):
            client.fetch_day(date(2025, 5, 16))

    @respx.mock
    def test_404_nao_retenta(self, client: ApiClient) -> None:
        route = respx.get(API_URL).mock(return_value=httpx.Response(404))
        with pytest.raises(DateNotFoundError):
            client.fetch_day(date(2025, 5, 16))
        assert route.call_count == 1

    @respx.mock
    def test_400_nao_retenta(self, client: ApiClient) -> None:
        route = respx.get(API_URL).mock(return_value=httpx.Response(400))
        with pytest.raises(DateNotFoundError):
            client.fetch_day(date(2025, 5, 16))
        assert route.call_count == 1

    @respx.mock
    def test_erro_de_rede_retenta_e_sucesso(
        self,
        client: ApiClient,
        fixture_payload: dict,
        mocker: pytest.MonkeyPatch,
    ) -> None:
        mocker.patch("lotinha.extraction.api_client.time.sleep")
        respx.get(API_URL).mock(
            side_effect=[
                httpx.RequestError("Connection refused"),
                httpx.Response(200, json=fixture_payload),
            ]
        )
        result = client.fetch_day(date(2025, 5, 16))
        assert len(result) == 18

    @respx.mock
    def test_erro_de_rede_esgota_tentativas(
        self,
        client: ApiClient,
        mocker: pytest.MonkeyPatch,
    ) -> None:
        mocker.patch("lotinha.extraction.api_client.time.sleep")
        respx.get(API_URL).mock(side_effect=httpx.RequestError("Timeout"))
        with pytest.raises(ApiServerError):
            client.fetch_day(date(2025, 5, 16))

    @respx.mock
    def test_429_lê_retry_after_padrao_quando_ausente(
        self,
        client: ApiClient,
        mocker: pytest.MonkeyPatch,
    ) -> None:
        sleep_mock = mocker.patch("lotinha.extraction.api_client.time.sleep")
        respx.get(API_URL).mock(return_value=httpx.Response(429))  # sem Retry-After
        with pytest.raises(RateLimitExceededError):
            client.fetch_day(date(2025, 5, 16))
        # deve ter dormido 5 segundos (padrão)
        sleep_calls = [c for c in sleep_mock.call_args_list if c.args[0] == 5]
        assert len(sleep_calls) >= 1


# ── Rate limiting ──────────────────────────────────────────────────────────────

class TestRateLimit:
    @respx.mock
    def test_sleep_chamado_quando_muito_rapido(
        self,
        tmp_path: Path,
        mocker: pytest.MonkeyPatch,
        fixture_payload: dict,
    ) -> None:
        sleep_mock = mocker.patch("lotinha.extraction.api_client.time.sleep")
        monotonic_mock = mocker.patch("lotinha.extraction.api_client.time.monotonic")
        # simula: agora=100.0, last_request=99.5 → elapsed=0.5, wait=2.5-0.5=2.0
        monotonic_mock.side_effect = [100.0, 100.0]

        respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        client = ApiClient(
            rate_limit=2.5,
            cache_dir=tmp_path / "cache",
            http_client=httpx.Client(),
        )
        client._last_request = 99.5  # 0.5s atrás
        client.fetch_day(date(2025, 5, 16))

        sleep_calls = [c for c in sleep_mock.call_args_list if c.args and c.args[0] > 0]
        assert len(sleep_calls) >= 1

    @respx.mock
    def test_sem_sleep_quando_tempo_suficiente(
        self,
        tmp_path: Path,
        mocker: pytest.MonkeyPatch,
        fixture_payload: dict,
    ) -> None:
        sleep_mock = mocker.patch("lotinha.extraction.api_client.time.sleep")
        monotonic_mock = mocker.patch("lotinha.extraction.api_client.time.monotonic")
        # simula: now=100.0, last_request=97.0 → elapsed=3.0 > rate_limit=2.5
        monotonic_mock.side_effect = [100.0, 100.0]

        respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        client = ApiClient(
            rate_limit=2.5,
            cache_dir=tmp_path / "cache",
            http_client=httpx.Client(),
        )
        client._last_request = 97.0  # 3.0s atrás
        client.fetch_day(date(2025, 5, 16))

        positive_sleeps = [c for c in sleep_mock.call_args_list if c.args and c.args[0] > 0]
        assert len(positive_sleeps) == 0


# ── fetch_range ────────────────────────────────────────────────────────────────

class TestFetchRange:
    @respx.mock
    def test_itera_dias_corretamente(
        self, client: ApiClient, fixture_payload: dict
    ) -> None:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        results = list(
            client.fetch_range(date(2025, 5, 16), date(2025, 5, 18))
        )
        dates = [r[0] for r in results]
        assert dates == [date(2025, 5, 16), date(2025, 5, 17), date(2025, 5, 18)]

    @respx.mock
    def test_404_gera_lista_vazia_sem_quebrar(self, client: ApiClient) -> None:
        respx.get(API_URL).mock(return_value=httpx.Response(404))
        results = list(client.fetch_range(date(2025, 5, 16), date(2025, 5, 16)))
        assert results[0][1] == []

    @respx.mock
    def test_progress_callback_chamado(
        self, client: ApiClient, fixture_payload: dict
    ) -> None:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        calls: list[tuple[int, int]] = []
        client.fetch_range(
            date(2025, 5, 16),
            date(2025, 5, 18),
            progress_callback=lambda atual, total: calls.append((atual, total)),
        )
        # Precisamos consumir o generator
        list(
            client.fetch_range(
                date(2025, 5, 16),
                date(2025, 5, 18),
                progress_callback=lambda a, t: calls.append((a, t)),
            )
        )
        assert (1, 3) in calls
        assert (3, 3) in calls

    @respx.mock
    def test_intervalo_unico_dia(
        self, client: ApiClient, fixture_payload: dict
    ) -> None:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=fixture_payload))
        results = list(client.fetch_range(date(2025, 5, 16), date(2025, 5, 16)))
        assert len(results) == 1
        assert len(results[0][1]) == 18
