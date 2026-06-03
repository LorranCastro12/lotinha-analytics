"""Tab 1 — Dashboard: estatísticas gerais do banco."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lotinha.gui.theme import (
    BG_PANEL,
    BORDER,
    COLOR_ERROR,
    COLOR_PRIMARY,
    TEXT_SECONDARY,
)


class DashboardView(QWidget):
    def __init__(self, repo: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._build()
        self.refresh()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)
        outer.setContentsMargins(30, 20, 30, 20)
        outer.setSpacing(16)

        # Título
        title = QLabel("Dashboard")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(title)

        # Card de estatísticas
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(
            f"QWidget#card {{ background-color: {BG_PANEL}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setHorizontalSpacing(24)
        card_layout.setVerticalSpacing(10)
        card_layout.setColumnStretch(1, 1)

        bold_font = QFont()
        bold_font.setBold(True)

        self._stat_labels: dict[str, QLabel] = {}
        rows = [
            ("Total de sorteios", "total"),
            ("Data mais antiga", "data_min"),
            ("Data mais recente", "data_max"),
            ("Dias com dados", "dias"),
            ("Bancas disponíveis", "bancas"),
            ("Horários disponíveis", "horarios"),
        ]
        for i, (text, key) in enumerate(rows):
            lbl_key = QLabel(text + ":")
            lbl_key.setFont(bold_font)
            lbl_val = QLabel("—")
            lbl_val.setStyleSheet(f"color: {TEXT_SECONDARY};")
            card_layout.addWidget(lbl_key, i, 0, Qt.AlignmentFlag.AlignLeft)
            card_layout.addWidget(lbl_val, i, 1, Qt.AlignmentFlag.AlignLeft)
            self._stat_labels[key] = lbl_val

        outer.addWidget(card)

        # Botão e status
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_h = QHBoxLayout(btn_row)
        btn_h.setContentsMargins(0, 0, 0, 0)
        btn_h.addStretch()
        btn = QPushButton("Atualizar")
        btn.setFixedWidth(140)
        btn.clicked.connect(self.refresh)
        btn_h.addWidget(btn)
        btn_h.addStretch()
        outer.addWidget(btn_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        outer.addWidget(self._status_lbl)

        outer.addStretch()

    # ── Lógica ─────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        try:
            total = self._repo.count_total()
            latest = self._repo.latest_date()
            bancas = self._repo.list_bancas()
            horarios = self._repo.list_horarios()
            dates = self._repo.dates_with_data()

            self._stat_labels["total"].setText(str(total))
            self._stat_labels["data_min"].setText(str(min(dates)) if dates else "—")
            self._stat_labels["data_max"].setText(str(latest) if latest else "—")
            self._stat_labels["dias"].setText(str(len(dates)))
            self._stat_labels["bancas"].setText(
                ", ".join(sorted(bancas)) if bancas else "—"
            )
            self._stat_labels["horarios"].setText(
                "  ".join(f"{h}h" for h in sorted(horarios)) if horarios else "—"
            )
            self._status_lbl.setText("Atualizado com sucesso.")
            self._status_lbl.setStyleSheet(f"color: {COLOR_PRIMARY};")
        except Exception as exc:
            self._status_lbl.setText(f"Erro: {exc}")
            self._status_lbl.setStyleSheet(f"color: {COLOR_ERROR};")
