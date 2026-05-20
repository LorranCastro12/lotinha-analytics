"""Fixtures globais do pytest."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Executa testes de integração que chamam APIs reais",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: chama APIs reais")
    config.addinivalue_line("markers", "slow: testes lentos (ex: treino ML)")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="use --run-integration para rodar")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
