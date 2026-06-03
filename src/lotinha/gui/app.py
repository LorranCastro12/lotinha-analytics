"""Janela principal do Lotinha Analytics."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from lotinha.gui.theme import COLOR_PRIMARY
from lotinha.gui.views.analysis import AnalysisView
from lotinha.gui.views.backtesting import BacktestingView
from lotinha.gui.views.dashboard import DashboardView
from lotinha.gui.views.extraction import ExtractionView
from lotinha.gui.views.prediction import PredictionView
from lotinha.gui.views.reports_view import ReportsView


class App(QMainWindow):
    """Janela principal com QTabWidget de 6 abas."""

    def __init__(self, repo: Any, settings: Any) -> None:
        super().__init__()
        self._repo = repo
        self._settings = settings

        self.setWindowTitle("Lotinha Analytics")
        self.resize(1100, 760)
        self.setMinimumSize(900, 640)

        self._build()

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Cabeçalho ────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(50)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)

        title_lbl = QLabel("  Lotinha Analytics")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title_lbl.setFont(font)
        title_lbl.setStyleSheet(f"color: {COLOR_PRIMARY}; background: transparent;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        h_layout.addWidget(title_lbl)
        h_layout.addStretch()
        outer.addWidget(header)

        # ── Tabs ──────────────────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        outer.addWidget(tabs)

        tabs.addTab(DashboardView(repo=self._repo), "Dashboard")
        tabs.addTab(ExtractionView(repo=self._repo, settings=self._settings), "Extração")
        tabs.addTab(AnalysisView(repo=self._repo), "Análise")
        tabs.addTab(PredictionView(repo=self._repo), "Predição")
        tabs.addTab(BacktestingView(repo=self._repo, settings=self._settings), "Backtesting")
        tabs.addTab(ReportsView(repo=self._repo, settings=self._settings), "Relatórios")
