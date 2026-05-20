"""Modelos SQLAlchemy 2.0 (estilo Mapped[...]) para persistência da Lotinha."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SorteioModel(Base):
    """Resultado de um sorteio da Lotinha."""

    __tablename__ = "sorteios"
    __table_args__ = (
        UniqueConstraint("data", "hora", "banca", name="uq_sorteio_data_hora_banca"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora: Mapped[int] = mapped_column(Integer, nullable=False)
    banca: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    numeros: Mapped[str] = mapped_column(Text, nullable=False)          # JSON list[int]
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)     # "api"|"selenium"
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Sorteio {self.data} {self.hora:02d}h {self.banca}>"


class ExtractionLogModel(Base):
    """Auditoria de tentativas de extração."""

    __tablename__ = "extraction_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    banca: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hora: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)     # success|error|empty
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<ExtractionLog {self.data} status={self.status}>"


class PredictionModel(Base):
    """Palpites gerados pelo sistema (fecha o loop de validação)."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_alvo: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora: Mapped[int] = mapped_column(Integer, nullable=False)
    banca: Mapped[str] = mapped_column(String(100), nullable=False)
    estrategia: Mapped[str] = mapped_column(String(50), nullable=False)
    numeros_preditos: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list[int]
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    acertos: Mapped[int | None] = mapped_column(Integer, nullable=True)  # preenchido após resultado

    def __repr__(self) -> str:
        return f"<Prediction {self.data_alvo} {self.hora:02d}h {self.banca} {self.estrategia}>"
