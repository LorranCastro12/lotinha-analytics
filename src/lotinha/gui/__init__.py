"""Interface gráfica do Lotinha Analytics (customtkinter)."""

from __future__ import annotations


def run() -> None:
    """Inicializa banco, repositório e abre a janela principal."""
    from lotinha.config import Settings
    from lotinha.gui.app import App
    from lotinha.storage.migrations import create_all_tables, create_engine_from_path
    from lotinha.storage.repository import SorteioRepository

    settings = Settings()
    settings.ensure_dirs()
    engine = create_engine_from_path(settings.db_path)
    create_all_tables(engine)
    repo = SorteioRepository(engine)

    app = App(repo=repo, settings=settings)
    app.mainloop()
