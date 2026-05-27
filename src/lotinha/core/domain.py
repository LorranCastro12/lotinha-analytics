"""Entidades de domínio do sistema Lotinha."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from lotinha.core.exceptions import DomainValidationError

UNIVERSO = 25
N_SORTEADOS = 15
HORA_MIN = 7
HORA_MAX = 23


@dataclass
class Sorteio:
    """Resultado de um único sorteio da Lotinha.

    Args:
        data: Data do sorteio.
        hora: Hora do sorteio (7..23).
        banca: Nome da banca operadora.
        numeros: Lista dos 15 números sorteados (1..25), ordenada.
        extracted_at: Momento em que o registro entrou no banco.
        source: Origem do dado ("api" ou "selenium").
        raw_payload: Payload bruto da API (JSON serializado), para reprocessamento.
        id: Chave primária do banco (None antes de persistir).
    """

    data: date
    hora: int
    banca: str
    numeros: list[int]
    extracted_at: datetime
    source: str
    raw_payload: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not (HORA_MIN <= self.hora <= HORA_MAX):
            raise DomainValidationError(
                f"hora deve ser entre {HORA_MIN} e {HORA_MAX}, recebido: {self.hora}"
            )
        if not self.banca.strip():
            raise DomainValidationError("banca não pode ser vazia")
        if len(self.numeros) != N_SORTEADOS:
            raise DomainValidationError(
                f"numeros deve ter {N_SORTEADOS} elementos, recebido: {len(self.numeros)}"
            )
        if len(set(self.numeros)) != N_SORTEADOS:
            raise DomainValidationError("numeros contém duplicatas")
        if not all(1 <= n <= UNIVERSO for n in self.numeros):
            raise DomainValidationError(f"todos os números devem estar entre 1 e {UNIVERSO}")
        if self.source not in ("api", "selenium"):
            raise DomainValidationError(f"source inválido: {self.source!r}")

    @property
    def numeros_sorted(self) -> list[int]:
        return sorted(self.numeros)


@dataclass
class ExtractionLogEntry:
    """Registro de auditoria de uma tentativa de extração.

    Args:
        data: Data alvo da extração.
        banca: Nome da banca (ou None para extração de dia inteiro).
        hora: Hora específica (ou None para dia inteiro).
        status: "success", "error" ou "empty".
        error_message: Descrição do erro (None quando status != "error").
        timestamp: Momento da tentativa.
    """

    data: date
    status: str
    timestamp: datetime
    banca: str | None = None
    hora: int | None = None
    error_message: str | None = None

    _VALID_STATUSES = frozenset({"success", "error", "empty"})

    def __post_init__(self) -> None:
        if self.status not in self._VALID_STATUSES:
            raise DomainValidationError(
                f"status inválido: {self.status!r}. Esperado: {self._VALID_STATUSES}"
            )


@dataclass
class Prediction:
    """Palpite gerado pelo sistema para um (banca, hora, data) alvo.

    Args:
        data_alvo: Data para a qual o palpite foi gerado.
        hora: Hora do sorteio alvo.
        banca: Banca operadora alvo.
        estrategia: Nome da estratégia usada.
        numeros_preditos: Lista dos números recomendados (≤ 23).
        criado_em: Momento da geração.
        acertos: Número de acertos no sorteio real (None antes do resultado).
        id: Chave primária do banco (None antes de persistir).
    """

    data_alvo: date
    hora: int
    banca: str
    estrategia: str
    numeros_preditos: list[int]
    criado_em: datetime
    acertos: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not (17 <= len(self.numeros_preditos) <= 23):
            raise DomainValidationError(
                f"numeros_preditos deve ter entre 17 e 23 elementos, "
                f"recebido: {len(self.numeros_preditos)}"
            )
        if len(set(self.numeros_preditos)) != len(self.numeros_preditos):
            raise DomainValidationError("numeros_preditos contém duplicatas")
        if not all(1 <= n <= UNIVERSO for n in self.numeros_preditos):
            raise DomainValidationError(
                f"todos os números preditos devem estar entre 1 e {UNIVERSO}"
            )


@dataclass
class PredictionResult:
    """Resultado de uma predição com scores e confiança.

    Args:
        numeros: Lista dos números recomendados, ordenados por score desc.
        scores: Score individual de cada número (1..25).
        confidence: Confiança geral da predição (0..1).
        strategy_name: Nome da estratégia que gerou o resultado.
        metadata: Informações adicionais (ex: p-value do backtest, edge).
    """

    numeros: list[int]
    scores: dict[int, float]
    confidence: float
    strategy_name: str
    metadata: dict[str, Any] = field(default_factory=dict)
