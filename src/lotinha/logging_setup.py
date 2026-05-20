"""Configuração centralizada de logging via loguru."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_dir: Path, level: str = "INFO") -> None:
    """Configura loguru com handlers de console e arquivo rotativo.

    Args:
        log_dir: Diretório onde os arquivos de log serão gravados.
        level: Nível mínimo de log (DEBUG, INFO, WARNING, ERROR).
    """
    logger.remove()  # remove handler padrão do stderr

    fmt_console = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    )
    fmt_file = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{line} — "
        "{message}"
    )

    logger.add(sys.stderr, format=fmt_console, level=level, colorize=True)

    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "lotinha_{time:YYYY-MM-DD}.log",
        format=fmt_file,
        level=level,
        rotation="00:00",    # novo arquivo à meia-noite
        retention="30 days",
        compression="gz",
        encoding="utf-8",
    )

    logger.debug(f"Logging configurado: level={level}, dir={log_dir}")
