"""Janela principal do Lotinha Analytics."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from lotinha.gui.views.analysis import AnalysisView
from lotinha.gui.views.backtesting import BacktestingView
from lotinha.gui.views.dashboard import DashboardView
from lotinha.gui.views.extraction import ExtractionView
from lotinha.gui.views.prediction import PredictionView


class App(ctk.CTk):
    """Janela principal com CTkTabview de 5 abas.

    Args:
        repo: Repositório de sorteios.
        settings: Configurações do sistema.
    """

    def __init__(self, repo: Any, settings: Any) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.title("Lotinha Analytics")
        self.geometry("1100x760")
        self.minsize(900, 640)

        self._repo = repo
        self._settings = settings

        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Cabeçalho
        header = ctk.CTkFrame(self, height=48, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            header,
            text="  Lotinha Analytics",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#2CC985",
        ).pack(side="left", padx=16, pady=8)

        # Tabs
        tabs = ctk.CTkTabview(self, anchor="nw")
        tabs.grid(row=1, column=0, padx=12, pady=(4, 12), sticky="nsew")

        tab_defs = [
            ("Dashboard",   self._make_dashboard),
            ("Extração",    self._make_extraction),
            ("Análise",     self._make_analysis),
            ("Predição",    self._make_prediction),
            ("Backtesting", self._make_backtesting),
        ]
        for name, factory in tab_defs:
            tab = tabs.add(name)
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)
            view = factory(tab)
            view.grid(row=0, column=0, sticky="nsew")

    # ── Factories ──────────────────────────────────────────────────────────

    def _make_dashboard(self, parent: Any) -> DashboardView:
        return DashboardView(parent, repo=self._repo)

    def _make_extraction(self, parent: Any) -> ExtractionView:
        return ExtractionView(parent, repo=self._repo, settings=self._settings)

    def _make_analysis(self, parent: Any) -> AnalysisView:
        return AnalysisView(parent, repo=self._repo)

    def _make_prediction(self, parent: Any) -> PredictionView:
        return PredictionView(parent, repo=self._repo)

    def _make_backtesting(self, parent: Any) -> BacktestingView:
        return BacktestingView(parent, repo=self._repo, settings=self._settings)
