"""Fixtures compartilhadas para testes unitários."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine

from lotinha.core.domain import Sorteio
from lotinha.storage.repository import SorteioRepository

NUMEROS_PADRAO = list(range(1, 16))  # [1..15]


def make_sorteio(
    data: date = date(2025, 5, 16),
    hora: int = 7,
    banca: str = "Lotinha Ponto",
    numeros: list[int] | None = None,
    source: str = "api",
    raw_payload: str | None = '{"test": true}',
) -> Sorteio:
    """Factory de Sorteio para testes."""
    return Sorteio(
        data=data,
        hora=hora,
        banca=banca,
        numeros=numeros if numeros is not None else NUMEROS_PADRAO[:],
        extracted_at=datetime(2025, 5, 16, 12, 0, 0),
        source=source,
        raw_payload=raw_payload,
    )


@pytest.fixture
def repo() -> SorteioRepository:
    """Repositório em SQLite in-memory, tabelas criadas, zerado a cada teste."""
    return SorteioRepository.in_memory()


@pytest.fixture
def make_s() -> type:
    """Expõe a factory make_sorteio como fixture."""
    return make_sorteio
