"""Backup automático do banco SQLite."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from lotinha.core.exceptions import BackupError


def create_backup(
    db_path: Path,
    backup_dir: Path,
    max_backups: int = 5,
) -> Path:
    """Copia o banco SQLite para o diretório de backups.

    Args:
        db_path: Caminho do arquivo de banco a fazer backup.
        backup_dir: Diretório onde os backups são armazenados.
        max_backups: Número máximo de backups a manter (os mais antigos são removidos).

    Returns:
        Caminho do arquivo de backup criado.

    Raises:
        BackupError: Se o banco de origem não existir ou a cópia falhar.
    """
    if not db_path.exists():
        raise BackupError(f"Banco de dados não encontrado: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = _unique_backup_path(backup_dir)

    try:
        shutil.copy2(db_path, backup_path)
    except OSError as exc:
        raise BackupError(f"Falha ao criar backup: {exc}") from exc

    _cleanup_old_backups(backup_dir, max_backups)
    return backup_path


def _unique_backup_path(backup_dir: Path) -> Path:
    """Gera caminho de backup com nome único, mesmo sob alta frequência de chamadas."""
    base = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    candidate = backup_dir / f"lotinha_{base}.db"
    counter = 0
    while candidate.exists():
        counter += 1
        candidate = backup_dir / f"lotinha_{base}_{counter}.db"
    return candidate


def _cleanup_old_backups(backup_dir: Path, max_backups: int) -> None:
    """Remove backups excedentes, mantendo apenas os mais recentes."""
    backups = sorted(backup_dir.glob("lotinha_*.db"))
    excess = max(0, len(backups) - max_backups)
    for old in backups[:excess]:
        old.unlink(missing_ok=True)


def list_backups(backup_dir: Path) -> list[Path]:
    """Retorna lista de backups disponíveis, do mais antigo ao mais recente."""
    return sorted(backup_dir.glob("lotinha_*.db"))
