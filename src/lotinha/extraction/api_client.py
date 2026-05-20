"""Cliente HTTP para a API pontodobicho.com com retry, rate-limit e cache em disco."""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable, Iterator
from datetime import date, timedelta
from pathlib import Path

import httpx
from loguru import logger

from lotinha.core.domain import Sorteio
from lotinha.core.exceptions import (
    ApiServerError,
    DateNotFoundError,
    RateLimitExceededError,
)
from lotinha.extraction.parser import parse_api_response

_API_PATH = "/numeric-games/results/list"
_GAME_TYPE = "lotinha"
_BACKOFF_SECONDS = [2, 4, 8, 16, 32]
_JITTER_FACTOR = 0.2
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class ApiClient:
    """Cliente para a API pontodobicho.com.

    Implementa:
    - Rate-limiting interno configurável
    - Retry para 429 (lendo Retry-After) e 5xx (backoff exponencial)
    - Cache em disco dos payloads brutos por data
    - Sem retry para 4xx ≠ 429

    Args:
        base_url: URL base da API.
        rate_limit: Intervalo mínimo em segundos entre requests consecutivos.
        cache_dir: Diretório para cache de payloads.
        http_client: Cliente httpx injetável (útil para testes).
        max_attempts: Número máximo de tentativas por request.
    """

    def __init__(
        self,
        base_url: str = "https://api.pontodobicho.com",
        rate_limit: float = 2.5,
        cache_dir: Path | None = None,
        http_client: httpx.Client | None = None,
        max_attempts: int = 5,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._rate_limit = rate_limit
        self._cache_dir = cache_dir or Path("data/cache")
        self._http = http_client or httpx.Client(timeout=15.0)
        self._max_attempts = max_attempts
        self._last_request: float = 0.0

    # ── API pública ────────────────────────────────────────────────────────────

    def fetch_day(self, data: date) -> list[Sorteio]:
        """Busca todos os sorteios de um dia.

        Verifica cache antes de fazer request à rede. Em caso de sucesso,
        salva o payload bruto em cache para reprocessamento futuro.

        Args:
            data: Data alvo do sorteio.

        Returns:
            Lista de Sorteios do dia (pode ser vazia se não houver dados).

        Raises:
            DateNotFoundError: HTTP 4xx (sem retry).
            ApiServerError: HTTP 5xx após esgotar tentativas.
            RateLimitExceededError: HTTP 429 após esgotar tentativas.
        """
        cached = self._load_cache(data)
        if cached is not None:
            logger.debug(f"Cache hit: {data}")
            return parse_api_response(cached)

        raw = self._fetch_raw(data)
        self._save_cache(data, raw)
        return parse_api_response(raw)

    def fetch_range(
        self,
        inicio: date,
        fim: date,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Iterator[tuple[date, list[Sorteio]]]:
        """Itera sobre um intervalo de datas, buscando sorteios de cada dia.

        Args:
            inicio: Data inicial (inclusiva).
            fim: Data final (inclusiva).
            progress_callback: Callable(atual, total) chamado a cada dia processado.

        Yields:
            Tuplas (data, sorteios). Em caso de falha, sorteios é lista vazia.
        """
        days = [(inicio + timedelta(days=i)) for i in range((fim - inicio).days + 1)]
        total = len(days)

        for idx, current in enumerate(days, start=1):
            try:
                sorteios = self.fetch_day(current)
                yield current, sorteios
            except DateNotFoundError:
                logger.warning(f"Data sem dados na API: {current}")
                yield current, []
            except (ApiServerError, RateLimitExceededError) as exc:
                logger.error(f"Falha ao buscar {current}: {exc}")
                yield current, []

            if progress_callback:
                progress_callback(idx, total)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _fetch_raw(self, data: date) -> dict[str, object]:
        """Executa o request HTTP com retry e rate-limit."""
        url = f"{self._base_url}{_API_PATH}"
        params: dict[str, str] = {"date": data.isoformat(), "gameType": _GAME_TYPE}

        for attempt in range(self._max_attempts):
            self._apply_rate_limit()

            try:
                resp = self._http.get(url, params=params, headers=_DEFAULT_HEADERS)
            except httpx.RequestError as exc:
                logger.warning(f"Erro de rede (tentativa {attempt + 1}): {exc}")
                if attempt == self._max_attempts - 1:
                    raise ApiServerError(
                        f"Falha de rede após {self._max_attempts} tentativas: {exc}"
                    ) from exc
                self._sleep_backoff(attempt)
                continue

            if resp.status_code == 200:
                result: dict[str, object] = resp.json()
                return result

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                if attempt == self._max_attempts - 1:
                    raise RateLimitExceededError(retry_after=retry_after)
                logger.warning(
                    f"429 Rate-limited — Retry-After: {retry_after}s "
                    f"(tentativa {attempt + 1}/{self._max_attempts})"
                )
                time.sleep(retry_after)
                continue

            if resp.status_code >= 500:
                logger.warning(f"HTTP {resp.status_code} (tentativa {attempt + 1})")
                if attempt == self._max_attempts - 1:
                    raise ApiServerError(
                        f"HTTP {resp.status_code} após {self._max_attempts} tentativas",
                        status_code=resp.status_code,
                    )
                self._sleep_backoff(attempt)
                continue

            # 4xx ≠ 429 — não retenta
            raise DateNotFoundError(date_str=data.isoformat(), status_code=resp.status_code)

        raise ApiServerError("Tentativas esgotadas")  # pragma: no cover

    def _apply_rate_limit(self) -> None:
        """Garante o intervalo mínimo entre requests consecutivos."""
        now = time.monotonic()
        elapsed = now - self._last_request
        wait = self._rate_limit - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _sleep_backoff(self, attempt: int) -> None:
        """Dorme com backoff exponencial ±20% jitter."""
        base = _BACKOFF_SECONDS[min(attempt, len(_BACKOFF_SECONDS) - 1)]
        jitter = random.uniform(-_JITTER_FACTOR * base, _JITTER_FACTOR * base)
        sleep_time = max(0.0, base + jitter)
        logger.debug(f"Backoff: {sleep_time:.2f}s")
        time.sleep(sleep_time)

    def _cache_path(self, data: date) -> Path:
        return self._cache_dir / f"{data.isoformat()}.json"

    def _load_cache(self, data: date) -> dict[str, object] | None:
        path = self._cache_path(data)
        if not path.exists():
            return None
        try:
            result: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
            return result
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Cache corrompido para {data}, ignorando: {exc}")
            return None

    def _save_cache(self, data: date, raw: dict[str, object]) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._cache_path(data).write_text(
                json.dumps(raw, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning(f"Falha ao salvar cache para {data}: {exc}")
