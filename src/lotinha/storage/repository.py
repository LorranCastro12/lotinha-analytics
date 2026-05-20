"""Repository pattern para acesso ao banco SQLite."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import pandas as pd
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from lotinha.core.domain import ExtractionLogEntry, Prediction, Sorteio
from lotinha.storage.models import (
    Base,
    ExtractionLogModel,
    PredictionModel,
    SorteioModel,
)

if TYPE_CHECKING:
    pass


class SorteioRepository:
    """Interface de persistência — a camada de análise nunca toca SQL direto.

    Args:
        engine: Engine SQLAlchemy já configurada.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        Base.metadata.create_all(engine)

    # ── Sorteios ───────────────────────────────────────────────────────────────

    def upsert(self, sorteio: Sorteio) -> None:
        """Insere ou atualiza um sorteio (idempotente por data+hora+banca)."""
        with Session(self._engine) as session:
            stmt = sqlite_insert(SorteioModel).values(
                data=sorteio.data,
                hora=sorteio.hora,
                banca=sorteio.banca,
                numeros=json.dumps(sorted(sorteio.numeros)),
                extracted_at=sorteio.extracted_at,
                source=sorteio.source,
                raw_payload=sorteio.raw_payload,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["data", "hora", "banca"],
                set_={
                    "numeros": stmt.excluded.numeros,
                    "extracted_at": stmt.excluded.extracted_at,
                    "source": stmt.excluded.source,
                    "raw_payload": stmt.excluded.raw_payload,
                },
            )
            session.execute(stmt)
            session.commit()

    def upsert_batch(self, sorteios: list[Sorteio]) -> int:
        """Insere/atualiza uma lista de sorteios. Retorna quantos foram processados."""
        if not sorteios:
            return 0
        with Session(self._engine) as session:
            for sorteio in sorteios:
                stmt = sqlite_insert(SorteioModel).values(
                    data=sorteio.data,
                    hora=sorteio.hora,
                    banca=sorteio.banca,
                    numeros=json.dumps(sorted(sorteio.numeros)),
                    extracted_at=sorteio.extracted_at,
                    source=sorteio.source,
                    raw_payload=sorteio.raw_payload,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["data", "hora", "banca"],
                    set_={
                        "numeros": stmt.excluded.numeros,
                        "extracted_at": stmt.excluded.extracted_at,
                        "source": stmt.excluded.source,
                        "raw_payload": stmt.excluded.raw_payload,
                    },
                )
                session.execute(stmt)
            session.commit()
        return len(sorteios)

    def get_resultados(
        self,
        banca: str | None = None,
        hora: int | None = None,
        desde: date | None = None,
        ate: date | None = None,
    ) -> pd.DataFrame:
        """Retorna sorteios filtrados como DataFrame.

        Columns: id, data, hora, banca, numeros (list[int]), extracted_at, source.
        """
        with Session(self._engine) as session:
            q = select(SorteioModel)
            if banca is not None:
                q = q.where(SorteioModel.banca == banca)
            if hora is not None:
                q = q.where(SorteioModel.hora == hora)
            if desde is not None:
                q = q.where(SorteioModel.data >= desde)
            if ate is not None:
                q = q.where(SorteioModel.data <= ate)
            q = q.order_by(SorteioModel.data, SorteioModel.hora, SorteioModel.banca)
            rows = session.execute(q).scalars().all()

        if not rows:
            return pd.DataFrame(
                columns=["id", "data", "hora", "banca", "numeros", "extracted_at", "source"]
            )

        records = [
            {
                "id": r.id,
                "data": r.data,
                "hora": r.hora,
                "banca": r.banca,
                "numeros": json.loads(r.numeros),
                "extracted_at": r.extracted_at,
                "source": r.source,
            }
            for r in rows
        ]
        return pd.DataFrame(records)

    def count_total(self) -> int:
        """Retorna total de sorteios no banco."""
        with Session(self._engine) as session:
            result = session.execute(select(func.count()).select_from(SorteioModel))
            return result.scalar_one()

    def latest_date(self) -> date | None:
        """Retorna a data mais recente com dados, ou None se o banco estiver vazio."""
        with Session(self._engine) as session:
            result = session.execute(select(func.max(SorteioModel.data)))
            return result.scalar_one_or_none()

    def list_bancas(self) -> list[str]:
        """Retorna lista de bancas distintas presentes no banco."""
        with Session(self._engine) as session:
            result = session.execute(
                select(SorteioModel.banca).distinct().order_by(SorteioModel.banca)
            )
            return [row[0] for row in result.all()]

    def list_horarios(self) -> list[int]:
        """Retorna lista de horários distintos presentes no banco."""
        with Session(self._engine) as session:
            result = session.execute(
                select(SorteioModel.hora).distinct().order_by(SorteioModel.hora)
            )
            return [row[0] for row in result.all()]

    def dates_with_data(self) -> set[date]:
        """Retorna conjunto de datas que possuem pelo menos 1 sorteio."""
        with Session(self._engine) as session:
            result = session.execute(select(SorteioModel.data).distinct())
            return {row[0] for row in result.all()}

    def get_all_as_dicts(self) -> list[dict[str, Any]]:
        """Retorna todos os sorteios como lista de dicionários (para export)."""
        with Session(self._engine) as session:
            rows = session.execute(
                select(SorteioModel).order_by(
                    SorteioModel.data, SorteioModel.hora, SorteioModel.banca
                )
            ).scalars().all()
            return [
                {
                    "data": r.data.isoformat(),
                    "hora": r.hora,
                    "banca": r.banca,
                    "numeros": json.loads(r.numeros),
                    "extracted_at": r.extracted_at.isoformat(),
                    "source": r.source,
                    "raw_payload": r.raw_payload,
                }
                for r in rows
            ]

    # ── ExtractionLog ──────────────────────────────────────────────────────────

    def log_extraction(self, entry: ExtractionLogEntry) -> None:
        """Registra tentativa de extração na tabela de auditoria."""
        with Session(self._engine) as session:
            log = ExtractionLogModel(
                data=entry.data,
                banca=entry.banca,
                hora=entry.hora,
                status=entry.status,
                error_message=entry.error_message,
                timestamp=entry.timestamp,
            )
            session.add(log)
            session.commit()

    # ── Predictions ────────────────────────────────────────────────────────────

    def save_prediction(self, prediction: Prediction) -> int:
        """Salva um palpite e retorna o id gerado."""
        with Session(self._engine) as session:
            model = PredictionModel(
                data_alvo=prediction.data_alvo,
                hora=prediction.hora,
                banca=prediction.banca,
                estrategia=prediction.estrategia,
                numeros_preditos=json.dumps(prediction.numeros_preditos),
                criado_em=prediction.criado_em,
                acertos=prediction.acertos,
            )
            session.add(model)
            session.commit()
            session.refresh(model)
            assert model.id is not None
            return model.id

    def update_prediction_acertos(self, prediction_id: int, acertos: int) -> None:
        """Preenche o campo acertos após o sorteio real."""
        with Session(self._engine) as session:
            model = session.get(PredictionModel, prediction_id)
            if model is not None:
                model.acertos = acertos
                session.commit()

    # ── Factory ────────────────────────────────────────────────────────────────

    @classmethod
    def from_url(cls, url: str) -> SorteioRepository:
        """Cria repositório a partir de uma URL SQLAlchemy (ex: 'sqlite:///data/lotinha.db')."""
        engine = create_engine(url, echo=False)
        return cls(engine)

    @classmethod
    def in_memory(cls) -> SorteioRepository:
        """Cria repositório em memória (útil para testes)."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        return cls(engine)

    def _sorteio_from_dict(self, d: dict[str, Any]) -> Sorteio:
        return Sorteio(
            data=date.fromisoformat(d["data"]),
            hora=d["hora"],
            banca=d["banca"],
            numeros=d["numeros"],
            extracted_at=datetime.fromisoformat(d["extracted_at"]),
            source=d["source"],
            raw_payload=d.get("raw_payload"),
        )
