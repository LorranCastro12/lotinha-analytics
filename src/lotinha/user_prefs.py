"""Preferências do usuário persistidas em JSON entre sessões."""

from __future__ import annotations

import json
from pathlib import Path

_PREFS_FILE = Path("data/user_prefs.json")


class UserPrefs:
    """Preferências simples salvas em JSON; lidas na inicialização da GUI."""

    def __init__(self) -> None:
        self._data: dict = self._load()

    def _load(self) -> dict:
        if _PREFS_FILE.exists():
            try:
                return json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        _PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PREFS_FILE.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @property
    def reports_dir(self) -> str:
        return self._data.get("reports_dir", str(Path.home()))

    @reports_dir.setter
    def reports_dir(self, value: str) -> None:
        self._data["reports_dir"] = value
        self.save()
