"""Hierarquia de exceções do domínio Lotinha."""

from __future__ import annotations


class LotinhaError(Exception):
    """Base de todas as exceções do sistema."""


# ── Extração / API ─────────────────────────────────────────────────────────────

class ExtractionError(LotinhaError):
    """Erro genérico de extração."""


class ApiError(ExtractionError):
    """Erro ao comunicar com a API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitExceededError(ApiError):
    """HTTP 429 esgotou todas as tentativas."""

    def __init__(self, retry_after: int | None = None) -> None:
        super().__init__("Rate limit excedido após todas as tentativas", status_code=429)
        self.retry_after = retry_after


class ApiServerError(ApiError):
    """HTTP 5xx — servidor com problema."""


class DateNotFoundError(ApiError):
    """HTTP 4xx ≠ 429 — data inválida ou sem dados."""

    def __init__(self, date_str: str, status_code: int) -> None:
        super().__init__(f"Data sem dados na API: {date_str}", status_code=status_code)
        self.date_str = date_str


class ParseError(ExtractionError):
    """Falha ao converter resposta da API em entidades de domínio."""


# ── Armazenamento ──────────────────────────────────────────────────────────────

class StorageError(LotinhaError):
    """Erro de persistência."""


class MigrationError(StorageError):
    """Falha ao aplicar migration do banco."""


class BackupError(StorageError):
    """Falha ao criar ou restaurar backup."""


class ExportError(StorageError):
    """Falha ao exportar dados."""


class ImportError(StorageError):
    """Falha ao importar dados."""


# ── Análise / Predição ─────────────────────────────────────────────────────────

class AnalysisError(LotinhaError):
    """Erro no módulo de análise."""


class InsufficientDataError(AnalysisError):
    """Histórico insuficiente para treinar a estratégia."""

    def __init__(self, required: int, available: int) -> None:
        super().__init__(f"Necessário {required} sorteios, disponíveis {available}")
        self.required = required
        self.available = available


class PredictionError(AnalysisError):
    """Erro ao gerar predição."""


# ── Domínio ────────────────────────────────────────────────────────────────────

class DomainValidationError(LotinhaError):
    """Violação de regra de negócio na entidade de domínio."""
