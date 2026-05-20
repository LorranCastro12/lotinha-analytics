"""Testes da Fase 0: config e logging_setup."""

from __future__ import annotations

from pathlib import Path

import pytest

from lotinha.config import Settings


class TestSettings:
    def test_defaults(self) -> None:
        s = Settings()
        assert s.db_path == Path("data/lotinha.db")
        assert s.api_rate_limit == 1.5
        assert s.log_level == "INFO"
        assert s.max_backups == 5

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOTINHA_API_RATE_LIMIT", "3.0")
        monkeypatch.setenv("LOTINHA_LOG_LEVEL", "debug")
        s = Settings()
        assert s.api_rate_limit == 3.0
        assert s.log_level == "DEBUG"

    def test_invalid_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOTINHA_LOG_LEVEL", "INVALID")
        with pytest.raises(Exception):
            Settings()

    def test_invalid_rate_limit_too_low(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOTINHA_API_RATE_LIMIT", "0.1")
        with pytest.raises(Exception):
            Settings()

    def test_custo_para(self) -> None:
        s = Settings(custo_apostas=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
        assert s.custo_para(17) == 1.0
        assert s.custo_para(23) == 7.0

    def test_custo_para_fora_do_range(self) -> None:
        s = Settings()
        with pytest.raises(ValueError):
            s.custo_para(16)
        with pytest.raises(ValueError):
            s.custo_para(24)

    def test_premio_para(self) -> None:
        s = Settings(premios_por_faixa=[10.0, 20.0, 50.0, 100.0, 500.0])
        assert s.premio_para(11) == 10.0
        assert s.premio_para(15) == 500.0

    def test_premio_para_fora_do_range(self) -> None:
        s = Settings()
        with pytest.raises(ValueError):
            s.premio_para(10)
        with pytest.raises(ValueError):
            s.premio_para(16)

    def test_premios_tamanho_errado(self) -> None:
        with pytest.raises(Exception):
            Settings(premios_por_faixa=[1.0, 2.0])

    def test_custos_tamanho_errado(self) -> None:
        with pytest.raises(Exception):
            Settings(custo_apostas=[1.0, 2.0])

    def test_ensure_dirs(self, tmp_path: Path) -> None:
        s = Settings(
            db_path=tmp_path / "data" / "lotinha.db",
            log_dir=tmp_path / "logs",
            cache_dir=tmp_path / "cache",
        )
        s.ensure_dirs()
        assert (tmp_path / "data").exists()
        assert (tmp_path / "logs").exists()
        assert (tmp_path / "cache").exists()


class TestLoggingSetup:
    def test_setup_creates_log_dir(self, tmp_path: Path) -> None:
        from lotinha.logging_setup import setup_logging

        log_dir = tmp_path / "logs"
        setup_logging(log_dir, level="DEBUG")
        assert log_dir.exists()

    def test_setup_accepts_all_levels(self, tmp_path: Path) -> None:
        from lotinha.logging_setup import setup_logging

        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            setup_logging(tmp_path / "logs", level=level)
