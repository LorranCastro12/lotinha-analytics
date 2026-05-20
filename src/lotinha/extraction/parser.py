"""Parser: converte resposta JSON da API em entidades de domínio."""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict

from lotinha.core.domain import Sorteio
from lotinha.core.exceptions import ParseError

# ── Modelos Pydantic do payload bruto da API ───────────────────────────────────

class CatalogInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str


class GameInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    gameType: str
    gameVariant: str


class SorteioRaw(BaseModel):
    """Mapeamento direto de um item do array `data` retornado pela API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    drawnNumbers: list[int]
    gameDate: str
    drawDate: str
    catalog: CatalogInfo
    game: GameInfo


class ApiResponse(BaseModel):
    """Estrutura raiz da resposta da API."""

    model_config = ConfigDict(extra="ignore")

    type: str
    data: list[SorteioRaw]


# ── Funções de parsing ─────────────────────────────────────────────────────────

_CATALOG_RE = re.compile(r"^(.+?)\s+(\d{1,2})h$", re.IGNORECASE)


def parse_catalog_name(name: str) -> tuple[str, int]:
    """Extrai banca e hora de um nome de catálogo.

    Args:
        name: String como "LOTINHA PONTO 07h" ou "LOTINHA FEDERAL 19h".

    Returns:
        Tupla (banca, hora) onde hora é um inteiro 7..23.

    Raises:
        ParseError: Se o formato não for reconhecido.
    """
    match = _CATALOG_RE.match(name.strip())
    if not match:
        raise ParseError(f"Formato de catalog.name não reconhecido: {name!r}")
    banca = match.group(1).strip()
    hora = int(match.group(2))
    return banca, hora


def sorteio_raw_to_domain(raw: SorteioRaw, source: str = "api") -> Sorteio:
    """Converte um SorteioRaw em entidade de domínio Sorteio.

    Args:
        raw: Dados brutos validados pela API.
        source: Origem da extração ("api" ou "selenium").

    Returns:
        Entidade `Sorteio` validada pelo domínio.

    Raises:
        ParseError: Se a conversão falhar por dados inválidos.
    """
    try:
        banca, hora = parse_catalog_name(raw.catalog.name)
        data = date.fromisoformat(raw.gameDate)
    except (ValueError, ParseError) as exc:
        raise ParseError(f"Falha ao converter SorteioRaw {raw.id!r}: {exc}") from exc

    return Sorteio(
        data=data,
        hora=hora,
        banca=banca,
        numeros=sorted(raw.drawnNumbers),
        extracted_at=datetime.now(tz=UTC).replace(tzinfo=None),
        source=source,
        raw_payload=raw.model_dump_json(),
    )


def parse_api_response(payload: dict[str, object]) -> list[Sorteio]:
    """Converte o payload completo da API em lista de Sorteios.

    Args:
        payload: Dicionário com a estrutura retornada pelo endpoint.

    Returns:
        Lista de Sorteios válidos. Entradas com erro de parse são ignoradas
        com log de warning.

    Raises:
        ParseError: Se o payload não tiver o campo `data`.
    """
    if "data" not in payload:
        raise ParseError(f"Payload sem campo 'data': {json.dumps(payload)[:200]}")

    raw_list = payload["data"]
    if not isinstance(raw_list, list):
        raise ParseError("Campo 'data' não é uma lista")

    sorteios: list[Sorteio] = []
    for raw_dict in raw_list:
        try:
            raw = SorteioRaw.model_validate(raw_dict)
            sorteio = sorteio_raw_to_domain(raw)
            sorteios.append(sorteio)
        except Exception as exc:
            # Não quebra o pipeline por um sorteio malformado
            from loguru import logger
            logger.warning(f"Sorteio ignorado por erro de parse: {exc}")

    return sorteios
