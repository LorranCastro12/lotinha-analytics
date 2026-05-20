"""Testes da CLI — Fase 4."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from lotinha.extraction.orchestrator import ExtractionReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report(**kwargs: object) -> ExtractionReport:
    defaults: dict[str, object] = dict(
        inicio=date(2025, 1, 1),
        fim=date(2025, 1, 31),
        total_dias=31,
        extraidos=30,
        ja_presentes=0,
        falhas=0,
        vazios=1,
        erros=[],
        started_at=datetime.now(),
        finished_at=datetime.now(),
    )
    defaults.update(kwargs)
    return ExtractionReport(**defaults)  # type: ignore[arg-type]


def _make_repo(
    *,
    total: int = 500,
    latest: date | None = date(2025, 5, 16),
    bancas: list[str] | None = None,
    horarios: list[int] | None = None,
    dates: set[date] | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.count_total.return_value = total
    repo.latest_date.return_value = latest
    repo.list_bancas.return_value = bancas or ["LOTINHA FEDERAL", "LOTINHA PONTO"]
    repo.list_horarios.return_value = horarios or [7, 9, 11, 13, 15, 17, 19, 21, 23]
    repo.dates_with_data.return_value = dates or {date(2025, 5, i) for i in range(1, 17)}
    return repo


def _make_settings(db_path: Path | None = None) -> MagicMock:
    s = MagicMock()
    s.api_base_url = "https://api.pontodobicho.com"
    s.api_rate_limit = 0.0
    s.db_path = db_path or Path("/tmp/lotinha_test.db")
    return s


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def cli():
    from lotinha.cli.commands import cli as _cli
    return _cli


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

class TestStatusCommand:
    def test_exibe_total_sorteios(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        repo = _make_repo(total=1234)
        settings = _make_settings(tmp_path / "db.sqlite")
        with patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "1234" in result.output

    def test_exibe_bancas(self, runner: CliRunner, cli: object) -> None:
        repo = _make_repo(bancas=["LOTINHA FEDERAL", "LOTINHA PONTO"])
        settings = _make_settings()
        with patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)):
            result = runner.invoke(cli, ["status"])
        assert "LOTINHA FEDERAL" in result.output
        assert "LOTINHA PONTO" in result.output

    def test_exibe_horarios(self, runner: CliRunner, cli: object) -> None:
        repo = _make_repo(horarios=[7, 19, 23])
        settings = _make_settings()
        with patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)):
            result = runner.invoke(cli, ["status"])
        assert "7h" in result.output
        assert "19h" in result.output

    def test_banco_vazio(self, runner: CliRunner, cli: object) -> None:
        repo = _make_repo(total=0, latest=None, bancas=[], horarios=[], dates=set())
        settings = _make_settings()
        with patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "—" in result.output

    def test_exibe_data_mais_recente(self, runner: CliRunner, cli: object) -> None:
        repo = _make_repo(latest=date(2025, 5, 16))
        settings = _make_settings()
        with patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)):
            result = runner.invoke(cli, ["status"])
        assert "2025-05-16" in result.output


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

class TestExtractCommand:
    def _patch_orchestrator(self, report: ExtractionReport) -> object:
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.extract_range.return_value = report
        mock_cls.return_value = mock_instance
        return mock_cls

    def test_extrai_intervalo_valido(self, runner: CliRunner, cli: object) -> None:
        report = _make_report(extraidos=30, falhas=0, vazios=1)
        repo = _make_repo()
        settings = _make_settings()
        mock_cls = self._patch_orchestrator(report)

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.ExtractionOrchestrator", mock_cls),
            patch("lotinha.cli.commands.ApiClient"),
        ):
            result = runner.invoke(cli, ["extract", "--inicio", "2025-01-01", "--fim", "2025-01-31"])

        assert result.exit_code == 0
        assert "extraídos=30" in result.output

    def test_saida_com_falha_retorna_exit_1(self, runner: CliRunner, cli: object) -> None:
        report = _make_report(falhas=2, erros=[(date(2025, 1, 5), "HTTP 503")])
        repo = _make_repo()
        settings = _make_settings()
        mock_cls = self._patch_orchestrator(report)

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.ExtractionOrchestrator", mock_cls),
            patch("lotinha.cli.commands.ApiClient"),
        ):
            result = runner.invoke(cli, ["extract", "--inicio", "2025-01-01", "--fim", "2025-01-31"])

        assert result.exit_code == 1

    def test_data_invalida_retorna_erro(self, runner: CliRunner, cli: object) -> None:
        result = runner.invoke(cli, ["extract", "--inicio", "nao-eh-data", "--fim", "2025-01-31"])
        assert result.exit_code != 0

    def test_inicio_maior_que_fim_retorna_erro(self, runner: CliRunner, cli: object) -> None:
        repo = _make_repo()
        settings = _make_settings()

        with patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)):
            result = runner.invoke(cli, ["extract", "--inicio", "2025-02-01", "--fim", "2025-01-01"])

        assert result.exit_code != 0

    def test_exibe_backup_path_quando_criado(self, runner: CliRunner, cli: object) -> None:
        bp = Path("/tmp/backup_test.db")
        report = _make_report(backup_path=bp)
        repo = _make_repo()
        settings = _make_settings()
        mock_cls = self._patch_orchestrator(report)

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.ExtractionOrchestrator", mock_cls),
            patch("lotinha.cli.commands.ApiClient"),
        ):
            result = runner.invoke(cli, ["extract", "--inicio", "2025-01-01", "--fim", "2025-01-01"])

        assert str(bp) in result.output

    def test_passa_skip_existing_para_orchestrator(self, runner: CliRunner, cli: object) -> None:
        report = _make_report()
        repo = _make_repo()
        settings = _make_settings()
        mock_cls = self._patch_orchestrator(report)
        mock_instance = mock_cls.return_value

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.ExtractionOrchestrator", mock_cls),
            patch("lotinha.cli.commands.ApiClient"),
        ):
            runner.invoke(cli, ["extract", "--inicio", "2025-01-01", "--fim", "2025-01-01", "--no-skip-existing"])

        _, kwargs = mock_instance.extract_range.call_args
        assert kwargs.get("skip_existing") is False

    def test_requer_inicio_e_fim(self, runner: CliRunner, cli: object) -> None:
        result = runner.invoke(cli, ["extract"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# gaps
# ---------------------------------------------------------------------------

class TestGapsCommand:
    def test_sem_lacunas(self, runner: CliRunner, cli: object) -> None:
        repo = _make_repo()
        settings = _make_settings()
        mock_detector = MagicMock()
        mock_detector.return_value.find_all_gaps.return_value = []

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.GapDetector", mock_detector),
        ):
            result = runner.invoke(cli, ["gaps"])

        assert result.exit_code == 0
        assert "Nenhuma lacuna" in result.output

    def test_lista_lacunas(self, runner: CliRunner, cli: object) -> None:
        gaps_list = [date(2025, 3, 10), date(2025, 3, 15)]
        repo = _make_repo()
        settings = _make_settings()
        mock_detector = MagicMock()
        mock_detector.return_value.find_all_gaps.return_value = gaps_list

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.GapDetector", mock_detector),
        ):
            result = runner.invoke(cli, ["gaps"])

        assert "2025-03-10" in result.output
        assert "2025-03-15" in result.output
        assert "2 lacuna" in result.output

    def test_gaps_com_intervalo(self, runner: CliRunner, cli: object) -> None:
        repo = _make_repo()
        settings = _make_settings()
        mock_detector = MagicMock()
        mock_instance = mock_detector.return_value
        mock_instance.find_gaps.return_value = [date(2025, 2, 14)]

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.GapDetector", mock_detector),
        ):
            result = runner.invoke(cli, ["gaps", "--inicio", "2025-02-01", "--fim", "2025-02-28"])

        mock_instance.find_gaps.assert_called_once_with(date(2025, 2, 1), date(2025, 2, 28))
        assert "2025-02-14" in result.output


# ---------------------------------------------------------------------------
# recover-gaps
# ---------------------------------------------------------------------------

class TestRecoverGapsCommand:
    def _patch_orchestrator(self, report: ExtractionReport) -> object:
        mock_cls = MagicMock()
        mock_cls.return_value.recover_gaps.return_value = report
        return mock_cls

    def test_sem_lacunas(self, runner: CliRunner, cli: object) -> None:
        report = _make_report(total_dias=0, extraidos=0, falhas=0, vazios=0)
        repo = _make_repo()
        settings = _make_settings()
        mock_cls = self._patch_orchestrator(report)

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.ExtractionOrchestrator", mock_cls),
            patch("lotinha.cli.commands.ApiClient"),
        ):
            result = runner.invoke(cli, ["recover-gaps"])

        assert result.exit_code == 0
        assert "Nenhuma lacuna" in result.output

    def test_recupera_lacunas(self, runner: CliRunner, cli: object) -> None:
        report = _make_report(total_dias=5, extraidos=5, falhas=0, vazios=0)
        repo = _make_repo()
        settings = _make_settings()
        mock_cls = self._patch_orchestrator(report)

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.ExtractionOrchestrator", mock_cls),
            patch("lotinha.cli.commands.ApiClient"),
        ):
            result = runner.invoke(cli, ["recover-gaps"])

        assert result.exit_code == 0
        assert "extraídos=5" in result.output

    def test_falhas_retorna_exit_1(self, runner: CliRunner, cli: object) -> None:
        report = _make_report(total_dias=5, extraidos=3, falhas=2)
        repo = _make_repo()
        settings = _make_settings()
        mock_cls = self._patch_orchestrator(report)

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.ExtractionOrchestrator", mock_cls),
            patch("lotinha.cli.commands.ApiClient"),
        ):
            result = runner.invoke(cli, ["recover-gaps"])

        assert result.exit_code == 1

    def test_passa_intervalo_para_orchestrator(self, runner: CliRunner, cli: object) -> None:
        report = _make_report(total_dias=0)
        repo = _make_repo()
        settings = _make_settings()
        mock_cls = MagicMock()
        mock_instance = mock_cls.return_value
        mock_instance.recover_gaps.return_value = report

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.ExtractionOrchestrator", mock_cls),
            patch("lotinha.cli.commands.ApiClient"),
        ):
            runner.invoke(cli, ["recover-gaps", "--inicio", "2025-01-01", "--fim", "2025-03-31"])

        _, kwargs = mock_instance.recover_gaps.call_args
        assert kwargs.get("inicio") == date(2025, 1, 1)
        assert kwargs.get("fim") == date(2025, 3, 31)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

class TestExportCommand:
    def test_exporta_json(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        repo = _make_repo()
        settings = _make_settings()
        output = tmp_path / "out.json"

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.export_to_json", return_value=42) as mock_fn,
        ):
            result = runner.invoke(cli, ["export", "--output", str(output)])

        assert result.exit_code == 0
        mock_fn.assert_called_once()
        assert "42" in result.output

    def test_exporta_parquet(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        repo = _make_repo()
        settings = _make_settings()
        output = tmp_path / "out.parquet"

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.export_to_parquet", return_value=10) as mock_fn,
        ):
            result = runner.invoke(cli, ["export", "--output", str(output), "--format", "parquet"])

        assert result.exit_code == 0
        mock_fn.assert_called_once()

    def test_requer_output(self, runner: CliRunner, cli: object) -> None:
        result = runner.invoke(cli, ["export"])
        assert result.exit_code != 0

    def test_formato_invalido(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        result = runner.invoke(cli, ["export", "--output", str(tmp_path / "f.xyz"), "--format", "xml"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------

class TestImportCommand:
    def test_importa_json(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        input_file = tmp_path / "data.json"
        input_file.write_text("[]")
        repo = _make_repo()
        settings = _make_settings()

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.import_from_json", return_value=55) as mock_fn,
        ):
            result = runner.invoke(cli, ["import", "--input", str(input_file)])

        assert result.exit_code == 0
        mock_fn.assert_called_once()
        assert "55" in result.output

    def test_importa_parquet(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        input_file = tmp_path / "data.parquet"
        input_file.touch()
        repo = _make_repo()
        settings = _make_settings()

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.import_from_parquet", return_value=7) as mock_fn,
        ):
            result = runner.invoke(
                cli, ["import", "--input", str(input_file), "--format", "parquet"]
            )

        assert result.exit_code == 0
        mock_fn.assert_called_once()

    def test_arquivo_inexistente_retorna_erro(self, runner: CliRunner, cli: object) -> None:
        result = runner.invoke(cli, ["import", "--input", "/nao/existe.json"])
        assert result.exit_code != 0

    def test_requer_input(self, runner: CliRunner, cli: object) -> None:
        result = runner.invoke(cli, ["import"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# --db-path option (grupo principal)
# ---------------------------------------------------------------------------

class TestDbPathOption:
    def test_db_path_passado_para_get_repo(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        custom_db = tmp_path / "custom.db"
        repo = _make_repo()
        settings = _make_settings(custom_db)

        captured: dict[str, object] = {}

        def fake_get_repo(ctx: object) -> tuple[MagicMock, MagicMock, Path]:
            import click
            assert isinstance(ctx, click.Context)
            captured["db_path"] = ctx.obj.get("db_path")
            return repo, settings, custom_db

        with patch("lotinha.cli.commands._get_repo", side_effect=fake_get_repo):
            runner.invoke(cli, ["--db-path", str(custom_db), "status"])

        assert captured.get("db_path") == custom_db


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

class TestReportCommand:
    def test_gera_pdf(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        output = tmp_path / "report.pdf"
        repo = _make_repo()
        settings = _make_settings()

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.generate_report", return_value=output) as mock_gen,
        ):
            result = runner.invoke(cli, ["report", "--output", str(output)])

        assert result.exit_code == 0
        mock_gen.assert_called_once()

    def test_exibe_caminho_gerado(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        output = tmp_path / "report.pdf"
        repo = _make_repo()
        settings = _make_settings()

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.generate_report", return_value=output),
        ):
            result = runner.invoke(cli, ["report", "--output", str(output)])

        assert str(output) in result.output

    def test_passa_banca_para_config(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        from lotinha.reporting.report import ReportConfig

        output = tmp_path / "report.pdf"
        repo = _make_repo()
        settings = _make_settings()

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.generate_report", return_value=output) as mock_gen,
        ):
            runner.invoke(cli, ["report", "--output", str(output), "--banca", "Federal"])

        _, kwargs = mock_gen.call_args
        cfg: ReportConfig = kwargs["config"]
        assert cfg.banca == "Federal"

    def test_passa_horario_para_config(self, runner: CliRunner, cli: object, tmp_path: Path) -> None:
        from lotinha.reporting.report import ReportConfig

        output = tmp_path / "report.pdf"
        repo = _make_repo()
        settings = _make_settings()

        with (
            patch("lotinha.cli.commands._get_repo", return_value=(repo, settings, settings.db_path)),
            patch("lotinha.cli.commands.generate_report", return_value=output) as mock_gen,
        ):
            runner.invoke(cli, ["report", "--output", str(output), "--horario", "14"])

        _, kwargs = mock_gen.call_args
        cfg: ReportConfig = kwargs["config"]
        assert cfg.hora == 14

    def test_requer_output(self, runner: CliRunner, cli: object) -> None:
        result = runner.invoke(cli, ["report"])
        assert result.exit_code != 0
