"""Testes para geração de relatório PDF (Phase 9)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from lotinha.reporting.report import ReportConfig, generate_report


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_df(n: int = 30) -> pd.DataFrame:
    import random
    rng = random.Random(42)
    rows = []
    for i in range(n):
        numeros = sorted(rng.sample(range(1, 26), 15))
        rows.append({
            "id": i,
            "data": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
            "hora": 14,
            "banca": "Federal",
            "numeros": numeros,
            "extracted_at": pd.Timestamp.now(),
            "source": "api",
        })
    return pd.DataFrame(rows)


def _make_repo() -> MagicMock:
    repo = MagicMock()
    repo.count_total.return_value = 300
    repo.latest_date.return_value = pd.Timestamp("2024-12-31").date()
    repo.list_bancas.return_value = ["Federal", "Rio"]
    repo.list_horarios.return_value = [11, 14, 16, 18, 21]
    repo.dates_with_data.return_value = list(range(60))
    repo.get_resultados.return_value = _make_df()
    return repo


# ── ReportConfig ───────────────────────────────────────────────────────────────


class TestReportConfig:
    def test_defaults(self) -> None:
        cfg = ReportConfig()
        assert cfg.banca is None
        assert cfg.hora is None
        assert cfg.n_top == 5

    def test_custom_values(self) -> None:
        cfg = ReportConfig(banca="Federal", hora=14, n_top=10)
        assert cfg.banca == "Federal"
        assert cfg.hora == 14
        assert cfg.n_top == 10

    def test_none_defaults_allow_filtering(self) -> None:
        cfg = ReportConfig(banca=None, hora=None)
        assert cfg.banca is None
        assert cfg.hora is None


# ── generate_report ────────────────────────────────────────────────────────────


class TestGenerateReport:
    def test_creates_file(self, tmp_path: Path) -> None:
        output = tmp_path / "report.pdf"
        generate_report(_make_repo(), output)
        assert output.exists()

    def test_returns_output_path(self, tmp_path: Path) -> None:
        output = tmp_path / "report.pdf"
        result = generate_report(_make_repo(), output)
        assert result == output

    def test_output_is_valid_pdf(self, tmp_path: Path) -> None:
        output = tmp_path / "report.pdf"
        generate_report(_make_repo(), output)
        assert output.read_bytes()[:4] == b"%PDF"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        output = tmp_path / "sub" / "dir" / "report.pdf"
        generate_report(_make_repo(), output)
        assert output.exists()

    def test_with_banca_filter(self, tmp_path: Path) -> None:
        repo = _make_repo()
        output = tmp_path / "report.pdf"
        generate_report(repo, output, config=ReportConfig(banca="Federal"))
        repo.get_resultados.assert_called_with(banca="Federal", hora=None)

    def test_with_hora_filter(self, tmp_path: Path) -> None:
        repo = _make_repo()
        output = tmp_path / "report.pdf"
        generate_report(repo, output, config=ReportConfig(hora=14))
        repo.get_resultados.assert_called_with(banca=None, hora=14)

    def test_with_both_filters(self, tmp_path: Path) -> None:
        repo = _make_repo()
        output = tmp_path / "report.pdf"
        cfg = ReportConfig(banca="Rio", hora=21)
        generate_report(repo, output, config=cfg)
        repo.get_resultados.assert_called_with(banca="Rio", hora=21)

    def test_empty_dataframe_no_crash(self, tmp_path: Path) -> None:
        repo = _make_repo()
        repo.get_resultados.return_value = pd.DataFrame()
        output = tmp_path / "report.pdf"
        generate_report(repo, output)
        assert output.exists()

    def test_empty_bancas_no_crash(self, tmp_path: Path) -> None:
        repo = _make_repo()
        repo.list_bancas.return_value = []
        repo.list_horarios.return_value = []
        repo.count_total.return_value = 0
        repo.dates_with_data.return_value = []
        repo.get_resultados.return_value = pd.DataFrame()
        output = tmp_path / "report.pdf"
        generate_report(repo, output)
        assert output.exists()

    def test_default_config_used_when_none(self, tmp_path: Path) -> None:
        repo = _make_repo()
        output = tmp_path / "report.pdf"
        generate_report(repo, output, config=None)
        repo.get_resultados.assert_called_with(banca=None, hora=None)

    def test_file_size_nonzero(self, tmp_path: Path) -> None:
        output = tmp_path / "report.pdf"
        generate_report(_make_repo(), output)
        assert output.stat().st_size > 1024
