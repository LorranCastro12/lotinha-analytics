"""Cria schema inicial: sorteios, extraction_log, predictions.

Revision ID: 0001
Revises:
Create Date: 2026-05-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sorteios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("hora", sa.Integer(), nullable=False),
        sa.Column("banca", sa.String(100), nullable=False),
        sa.Column("numeros", sa.Text(), nullable=False),
        sa.Column("extracted_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("data", "hora", "banca", name="uq_sorteio_data_hora_banca"),
    )
    op.create_index("ix_sorteios_data", "sorteios", ["data"])
    op.create_index("ix_sorteios_banca", "sorteios", ["banca"])

    op.create_table(
        "extraction_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("banca", sa.String(100), nullable=True),
        sa.Column("hora", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extraction_log_data", "extraction_log", ["data"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data_alvo", sa.Date(), nullable=False),
        sa.Column("hora", sa.Integer(), nullable=False),
        sa.Column("banca", sa.String(100), nullable=False),
        sa.Column("estrategia", sa.String(50), nullable=False),
        sa.Column("numeros_preditos", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("acertos", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_data_alvo", "predictions", ["data_alvo"])


def downgrade() -> None:
    op.drop_table("predictions")
    op.drop_table("extraction_log")
    op.drop_table("sorteios")
