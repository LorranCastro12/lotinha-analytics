"""Tab 3 — Análise: frequências, atraso e co-ocorrências."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lotinha.gui.theme import (
    COLOR_ERROR,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    MATPLOTLIB_STYLE,
    TEXT_SECONDARY,
)


class AnalysisView(QWidget):
    def __init__(self, repo: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(10)

        # Título
        title = QLabel("Análise Estatística")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Filtros
        filt_row = QWidget()
        filt_row.setStyleSheet("background: transparent;")
        filt_h = QHBoxLayout(filt_row)
        filt_h.setContentsMargins(0, 0, 0, 0)
        filt_h.setSpacing(8)

        filt_h.addWidget(QLabel("Banca:"))
        self._banca_cb = QComboBox()
        self._banca_cb.addItem("Todas")
        self._banca_cb.setFixedWidth(200)
        filt_h.addWidget(self._banca_cb)

        filt_h.addWidget(QLabel("Horário:"))
        self._hora_cb = QComboBox()
        self._hora_cb.addItem("Todos")
        self._hora_cb.setFixedWidth(100)
        filt_h.addWidget(self._hora_cb)

        filt_h.addWidget(QLabel("Janela:"))
        self._janela_cb = QComboBox()
        self._janela_cb.addItems(["Todos", "30", "60", "90", "180"])
        self._janela_cb.setFixedWidth(100)
        filt_h.addWidget(self._janela_cb)

        btn_analisar = QPushButton("Analisar")
        btn_analisar.setFixedWidth(120)
        btn_analisar.clicked.connect(self._analisar)
        filt_h.addWidget(btn_analisar)

        filt_h.addStretch()
        layout.addWidget(filt_row)

        # Tipo de gráfico
        tipo_row = QWidget()
        tipo_row.setStyleSheet("background: transparent;")
        tipo_h = QHBoxLayout(tipo_row)
        tipo_h.setContentsMargins(0, 0, 0, 0)
        tipo_h.setSpacing(8)
        tipo_h.addWidget(QLabel("Exibir:"))
        self._tipo_cb = QComboBox()
        self._tipo_cb.addItems(["Frequência", "Atraso"])
        self._tipo_cb.setFixedWidth(160)
        self._tipo_cb.currentTextChanged.connect(lambda _: self._analisar())
        tipo_h.addWidget(self._tipo_cb)
        tipo_h.addStretch()
        layout.addWidget(tipo_row)

        # Matplotlib canvas
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        self._fig = Figure(figsize=(9, 4), dpi=96, tight_layout=True)
        self._fig.patch.set_facecolor(MATPLOTLIB_STYLE["fig_facecolor"])
        self._ax = self._fig.add_subplot(111)
        self._style_ax()

        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setMinimumHeight(280)
        layout.addWidget(self._canvas, stretch=1)

        self._status_lbl = QLabel("Selecione os filtros e clique em Analisar.")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self._status_lbl)

        self._load_filters()

    def _style_ax(self) -> None:
        s = MATPLOTLIB_STYLE
        self._ax.set_facecolor(s["ax_facecolor"])
        self._ax.tick_params(colors=s["tick_color"])
        self._ax.xaxis.label.set_color(s["label_color"])
        self._ax.yaxis.label.set_color(s["label_color"])
        self._ax.title.set_color(s["title_color"])
        for spine in self._ax.spines.values():
            spine.set_color(s["spine_color"])
        self._ax.spines["right"].set_visible(False)
        self._ax.spines["top"].set_visible(False)

    # ── Lógica ─────────────────────────────────────────────────────────────

    def _load_filters(self) -> None:
        try:
            bancas = self._repo.list_bancas()
            horarios = self._repo.list_horarios()
            self._banca_cb.clear()
            self._banca_cb.addItems(["Todas", *sorted(bancas)])
            self._hora_cb.clear()
            self._hora_cb.addItems(["Todos", *(str(h) for h in sorted(horarios))])
        except Exception:
            pass

    def _analisar(self) -> None:
        from lotinha.analysis.statistics import atraso, frequencia

        banca = self._banca_cb.currentText()
        hora_s = self._hora_cb.currentText()
        janela_s = self._janela_cb.currentText()

        banca_filter = None if banca == "Todas" else banca
        hora_filter = None if hora_s == "Todos" else int(hora_s)
        janela = None if janela_s == "Todos" else int(janela_s)

        try:
            df = self._repo.get_resultados(banca=banca_filter, hora=hora_filter)
        except Exception as exc:
            self._status_lbl.setText(f"Erro: {exc}")
            self._status_lbl.setStyleSheet(f"color: {COLOR_ERROR};")
            return

        if df.empty:
            self._status_lbl.setText("Sem dados para os filtros selecionados.")
            self._status_lbl.setStyleSheet(f"color: {COLOR_SECONDARY};")
            return

        tipo = self._tipo_cb.currentText()
        self._ax.clear()
        self._style_ax()

        if tipo == "Frequência":
            scores = frequencia(df, janela)
            self._ax.bar(scores.index, scores.values, color=COLOR_PRIMARY, edgecolor="none")
            self._ax.set_title(
                f"Frequência relativa — {banca} / {hora_s}h",
                color=MATPLOTLIB_STYLE["title_color"],
            )
            self._ax.set_xlabel("Número", color=MATPLOTLIB_STYLE["label_color"])
            self._ax.set_ylabel("Frequência", color=MATPLOTLIB_STYLE["label_color"])
            self._ax.axhline(
                15 / 25, color="#FF5555", linestyle="--",
                linewidth=1, label="Esperado (15/25)",
            )
            self._ax.legend(fontsize=8, facecolor=MATPLOTLIB_STYLE["ax_facecolor"],
                            labelcolor=MATPLOTLIB_STYLE["tick_color"])
        else:
            scores = atraso(df).astype(float)
            self._ax.bar(scores.index, scores.values, color=COLOR_SECONDARY, edgecolor="none")
            self._ax.set_title(
                f"Atraso (sorteios sem aparecer) — {banca} / {hora_s}h",
                color=MATPLOTLIB_STYLE["title_color"],
            )
            self._ax.set_xlabel("Número", color=MATPLOTLIB_STYLE["label_color"])
            self._ax.set_ylabel("Atraso (sorteios)", color=MATPLOTLIB_STYLE["label_color"])

        self._ax.set_xticks(range(1, 26))
        self._canvas.draw()
        n = len(df)
        self._status_lbl.setText(f"{n} sorteios analisados.")
        self._status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
