"""Configurações centrais do sistema via pydantic-settings."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações lidas de variáveis de ambiente / arquivo .env."""

    model_config = SettingsConfigDict(
        env_prefix="LOTINHA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Banco de dados
    db_path: Path = Field(default=Path("data/lotinha.db"), description="Caminho do SQLite")

    # API
    api_base_url: str = Field(
        default="https://api.pontodobicho.com",
        description="URL base da API",
    )
    api_rate_limit: Annotated[float, Field(ge=0.5, le=10.0)] = Field(
        default=1.5,
        description="Segundos mínimos entre requests",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Nível de log")
    log_dir: Path = Field(default=Path("logs"), description="Diretório de logs")

    # Cache e backups
    cache_dir: Path = Field(default=Path("data/cache"), description="Cache de payloads brutos")
    max_backups: Annotated[int, Field(ge=1, le=20)] = Field(
        default=5,
        description="Máximo de backups do banco mantidos",
    )

    # Prêmios (preenchidos pelo usuário via GUI ou .env)
    # Lista de valores para 11, 12, 13, 14, 15 acertos
    premios_por_faixa: list[float] = Field(
        default=[0.0, 0.0, 0.0, 0.0, 0.0],
        description="Prêmios por faixa de acertos (11..15)",
    )
    # Lista de custos para apostas com 17, 18, 19, 20, 21, 22, 23 números
    custo_apostas: list[float] = Field(
        default=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        description="Custo por quantidade de números apostados (17..23)",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level deve ser um de {allowed}")
        return upper

    @field_validator("premios_por_faixa")
    @classmethod
    def validate_premios(cls, v: list[float]) -> list[float]:
        if len(v) != 5:
            raise ValueError("premios_por_faixa deve ter exatamente 5 valores (faixas 11..15)")
        return v

    @field_validator("custo_apostas")
    @classmethod
    def validate_custos(cls, v: list[float]) -> list[float]:
        if len(v) != 7:
            raise ValueError("custo_apostas deve ter exatamente 7 valores (17..23 números)")
        return v

    def custo_para(self, n_numeros: int) -> float:
        """Retorna o custo da aposta para n_numeros (17..23)."""
        if n_numeros < 17 or n_numeros > 23:
            raise ValueError(f"n_numeros deve ser entre 17 e 23, recebido: {n_numeros}")
        return self.custo_apostas[n_numeros - 17]

    def premio_para(self, acertos: int) -> float:
        """Retorna o prêmio para a faixa de acertos (11..15)."""
        if acertos < 11 or acertos > 15:
            raise ValueError(f"acertos deve ser entre 11 e 15, recebido: {acertos}")
        return self.premios_por_faixa[acertos - 11]

    def ensure_dirs(self) -> None:
        """Cria diretórios necessários se não existirem."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        Path("data/backups").mkdir(parents=True, exist_ok=True)


# Instância global — importar com `from lotinha.config import settings`
settings = Settings()
