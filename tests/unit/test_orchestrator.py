"""Testes da Fase 3: ExtractionOrchestrator."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lotinha.core.domain import Sorteio
from lotinha.core.exceptions import ApiServerError, DateNotFoundError, RateLimitExceededError
from lotinha.extraction.orchestrator import ExtractionOrchestrator, ExtractionReport
from lotinha.storage.repository import SorteioRepository

from .conftest import make_sorteio


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_api(sorteios_by_date: dict[date, list[Sorteio]] | None = None) -> MagicMock:
    """Cria mock de ApiClient que retorna sorteios configurados por data."""
    api = MagicMock()
    if sorteios_by_date is not None:
        api.fetch_day.side_effect = lambda d: sorteios_by_date.get(d, [])
    else:
        api.fetch_day.return_value = []
    return api


def _orch(
    api: MagicMock,
    repo: SorteioRepository,
    tmp_path: Path | None = None,
    db_path: Path | None = None,
) -> ExtractionOrchestrator:
    return ExtractionOrchestrator(
        api_client=api,
        repo=repo,
        backup_dir=tmp_path / "backups" if tmp_path else None,
        db_path=db_path,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ExtractionReport
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractionReport:
    def test_campos_basicos(self) -> None:
        r = ExtractionReport(
            inicio=date(2025, 5, 16),
            fim=date(2025, 5, 18),
            total_dias=3,
            extraidos=2,
            ja_presentes=1,
            falhas=0,
            vazios=0,
            erros=[],
            started_at=datetime.now(),
        )
        assert r.total_dias == 3
        assert r.sucesso is True

    def test_sucesso_false_quando_ha_falhas(self) -> None:
        r = ExtractionReport(
            inicio=date(2025, 5, 16),
            fim=date(2025, 5, 16),
            total_dias=1,
            extraidos=0,
            ja_presentes=0,
            falhas=1,
            vazios=0,
            erros=[(date(2025, 5, 16), "HTTP 500")],
            started_at=datetime.now(),
        )
        assert r.sucesso is False


# ══════════════════════════════════════════════════════════════════════════════
# extract_range — comportamento básico
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractRangeBasico:
    def test_banco_vazio_tenta_todos_os_dias(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = _make_api()
        orch = _orch(api, repo, tmp_path)
        orch.extract_range(date(2025, 5, 16), date(2025, 5, 18), backup_before=False)
        assert api.fetch_day.call_count == 3

    def test_dias_com_dados_sao_pulados(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        repo.upsert(make_sorteio(data=date(2025, 5, 16)))
        repo.upsert(make_sorteio(data=date(2025, 5, 18), hora=8))
        api = _make_api()
        orch = _orch(api, repo, tmp_path)
        orch.extract_range(date(2025, 5, 16), date(2025, 5, 18), backup_before=False)
        # Apenas 2025-05-17 faltando
        assert api.fetch_day.call_count == 1
        assert api.fetch_day.call_args[0][0] == date(2025, 5, 17)

    def test_skip_existing_false_extrai_todos(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        repo.upsert(make_sorteio(data=date(2025, 5, 16)))
        api = _make_api({date(2025, 5, 16): [make_sorteio(data=date(2025, 5, 16))]})
        orch = _orch(api, repo, tmp_path)
        orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16),
            skip_existing=False,
            backup_before=False,
        )
        assert api.fetch_day.call_count == 1

    def test_intervalo_unico_dia(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        s = make_sorteio(data=date(2025, 5, 16))
        api = _make_api({date(2025, 5, 16): [s]})
        orch = _orch(api, repo, tmp_path)
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=False
        )
        assert report.extraidos == 1
        assert repo.count_total() == 1

    def test_intervalo_invertido_nao_faz_requests(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = _make_api()
        orch = _orch(api, repo, tmp_path)
        report = orch.extract_range(
            date(2025, 5, 18), date(2025, 5, 16), backup_before=False
        )
        assert api.fetch_day.call_count == 0
        assert report.total_dias == 0


# ══════════════════════════════════════════════════════════════════════════════
# Persistência e idempotência
# ══════════════════════════════════════════════════════════════════════════════

class TestIdempotencia:
    def test_reextrair_nao_duplica(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        s = make_sorteio(data=date(2025, 5, 16))
        api = _make_api({date(2025, 5, 16): [s]})
        orch = _orch(api, repo, tmp_path)
        orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16),
            skip_existing=False, backup_before=False,
        )
        orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16),
            skip_existing=False, backup_before=False,
        )
        assert repo.count_total() == 1

    def test_sorteios_persistidos_no_banco(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        sorteios = [
            make_sorteio(data=date(2025, 5, 16), hora=h)
            for h in range(7, 10)
        ]
        api = _make_api({date(2025, 5, 16): sorteios})
        orch = _orch(api, repo, tmp_path)
        orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=False
        )
        assert repo.count_total() == 3


# ══════════════════════════════════════════════════════════════════════════════
# Relatório de extração
# ══════════════════════════════════════════════════════════════════════════════

class TestRelatorio:
    def test_conta_extraidos_corretamente(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = _make_api({
            date(2025, 5, 16): [make_sorteio(data=date(2025, 5, 16))],
            date(2025, 5, 17): [make_sorteio(data=date(2025, 5, 17), hora=8)],
            date(2025, 5, 18): [],  # sem dados
        })
        orch = _orch(api, repo, tmp_path)
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 18), backup_before=False
        )
        assert report.extraidos == 2
        assert report.vazios == 1
        assert report.falhas == 0
        assert report.total_dias == 3

    def test_conta_ja_presentes(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        repo.upsert(make_sorteio(data=date(2025, 5, 16)))
        api = _make_api({date(2025, 5, 17): [make_sorteio(data=date(2025, 5, 17))]})
        orch = _orch(api, repo, tmp_path)
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 17), backup_before=False
        )
        assert report.ja_presentes == 1
        assert report.extraidos == 1

    def test_tempo_de_execucao_preenchido(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = _make_api()
        orch = _orch(api, repo, tmp_path)
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=False
        )
        assert report.finished_at is not None
        assert report.finished_at >= report.started_at


# ══════════════════════════════════════════════════════════════════════════════
# Tratamento de falhas
# ══════════════════════════════════════════════════════════════════════════════

class TestFalhas:
    def test_falha_em_1_dia_continua_os_outros(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = MagicMock()
        api.fetch_day.side_effect = [
            ApiServerError("HTTP 500"),
            [make_sorteio(data=date(2025, 5, 17))],
            [make_sorteio(data=date(2025, 5, 18))],
        ]
        orch = _orch(api, repo, tmp_path)
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 18), backup_before=False
        )
        assert report.falhas == 1
        assert report.extraidos == 2
        assert len(report.erros) == 1
        assert report.erros[0][0] == date(2025, 5, 16)

    def test_429_contabilizado_como_falha(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = MagicMock()
        api.fetch_day.side_effect = RateLimitExceededError(retry_after=1)
        orch = _orch(api, repo, tmp_path)
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=False
        )
        assert report.falhas == 1

    def test_date_not_found_contabilizado_como_vazio(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = MagicMock()
        api.fetch_day.side_effect = DateNotFoundError("2025-05-16", 404)
        orch = _orch(api, repo, tmp_path)
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=False
        )
        assert report.vazios == 1
        assert report.falhas == 0

    def test_todas_falhas_sucesso_false(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = MagicMock()
        api.fetch_day.side_effect = ApiServerError("boom")
        orch = _orch(api, repo, tmp_path)
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=False
        )
        assert report.sucesso is False


# ══════════════════════════════════════════════════════════════════════════════
# Progress callback
# ══════════════════════════════════════════════════════════════════════════════

class TestProgressCallback:
    def test_callback_chamado_por_dia(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = _make_api()
        calls: list[tuple[int, int, date]] = []
        orch = _orch(api, repo, tmp_path)
        orch.extract_range(
            date(2025, 5, 16),
            date(2025, 5, 18),
            backup_before=False,
            progress_callback=lambda atual, total, d: calls.append((atual, total, d)),
        )
        assert len(calls) == 3
        assert calls[0] == (1, 3, date(2025, 5, 16))
        assert calls[2] == (3, 3, date(2025, 5, 18))

    def test_callback_none_nao_explode(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = _make_api()
        orch = _orch(api, repo, tmp_path)
        orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16),
            backup_before=False,
            progress_callback=None,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Backup automático
# ══════════════════════════════════════════════════════════════════════════════

class TestBackupAutomatico:
    def test_backup_criado_antes_da_extracao(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "lotinha.db"
        db_path.write_bytes(b"SQLite fake content")
        backup_dir = tmp_path / "backups"

        api = _make_api()
        orch = ExtractionOrchestrator(
            api_client=api,
            repo=repo,
            backup_dir=backup_dir,
            db_path=db_path,
        )
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=True
        )
        assert report.backup_path is not None
        assert report.backup_path.exists()
        assert len(list(backup_dir.glob("lotinha_*.db"))) >= 1

    def test_backup_false_nao_cria_backup(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "lotinha.db"
        db_path.write_bytes(b"SQLite fake")
        backup_dir = tmp_path / "backups"

        api = _make_api()
        orch = ExtractionOrchestrator(
            api_client=api, repo=repo, backup_dir=backup_dir, db_path=db_path
        )
        report = orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=False
        )
        assert report.backup_path is None

    def test_backup_sem_db_path_nao_explode(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = _make_api()
        orch = ExtractionOrchestrator(
            api_client=api, repo=repo, backup_dir=tmp_path / "backups", db_path=None
        )
        orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# recover_gaps
# ══════════════════════════════════════════════════════════════════════════════

class TestRecoverGaps:
    def test_banco_vazio_nao_faz_requests(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = _make_api()
        orch = _orch(api, repo, tmp_path)
        report = orch.recover_gaps()
        assert api.fetch_day.call_count == 0
        assert report.total_dias == 0

    def test_recupera_lacunas_existentes(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        # dias 16 e 18 presentes → 17 é lacuna
        repo.upsert(make_sorteio(data=date(2025, 5, 16)))
        repo.upsert(make_sorteio(data=date(2025, 5, 18), hora=8))
        api = _make_api()
        orch = _orch(api, repo, tmp_path)
        report = orch.recover_gaps(fim=date(2025, 5, 18))
        assert api.fetch_day.call_count == 1
        assert api.fetch_day.call_args[0][0] == date(2025, 5, 17)
        assert report.total_dias == 1

    def test_sem_lacunas_nao_faz_requests(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        for d in [date(2025, 5, 16), date(2025, 5, 17), date(2025, 5, 18)]:
            repo.upsert(make_sorteio(data=d))
        api = _make_api()
        orch = _orch(api, repo, tmp_path)
        report = orch.recover_gaps(fim=date(2025, 5, 18))
        assert api.fetch_day.call_count == 0
        assert report.total_dias == 0

    def test_fim_customizado(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        repo.upsert(make_sorteio(data=date(2025, 5, 16)))
        api = _make_api()
        orch = _orch(api, repo, tmp_path)
        orch.recover_gaps(fim=date(2025, 5, 18))
        # lacunas 17 e 18
        assert api.fetch_day.call_count == 2


# ══════════════════════════════════════════════════════════════════════════════
# Extraction log
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractionLog:
    def test_log_registrado_apos_extracao(
        self, repo: SorteioRepository, tmp_path: Path
    ) -> None:
        api = _make_api({date(2025, 5, 16): [make_sorteio(data=date(2025, 5, 16))]})
        orch = _orch(api, repo, tmp_path)
        # deve executar sem erros (log é interno)
        orch.extract_range(
            date(2025, 5, 16), date(2025, 5, 16), backup_before=False
        )
