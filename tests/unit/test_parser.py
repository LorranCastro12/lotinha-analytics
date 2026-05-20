"""Testes da Fase 2: extraction/parser.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lotinha.core.exceptions import ParseError
from lotinha.extraction.parser import (
    CatalogInfo,
    GameInfo,
    SorteioRaw,
    parse_api_response,
    parse_catalog_name,
    sorteio_raw_to_domain,
)

FIXTURE_PATH = Path("tests/fixtures/api_response_2025-05-16.json")


@pytest.fixture
def real_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _make_raw(
    catalog_name: str = "LOTINHA PONTO 07h",
    numeros: list[int] | None = None,
    game_date: str = "2025-05-16",
) -> SorteioRaw:
    if numeros is None:
        numeros = list(range(1, 16))
    return SorteioRaw(
        id="test-id",
        drawnNumbers=numeros,
        gameDate=game_date,
        drawDate=f"{game_date}T07:00:00.000-03:00",
        catalog=CatalogInfo(name=catalog_name),
        game=GameInfo(
            id="g-id",
            name=catalog_name,
            gameType="LOTINHA",
            gameVariant="PONTO",
        ),
    )


# ── parse_catalog_name ─────────────────────────────────────────────────────────

class TestParseCatalogName:
    def test_lotinha_ponto_07h(self) -> None:
        banca, hora = parse_catalog_name("LOTINHA PONTO 07h")
        assert banca == "LOTINHA PONTO"
        assert hora == 7

    def test_lotinha_federal_19h(self) -> None:
        banca, hora = parse_catalog_name("LOTINHA FEDERAL 19h")
        assert banca == "LOTINHA FEDERAL"
        assert hora == 19

    def test_lotinha_ponto_23h(self) -> None:
        banca, hora = parse_catalog_name("LOTINHA PONTO 23h")
        assert banca == "LOTINHA PONTO"
        assert hora == 23

    def test_ignora_espacos_extras(self) -> None:
        banca, hora = parse_catalog_name("  LOTINHA PONTO 07h  ")
        assert banca == "LOTINHA PONTO"
        assert hora == 7

    def test_formato_invalido_sem_hora(self) -> None:
        with pytest.raises(ParseError):
            parse_catalog_name("LOTINHA PONTO")

    def test_formato_invalido_vazio(self) -> None:
        with pytest.raises(ParseError):
            parse_catalog_name("")

    def test_formato_invalido_sem_banca(self) -> None:
        with pytest.raises(ParseError):
            parse_catalog_name("07h")

    def test_case_insensitive(self) -> None:
        banca, hora = parse_catalog_name("Lotinha Ponto 07H")
        assert hora == 7


# ── sorteio_raw_to_domain ──────────────────────────────────────────────────────

class TestSorteioRawToDomain:
    def test_converte_campos_basicos(self) -> None:
        from datetime import date
        raw = _make_raw()
        s = sorteio_raw_to_domain(raw)
        assert s.data == date(2025, 5, 16)
        assert s.hora == 7
        assert s.banca == "LOTINHA PONTO"
        assert s.source == "api"

    def test_numeros_ordenados(self) -> None:
        raw = _make_raw(numeros=[15, 1, 3, 7, 9, 11, 13, 5, 2, 4, 6, 8, 10, 12, 14])
        s = sorteio_raw_to_domain(raw)
        assert s.numeros == list(range(1, 16))

    def test_raw_payload_salvo(self) -> None:
        raw = _make_raw()
        s = sorteio_raw_to_domain(raw)
        assert s.raw_payload is not None
        payload = json.loads(s.raw_payload)
        assert payload["id"] == "test-id"

    def test_source_api(self) -> None:
        s = sorteio_raw_to_domain(_make_raw(), source="api")
        assert s.source == "api"

    def test_banca_federal(self) -> None:
        raw = _make_raw(catalog_name="LOTINHA FEDERAL 19h")
        s = sorteio_raw_to_domain(raw)
        assert s.banca == "LOTINHA FEDERAL"
        assert s.hora == 19

    def test_catalog_name_invalido_levanta_parse_error(self) -> None:
        raw = _make_raw(catalog_name="NOME INVALIDO SEM HORA")
        with pytest.raises(ParseError):
            sorteio_raw_to_domain(raw)


# ── parse_api_response ─────────────────────────────────────────────────────────

class TestParseApiResponse:
    def test_fixture_real_18_sorteios(self, real_fixture: dict) -> None:
        sorteios = parse_api_response(real_fixture)
        assert len(sorteios) == 18

    def test_fixture_real_bancas(self, real_fixture: dict) -> None:
        sorteios = parse_api_response(real_fixture)
        bancas = {s.banca for s in sorteios}
        assert "LOTINHA PONTO" in bancas
        assert "LOTINHA FEDERAL" in bancas

    def test_fixture_real_horarios(self, real_fixture: dict) -> None:
        sorteios = parse_api_response(real_fixture)
        horarios = {s.hora for s in sorteios}
        assert horarios == set(range(7, 24))

    def test_fixture_real_todos_15_numeros(self, real_fixture: dict) -> None:
        sorteios = parse_api_response(real_fixture)
        for s in sorteios:
            assert len(s.numeros) == 15
            assert all(1 <= n <= 25 for n in s.numeros)

    def test_fixture_real_todos_na_data_certa(self, real_fixture: dict) -> None:
        from datetime import date
        sorteios = parse_api_response(real_fixture)
        for s in sorteios:
            assert s.data == date(2025, 5, 16)

    def test_payload_sem_data_field_levanta_parse_error(self) -> None:
        with pytest.raises(ParseError):
            parse_api_response({"type": "success"})

    def test_payload_vazio_retorna_lista_vazia(self) -> None:
        sorteios = parse_api_response({"data": []})
        assert sorteios == []

    def test_entrada_malformada_ignorada_sem_crash(self) -> None:
        payload = {
            "data": [
                {"id": "bad", "invalid": True},  # malformado
                # sorteio válido
                {
                    "id": "ok",
                    "drawnNumbers": list(range(1, 16)),
                    "gameDate": "2025-05-16",
                    "drawDate": "2025-05-16T07:00:00.000-03:00",
                    "catalog": {"name": "LOTINHA PONTO 07h"},
                    "game": {
                        "id": "g",
                        "name": "LOTINHA PONTO 07h",
                        "gameType": "LOTINHA",
                        "gameVariant": "PONTO",
                    },
                },
            ]
        }
        sorteios = parse_api_response(payload)
        assert len(sorteios) == 1
