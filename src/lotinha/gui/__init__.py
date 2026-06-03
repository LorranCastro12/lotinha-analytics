"""Interface gráfica do Lotinha Analytics (PySide6)."""

from __future__ import annotations


def run() -> None:
    """Inicializa banco, repositório e abre a janela principal."""
    import sys

    from PySide6.QtWidgets import QApplication

    from lotinha.config import Settings
    from lotinha.gui.app import App
    from lotinha.gui.theme import APP_STYLE
    from lotinha.storage.migrations import create_all_tables, create_engine_from_path
    from lotinha.storage.repository import SorteioRepository

    settings = Settings()
    settings.ensure_dirs()
    engine = create_engine_from_path(settings.db_path)
    create_all_tables(engine)
    repo = SorteioRepository(engine)

    qapp = QApplication.instance() or QApplication(sys.argv)
    qapp.setStyle("Fusion")
    qapp.setStyleSheet(APP_STYLE)

    window = App(repo=repo, settings=settings)
    window.show()
    sys.exit(qapp.exec())
