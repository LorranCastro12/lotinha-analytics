"""Testes da Fase 1: storage (models, repository, gap_detector, backup, export/import)."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from lotinha.core.domain import ExtractionLogEntry, Prediction, Sorteio
from lotinha.core.exceptions import BackupError
from lotinha.core.exceptions import ImportError as LotinhaImportError
from lotinha.storage.backup import create_backup, list_backups
from lotinha.storage.export_import import (
    export_to_json,
    export_to_parquet,
    import_from_json,
    import_from_parquet,
)
from lotinha.storage.gap_detector import GapDetector
from lotinha.storage.migrations import create_all_tables, verify_schema
from lotinha.storage.repository import SorteioRepository

from .conftest import make_sorteio


# ── Helpers ────────────────────────────────────────────────────────────────────

def _s(
    data: date = date(2025, 5, 16),
    hora: int = 7,
    banca: str = "Lotinha Ponto",
    numeros: list[int] | None = None,
) -> Sorteio:
    return make_sorteio(data=data, hora=hora, banca=banca, numeros=numeros)


# ══════════════════════════════════════════════════════════════════════════════
# Domain entities
# ══════════════════════════════════════════════════════════════════════════════

class TestSorteioDomain:
    def test_valid_sorteio(self) -> None:
        s = _s()
        assert len(s.numeros) == 15

    def test_numeros_sorted_property(self) -> None:
        s = _s(numeros=[15, 1, 3, 7, 9, 11, 13, 5, 2, 4, 6, 8, 10, 12, 14])
        assert s.numeros_sorted == list(range(1, 16))

    def test_hora_invalida_baixa(self) -> None:
        with pytest.raises(Exception):
            _s(hora=6)

    def test_hora_invalida_alta(self) -> None:
        with pytest.raises(Exception):
            _s(hora=24)

    def test_numeros_errado_quantidade(self) -> None:
        with pytest.raises(Exception):
            _s(numeros=list(range(1, 14)))

    def test_numeros_duplicados(self) -> None:
        with pytest.raises(Exception):
            _s(numeros=[1] * 15)

    def test_numero_fora_do_universo(self) -> None:
        numeros = list(range(1, 15)) + [26]
        with pytest.raises(Exception):
            _s(numeros=numeros)

    def test_banca_vazia_invalida(self) -> None:
        with pytest.raises(Exception):
            make_sorteio(banca="   ")

    def test_source_invalido(self) -> None:
        with pytest.raises(Exception):
            make_sorteio(source="unknown")


class TestPredictionDomain:
    def test_valid_prediction(self) -> None:
        p = Prediction(
            data_alvo=date(2025, 5, 17),
            hora=8,
            banca="Lotinha Ponto",
            estrategia="frequency",
            numeros_preditos=list(range(1, 23)),
            criado_em=datetime.now(),
        )
        assert len(p.numeros_preditos) == 22

    def test_numeros_abaixo_do_minimo(self) -> None:
        with pytest.raises(Exception):
            Prediction(
                data_alvo=date(2025, 5, 17),
                hora=8,
                banca="B",
                estrategia="freq",
                numeros_preditos=list(range(1, 17)),  # 16 < 17
                criado_em=datetime.now(),
            )

    def test_numeros_acima_do_maximo(self) -> None:
        with pytest.raises(Exception):
            Prediction(
                data_alvo=date(2025, 5, 17),
                hora=8,
                banca="B",
                estrategia="freq",
                numeros_preditos=list(range(1, 24)),  # 23 > 22
                criado_em=datetime.now(),
            )

    def test_numeros_duplicados(self) -> None:
        with pytest.raises(Exception):
            Prediction(
                data_alvo=date(2025, 5, 17),
                hora=8,
                banca="B",
                estrategia="freq",
                numeros_preditos=[1] * 22,
                criado_em=datetime.now(),
            )


# ══════════════════════════════════════════════════════════════════════════════
# SorteioRepository
# ══════════════════════════════════════════════════════════════════════════════

class TestSorteioRepository:
    def test_banco_vazio_count_zero(self, repo: SorteioRepository) -> None:
        assert repo.count_total() == 0

    def test_banco_vazio_latest_date_none(self, repo: SorteioRepository) -> None:
        assert repo.latest_date() is None

    def test_banco_vazio_list_bancas(self, repo: SorteioRepository) -> None:
        assert repo.list_bancas() == []

    def test_banco_vazio_list_horarios(self, repo: SorteioRepository) -> None:
        assert repo.list_horarios() == []

    def test_upsert_novo(self, repo: SorteioRepository) -> None:
        repo.upsert(_s())
        assert repo.count_total() == 1

    def test_upsert_idempotente(self, repo: SorteioRepository) -> None:
        sorteio = _s()
        repo.upsert(sorteio)
        repo.upsert(sorteio)
        assert repo.count_total() == 1

    def test_upsert_atualiza_dados(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(numeros=list(range(1, 16))))
        repo.upsert(_s(numeros=list(range(11, 26))))  # mesma chave, novos números
        assert repo.count_total() == 1
        df = repo.get_resultados()
        assert df.iloc[0]["numeros"] == sorted(range(11, 26))

    def test_dois_sorteios_mesma_data_horas_diferentes(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(hora=7))
        repo.upsert(_s(hora=8))
        assert repo.count_total() == 2

    def test_dois_sorteios_mesma_data_bancas_diferentes(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(banca="Lotinha Ponto"))
        repo.upsert(_s(banca="Lotinha Federal"))
        assert repo.count_total() == 2

    def test_numeros_roundtrip(self, repo: SorteioRepository) -> None:
        numeros = [25, 1, 13, 7, 19, 3, 11, 5, 23, 9, 17, 15, 21, 2, 4]
        repo.upsert(_s(numeros=numeros))
        df = repo.get_resultados()
        assert df.iloc[0]["numeros"] == sorted(numeros)

    def test_list_bancas_distintas(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(banca="Lotinha Ponto", hora=7))
        repo.upsert(_s(banca="Lotinha Federal", hora=8))
        assert set(repo.list_bancas()) == {"Lotinha Ponto", "Lotinha Federal"}

    def test_list_horarios_distintos(self, repo: SorteioRepository) -> None:
        for h in [7, 9, 11]:
            repo.upsert(_s(hora=h))
        assert set(repo.list_horarios()) == {7, 9, 11}

    def test_latest_date(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(data=date(2025, 5, 16)))
        repo.upsert(_s(data=date(2025, 5, 20), hora=8))
        assert repo.latest_date() == date(2025, 5, 20)

    def test_get_resultados_sem_filtro(self, repo: SorteioRepository) -> None:
        for h in [7, 8, 9]:
            repo.upsert(_s(hora=h))
        df = repo.get_resultados()
        assert len(df) == 3

    def test_get_resultados_filtra_banca(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(banca="Lotinha Ponto", hora=7))
        repo.upsert(_s(banca="Lotinha Federal", hora=8))
        df = repo.get_resultados(banca="Lotinha Ponto")
        assert len(df) == 1
        assert df.iloc[0]["banca"] == "Lotinha Ponto"

    def test_get_resultados_filtra_hora(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(hora=7))
        repo.upsert(_s(hora=8))
        df = repo.get_resultados(hora=7)
        assert len(df) == 1
        assert df.iloc[0]["hora"] == 7

    def test_get_resultados_filtra_desde(self, repo: SorteioRepository) -> None:
        for d in [date(2025, 5, 16), date(2025, 5, 17), date(2025, 5, 18)]:
            repo.upsert(_s(data=d))
        df = repo.get_resultados(desde=date(2025, 5, 17))
        assert len(df) == 2

    def test_get_resultados_filtra_ate(self, repo: SorteioRepository) -> None:
        for d in [date(2025, 5, 16), date(2025, 5, 17), date(2025, 5, 18)]:
            repo.upsert(_s(data=d))
        df = repo.get_resultados(ate=date(2025, 5, 17))
        assert len(df) == 2

    def test_get_resultados_filtra_intervalo(self, repo: SorteioRepository) -> None:
        for d in [date(2025, 5, 16), date(2025, 5, 17), date(2025, 5, 18), date(2025, 5, 19)]:
            repo.upsert(_s(data=d))
        df = repo.get_resultados(desde=date(2025, 5, 17), ate=date(2025, 5, 18))
        assert len(df) == 2

    def test_get_resultados_vazio_retorna_dataframe(self, repo: SorteioRepository) -> None:
        df = repo.get_resultados()
        assert df.empty
        assert "numeros" in df.columns

    def test_dates_with_data(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(data=date(2025, 5, 16)))
        repo.upsert(_s(data=date(2025, 5, 18), hora=8))
        dates = repo.dates_with_data()
        assert date(2025, 5, 16) in dates
        assert date(2025, 5, 17) not in dates
        assert date(2025, 5, 18) in dates

    def test_upsert_batch(self, repo: SorteioRepository) -> None:
        sorteios = [_s(hora=h) for h in range(7, 12)]
        count = repo.upsert_batch(sorteios)
        assert count == 5
        assert repo.count_total() == 5

    def test_upsert_batch_idempotente(self, repo: SorteioRepository) -> None:
        sorteios = [_s(hora=h) for h in range(7, 10)]
        repo.upsert_batch(sorteios)
        repo.upsert_batch(sorteios)
        assert repo.count_total() == 3

    def test_upsert_batch_vazio(self, repo: SorteioRepository) -> None:
        count = repo.upsert_batch([])
        assert count == 0


class TestExtractionLog:
    def test_log_extraction_success(self, repo: SorteioRepository) -> None:
        entry = ExtractionLogEntry(
            data=date(2025, 5, 16),
            status="success",
            timestamp=datetime.now(),
        )
        repo.log_extraction(entry)  # não deve levantar exceção

    def test_log_extraction_error(self, repo: SorteioRepository) -> None:
        entry = ExtractionLogEntry(
            data=date(2025, 5, 16),
            banca="Lotinha Ponto",
            hora=7,
            status="error",
            error_message="HTTP 500",
            timestamp=datetime.now(),
        )
        repo.log_extraction(entry)

    def test_status_invalido(self) -> None:
        with pytest.raises(Exception):
            ExtractionLogEntry(
                data=date(2025, 5, 16),
                status="unknown",
                timestamp=datetime.now(),
            )


class TestPredictionPersistence:
    def test_save_prediction(self, repo: SorteioRepository) -> None:
        pred = Prediction(
            data_alvo=date(2025, 5, 17),
            hora=8,
            banca="Lotinha Ponto",
            estrategia="frequency",
            numeros_preditos=list(range(1, 23)),
            criado_em=datetime.now(),
        )
        pred_id = repo.save_prediction(pred)
        assert isinstance(pred_id, int)
        assert pred_id > 0

    def test_update_acertos(self, repo: SorteioRepository) -> None:
        pred = Prediction(
            data_alvo=date(2025, 5, 17),
            hora=8,
            banca="Lotinha Ponto",
            estrategia="frequency",
            numeros_preditos=list(range(1, 23)),
            criado_em=datetime.now(),
        )
        pred_id = repo.save_prediction(pred)
        repo.update_prediction_acertos(pred_id, 13)
        # não deve levantar exceção

    def test_update_acertos_id_inexistente(self, repo: SorteioRepository) -> None:
        repo.update_prediction_acertos(99999, 10)  # sem erro, apenas ignora


# ══════════════════════════════════════════════════════════════════════════════
# Migrations / Schema
# ══════════════════════════════════════════════════════════════════════════════

class TestMigrations:
    def test_create_all_tables(self, repo: SorteioRepository) -> None:
        assert verify_schema(repo._engine)

    def test_in_memory_factory(self) -> None:
        r = SorteioRepository.in_memory()
        assert r.count_total() == 0

    def test_from_url_factory(self, tmp_path: Path) -> None:
        url = f"sqlite:///{tmp_path / 'test.db'}"
        r = SorteioRepository.from_url(url)
        assert r.count_total() == 0


# ══════════════════════════════════════════════════════════════════════════════
# GapDetector
# ══════════════════════════════════════════════════════════════════════════════

class TestGapDetector:
    def test_sem_lacunas(self, repo: SorteioRepository) -> None:
        for d in [date(2025, 5, 16), date(2025, 5, 17), date(2025, 5, 18)]:
            repo.upsert(_s(data=d))
        detector = GapDetector(repo)
        assert detector.find_gaps(date(2025, 5, 16), date(2025, 5, 18)) == []

    def test_lacuna_unica(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(data=date(2025, 5, 16)))
        repo.upsert(_s(data=date(2025, 5, 18), hora=8))
        detector = GapDetector(repo)
        gaps = detector.find_gaps(date(2025, 5, 16), date(2025, 5, 18))
        assert gaps == [date(2025, 5, 17)]

    def test_multiplas_lacunas(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(data=date(2025, 5, 16)))
        repo.upsert(_s(data=date(2025, 5, 20), hora=8))
        detector = GapDetector(repo)
        gaps = detector.find_gaps(date(2025, 5, 16), date(2025, 5, 20))
        assert gaps == [date(2025, 5, d) for d in [17, 18, 19]]

    def test_banco_vazio_tudo_e_lacuna(self, repo: SorteioRepository) -> None:
        detector = GapDetector(repo)
        gaps = detector.find_gaps(date(2025, 5, 16), date(2025, 5, 18))
        assert len(gaps) == 3
        assert date(2025, 5, 16) in gaps
        assert date(2025, 5, 17) in gaps
        assert date(2025, 5, 18) in gaps

    def test_intervalo_invertido_retorna_vazio(self, repo: SorteioRepository) -> None:
        detector = GapDetector(repo)
        gaps = detector.find_gaps(date(2025, 5, 18), date(2025, 5, 16))
        assert gaps == []

    def test_intervalo_unico_dia_com_dado(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(data=date(2025, 5, 16)))
        detector = GapDetector(repo)
        gaps = detector.find_gaps(date(2025, 5, 16), date(2025, 5, 16))
        assert gaps == []

    def test_intervalo_unico_dia_sem_dado(self, repo: SorteioRepository) -> None:
        detector = GapDetector(repo)
        gaps = detector.find_gaps(date(2025, 5, 16), date(2025, 5, 16))
        assert gaps == [date(2025, 5, 16)]

    def test_count_gaps(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(data=date(2025, 5, 16)))
        repo.upsert(_s(data=date(2025, 5, 20), hora=8))
        detector = GapDetector(repo)
        assert detector.count_gaps(date(2025, 5, 16), date(2025, 5, 20)) == 3

    def test_find_all_gaps_banco_vazio(self, repo: SorteioRepository) -> None:
        detector = GapDetector(repo)
        assert detector.find_all_gaps() == []

    def test_find_all_gaps_com_dados(self, repo: SorteioRepository) -> None:
        repo.upsert(_s(data=date(2025, 5, 16)))
        repo.upsert(_s(data=date(2025, 5, 18), hora=8))
        detector = GapDetector(repo)
        gaps = detector.find_all_gaps()
        assert date(2025, 5, 17) in gaps


# ══════════════════════════════════════════════════════════════════════════════
# Backup
# ══════════════════════════════════════════════════════════════════════════════

class TestBackup:
    def test_cria_arquivo_backup(self, tmp_path: Path) -> None:
        db_path = tmp_path / "lotinha.db"
        db_path.write_bytes(b"SQLite")
        backup_dir = tmp_path / "backups"
        backup = create_backup(db_path, backup_dir)
        assert backup.exists()
        assert backup.name.startswith("lotinha_")

    def test_conteudo_identico(self, tmp_path: Path) -> None:
        db_path = tmp_path / "lotinha.db"
        db_path.write_bytes(b"SQLite fake content")
        backup_dir = tmp_path / "backups"
        backup = create_backup(db_path, backup_dir)
        assert backup.read_bytes() == db_path.read_bytes()

    def test_banco_inexistente_levanta_erro(self, tmp_path: Path) -> None:
        with pytest.raises(BackupError):
            create_backup(tmp_path / "nao_existe.db", tmp_path / "backups")

    def test_mantém_maximo_de_backups(self, tmp_path: Path) -> None:
        db_path = tmp_path / "lotinha.db"
        db_path.write_bytes(b"SQLite")
        backup_dir = tmp_path / "backups"
        for _ in range(7):
            create_backup(db_path, backup_dir, max_backups=3)
        backups = list_backups(backup_dir)
        assert len(backups) == 3

    def test_list_backups_vazio(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        assert list_backups(backup_dir) == []

    def test_list_backups_ordem_crescente(self, tmp_path: Path) -> None:
        db_path = tmp_path / "lotinha.db"
        db_path.write_bytes(b"x")
        backup_dir = tmp_path / "backups"
        for _ in range(3):
            create_backup(db_path, backup_dir, max_backups=10)
        backups = list_backups(backup_dir)
        nomes = [b.name for b in backups]
        assert nomes == sorted(nomes)


# ══════════════════════════════════════════════════════════════════════════════
# Export / Import
# ══════════════════════════════════════════════════════════════════════════════

class TestExportImportJSON:
    def test_export_json(self, repo: SorteioRepository, tmp_path: Path) -> None:
        for h in [7, 8, 9]:
            repo.upsert(_s(hora=h))
        out = tmp_path / "export.json"
        count = export_to_json(repo, out)
        assert count == 3
        assert out.exists()

    def test_export_json_formato(self, repo: SorteioRepository, tmp_path: Path) -> None:
        repo.upsert(_s())
        out = tmp_path / "export.json"
        export_to_json(repo, out)
        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert data[0]["banca"] == "Lotinha Ponto"
        assert isinstance(data[0]["numeros"], list)

    def test_import_json(self, tmp_path: Path) -> None:
        repo_origem = SorteioRepository.in_memory()
        for h in [7, 8, 9]:
            repo_origem.upsert(_s(hora=h))
        out = tmp_path / "export.json"
        export_to_json(repo_origem, out)

        repo_destino = SorteioRepository.in_memory()
        count = import_from_json(repo_destino, out)
        assert count == 3
        assert repo_destino.count_total() == 3

    def test_roundtrip_json(self, tmp_path: Path) -> None:
        repo_origem = SorteioRepository.in_memory()
        numeros = list(range(1, 16))
        repo_origem.upsert(_s(numeros=numeros))
        out = tmp_path / "export.json"
        export_to_json(repo_origem, out)

        repo_destino = SorteioRepository.in_memory()
        import_from_json(repo_destino, out)
        df = repo_destino.get_resultados()
        assert df.iloc[0]["numeros"] == sorted(numeros)
        assert df.iloc[0]["banca"] == "Lotinha Ponto"
        assert df.iloc[0]["hora"] == 7

    def test_import_json_idempotente(self, tmp_path: Path) -> None:
        repo_origem = SorteioRepository.in_memory()
        repo_origem.upsert(_s())
        out = tmp_path / "export.json"
        export_to_json(repo_origem, out)

        repo_destino = SorteioRepository.in_memory()
        import_from_json(repo_destino, out)
        import_from_json(repo_destino, out)
        assert repo_destino.count_total() == 1

    def test_import_json_arquivo_invalido(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("não é json", encoding="utf-8")
        repo = SorteioRepository.in_memory()
        with pytest.raises(LotinhaImportError):
            import_from_json(repo, bad_file)

    def test_export_json_banco_vazio(self, repo: SorteioRepository, tmp_path: Path) -> None:
        out = tmp_path / "export.json"
        count = export_to_json(repo, out)
        assert count == 0
        assert json.loads(out.read_text()) == []


class TestExportImportParquet:
    def test_roundtrip_parquet(self, tmp_path: Path) -> None:
        repo_origem = SorteioRepository.in_memory()
        for h in [7, 8, 9]:
            repo_origem.upsert(_s(hora=h))
        out = tmp_path / "export.parquet"
        count = export_to_parquet(repo_origem, out)
        assert count == 3
        assert out.exists()

        repo_destino = SorteioRepository.in_memory()
        imported = import_from_parquet(repo_destino, out)
        assert imported == 3
        assert repo_destino.count_total() == 3

    def test_parquet_preserva_numeros(self, tmp_path: Path) -> None:
        repo_origem = SorteioRepository.in_memory()
        numeros = list(range(11, 26))
        repo_origem.upsert(_s(numeros=numeros))
        out = tmp_path / "export.parquet"
        export_to_parquet(repo_origem, out)

        repo_destino = SorteioRepository.in_memory()
        import_from_parquet(repo_destino, out)
        df = repo_destino.get_resultados()
        assert df.iloc[0]["numeros"] == sorted(numeros)
