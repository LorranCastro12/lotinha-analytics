"""Fallback via Selenium para quando a API falha persistentemente."""

from __future__ import annotations

from datetime import date

from lotinha.core.domain import Sorteio


class SeleniumFallback:
    """Extrator alternativo usando Selenium.

    Ativado apenas quando a API principal falha persistentemente.
    """

    def fetch_day(self, data: date) -> list[Sorteio]:  # pragma: no cover
        raise NotImplementedError(
            "Selenium fallback não implementado. "
            "Instale as dependências opcionais: `uv pip install -e '.[selenium]'`"
        )
