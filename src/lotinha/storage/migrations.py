"""Helpers para criação e migração do schema via SQLAlchemy e Alembic."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, inspect, text

from lotinha.storage.models import Base


def create_engine_from_path(db_path: Path) -> Engine:
    """Cria engine SQLite a partir de um caminho de arquivo.

    Args:
        db_path: Caminho do arquivo .db (criado se não existir).

    Returns:
        Engine SQLAlchemy configurada.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path.as_posix()}"
    return create_engine(url, echo=False)


def create_all_tables(engine: Engine) -> None:
    """Cria todas as tabelas definidas nos models (idempotente).

    Usa SQLAlchemy direto — adequado para testes e primeira inicialização.

    Args:
        engine: Engine SQLAlchemy alvo.
    """
    Base.metadata.create_all(engine)


def drop_all_tables(engine: Engine) -> None:
    """Remove todas as tabelas (para testes)."""
    Base.metadata.drop_all(engine)


def verify_schema(engine: Engine) -> bool:
    """Verifica se todas as tabelas esperadas existem.

    Args:
        engine: Engine SQLAlchemy alvo.

    Returns:
        True se o schema estiver completo.
    """
    expected = {"sorteios", "extraction_log", "predictions"}
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    return expected.issubset(existing)


def run_pragma_optimizations(engine: Engine) -> None:
    """Aplica otimizações SQLite para melhor performance em leitura."""
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.execute(text("PRAGMA cache_size=-64000"))   # 64 MB
        conn.execute(text("PRAGMA temp_store=MEMORY"))
        conn.commit()
