"""Tema dark elegante para o Lotinha Analytics (PySide6)."""

from __future__ import annotations

COLOR_PRIMARY = "#2CC985"
COLOR_SECONDARY = "#F4A000"
COLOR_ERROR = "#FF5555"
COLOR_INFO = "#4FC3F7"
COLOR_WARNING = "#FF8080"

BG_DARK = "#0f0f17"
BG_PANEL = "#1a1a2a"
BG_INPUT = "#1f1f30"
BG_HOVER = "#252538"
BORDER = "#2e2e44"
TEXT_PRIMARY = "#e2e2e8"
TEXT_SECONDARY = "#8080a0"

MATPLOTLIB_STYLE = {
    "fig_facecolor": "#0f0f17",
    "ax_facecolor": "#1a1a2a",
    "tick_color": "#8080a0",
    "label_color": "#a0a0bc",
    "title_color": "#e2e2e8",
    "spine_color": "#2e2e44",
    "grid_color": "#252538",
}

APP_STYLE = f"""
/* ── Base ────────────────────────────────────────────────────────────── */
QMainWindow, QDialog {{
    background-color: {BG_DARK};
}}

QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Noto Sans", "SF Pro Display", Arial, sans-serif;
    font-size: 13px;
}}

/* ── Header ─────────────────────────────────────────────────────────── */
QWidget#header {{
    background-color: #09090f;
    border-bottom: 1px solid {BORDER};
}}

/* ── Cards / painéis ────────────────────────────────────────────────── */
QFrame#card {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QWidget#transparent_frame {{
    background: transparent;
}}

/* ── Tabs ────────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background-color: {BG_DARK};
    padding-top: 4px;
}}

QTabWidget::tab-bar {{
    alignment: left;
}}

QTabBar {{
    background: transparent;
}}

QTabBar::tab {{
    background-color: {BG_PANEL};
    color: {TEXT_SECONDARY};
    padding: 10px 22px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border-bottom: 2px solid transparent;
    font-size: 13px;
}}

QTabBar::tab:selected {{
    background-color: {BG_DARK};
    color: {COLOR_PRIMARY};
    border-bottom: 2px solid {COLOR_PRIMARY};
    font-weight: bold;
}}

QTabBar::tab:hover:!selected {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

/* ── Botões principais ──────────────────────────────────────────────── */
QPushButton {{
    background-color: transparent;
    color: {COLOR_PRIMARY};
    border: 2px solid {COLOR_PRIMARY};
    border-radius: 7px;
    padding: 8px 22px;
    font-weight: bold;
    font-size: 13px;
    min-height: 34px;
}}

QPushButton:hover {{
    background-color: {COLOR_PRIMARY};
    color: #000000;
    border-color: {COLOR_PRIMARY};
}}

QPushButton:pressed {{
    background-color: #1fa870;
    color: #000000;
    border-color: #1fa870;
}}

QPushButton:disabled {{
    background-color: transparent;
    color: #4a4a60;
    border: 2px solid #3a3a58;
}}

/* Botão laranja */
QPushButton#btn_orange {{
    background-color: transparent;
    color: {COLOR_SECONDARY};
    border: 2px solid {COLOR_SECONDARY};
}}

QPushButton#btn_orange:hover {{
    background-color: {COLOR_SECONDARY};
    color: #000000;
    border-color: {COLOR_SECONDARY};
}}

QPushButton#btn_orange:pressed {{
    background-color: #c07800;
    color: #000000;
    border-color: #c07800;
}}

QPushButton#btn_orange:disabled {{
    background-color: transparent;
    color: #4a4a60;
    border: 2px solid #3a3a58;
}}

/* Botão pequeno / utilitário */
QPushButton#btn_small {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    padding: 6px 12px;
    font-weight: normal;
    min-height: 28px;
}}

QPushButton#btn_small:hover {{
    background-color: {BG_HOVER};
    border-color: {COLOR_PRIMARY};
    color: {COLOR_PRIMARY};
}}

/* ── Entradas de texto ──────────────────────────────────────────────── */
QLineEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {COLOR_PRIMARY};
    selection-color: #09090f;
    min-height: 28px;
}}

QLineEdit:focus {{
    border-color: {COLOR_PRIMARY};
    background-color: #222235;
}}

QLineEdit:disabled {{
    color: #4a4a60;
    background-color: #141420;
}}

/* ── ComboBox ────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 28px;
}}

QComboBox:focus {{
    border-color: {COLOR_PRIMARY};
}}

QComboBox:disabled {{
    color: #4a4a60;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {TEXT_SECONDARY};
    width: 0;
    height: 0;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    selection-background-color: {COLOR_PRIMARY};
    selection-color: #09090f;
    border: 1px solid {BORDER};
    outline: none;
    padding: 4px;
}}

/* ── TextEdit (log) ─────────────────────────────────────────────────── */
QTextEdit {{
    background-color: #09090f;
    color: #9090b0;
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-family: "Consolas", "Fira Code", "Cascadia Code", monospace;
    font-size: 12px;
    padding: 4px;
    selection-background-color: {COLOR_PRIMARY};
    selection-color: #09090f;
}}

/* ── ProgressBar ────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {BG_INPUT};
    border: none;
    border-radius: 5px;
    height: 10px;
    color: transparent;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLOR_PRIMARY};
    border-radius: 5px;
}}

/* ── CheckBox ───────────────────────────────────────────────────────── */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {BORDER};
    border-radius: 4px;
    background-color: {BG_INPUT};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_PRIMARY};
    border-color: {COLOR_PRIMARY};
}}

QCheckBox::indicator:hover {{
    border-color: {COLOR_PRIMARY};
}}

/* ── Slider ─────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background-color: {BG_INPUT};
    height: 6px;
    border-radius: 3px;
    border: 1px solid {BORDER};
}}

QSlider::sub-page:horizontal {{
    background-color: {COLOR_PRIMARY};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {COLOR_PRIMARY};
    border: 2px solid {BG_DARK};
    width: 18px;
    height: 18px;
    border-radius: 9px;
    margin: -7px 0;
}}

QSlider::handle:horizontal:hover {{
    background-color: #3ae0a0;
}}

/* ── ScrollBar ──────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {BG_PANEL};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #5a5a78;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {BG_PANEL};
    height: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {BORDER};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #5a5a78;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* ── ScrollArea ─────────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ── Labels ─────────────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    color: {TEXT_PRIMARY};
}}

QLabel#title {{
    font-size: 20px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}

QLabel#section_title {{
    font-size: 14px;
    font-weight: bold;
}}

QLabel#label_muted {{
    color: {TEXT_SECONDARY};
}}

QLabel#metric_value {{
    font-size: 20px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}

/* ── Tooltip ────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
"""


def make_card() -> "QFrame":  # noqa: F821
    """Retorna um QFrame estilizado como card/painel."""
    from PySide6.QtWidgets import QFrame
    frame = QFrame()
    frame.setObjectName("card")
    return frame
