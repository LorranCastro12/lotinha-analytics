"""Tab 4 — Predição: gera números recomendados para o próximo sorteio."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from lotinha.gui.theme import (
    BG_PANEL,
    BORDER,
    COLOR_ERROR,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    TEXT_SECONDARY,
)
from lotinha.gui.widgets.number_grid import NumberGrid


class PredictionView(QWidget):
    def __init__(self, repo: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Título
        title = QLabel("Predição de Números")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Dois painéis lado a lado
        cols_row = QWidget()
        cols_row.setStyleSheet("background: transparent;")
        cols_h = QHBoxLayout(cols_row)
        cols_h.setContentsMargins(0, 0, 0, 0)
        cols_h.setSpacing(12)

        # ── Painel esquerdo — controles ───────────────────────────────────
        ctrl = QWidget()
        ctrl.setObjectName("card")
        ctrl.setStyleSheet(
            f"QWidget#card {{ background-color: {BG_PANEL}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        ctrl_layout = QGridLayout(ctrl)
        ctrl_layout.setContentsMargins(20, 16, 20, 16)
        ctrl_layout.setHorizontalSpacing(12)
        ctrl_layout.setVerticalSpacing(10)
        ctrl_layout.setColumnStretch(1, 1)

        row = 0

        # Banca
        ctrl_layout.addWidget(QLabel("Banca:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        self._banca_cb = QComboBox()
        self._banca_cb.addItem("—")
        self._banca_cb.setFixedWidth(200)
        ctrl_layout.addWidget(self._banca_cb, row, 1, Qt.AlignmentFlag.AlignLeft)
        row += 1

        # Horário
        ctrl_layout.addWidget(QLabel("Horário:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        self._hora_cb = QComboBox()
        self._hora_cb.addItem("—")
        self._hora_cb.setFixedWidth(100)
        ctrl_layout.addWidget(self._hora_cb, row, 1, Qt.AlignmentFlag.AlignLeft)
        row += 1

        # Data alvo
        ctrl_layout.addWidget(QLabel("Data alvo:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        _amanha = date.today() + timedelta(days=1)
        self._data_edit = QDateEdit()
        self._data_edit.setCalendarPopup(True)
        self._data_edit.setDate(QDate(_amanha.year, _amanha.month, _amanha.day))
        self._data_edit.setDisplayFormat("dd/MM/yyyy")
        self._data_edit.setFixedWidth(160)
        ctrl_layout.addWidget(self._data_edit, row, 1, Qt.AlignmentFlag.AlignLeft)
        row += 1

        # Estratégia
        ctrl_layout.addWidget(QLabel("Estratégia:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        self._strat_cb = QComboBox()
        self._strat_cb.addItems(["Frequência", "Atraso", "Markov", "LightGBM", "Ensemble"])
        self._strat_cb.setCurrentText("Ensemble")
        self._strat_cb.setFixedWidth(160)
        ctrl_layout.addWidget(self._strat_cb, row, 1, Qt.AlignmentFlag.AlignLeft)
        row += 1

        # Slider N preditos
        ctrl_layout.addWidget(QLabel("N preditos:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        self._n_slider = QSlider(Qt.Orientation.Horizontal)
        self._n_slider.setRange(17, 25)
        self._n_slider.setValue(24)
        self._n_slider.setSingleStep(1)
        self._n_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._n_slider.setTickInterval(1)
        ctrl_layout.addWidget(self._n_slider, row, 1)
        row += 1

        self._n_label = QLabel("24")
        self._n_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold;")
        ctrl_layout.addWidget(self._n_label, row, 1, Qt.AlignmentFlag.AlignLeft)
        self._n_slider.valueChanged.connect(lambda v: self._n_label.setText(str(v)))
        row += 1

        # Botão
        btn = QPushButton("Gerar Predição")
        btn.clicked.connect(self._predict)
        ctrl_layout.addWidget(btn, row, 0, 1, 2)
        row += 1

        # Resultado
        self._result_lbl = QLabel("")
        self._result_lbl.setWordWrap(True)
        self._result_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._result_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        ctrl_layout.addWidget(self._result_lbl, row, 0, 1, 2)

        # Espaçador no final do card
        ctrl_layout.setRowStretch(row + 1, 1)

        cols_h.addWidget(ctrl, stretch=1)

        # ── Painel direito — grade de números ─────────────────────────────
        right = QWidget()
        right.setObjectName("card")
        right.setStyleSheet(
            f"QWidget#card {{ background-color: {BG_PANEL}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        right_layout = QVBoxLayout(right)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        grid_title = QLabel("Números preditos")
        grid_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid_font = QFont()
        grid_font.setPointSize(13)
        grid_title.setFont(grid_font)
        right_layout.addWidget(grid_title)

        self._grid = NumberGrid()
        right_layout.addWidget(self._grid, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Legenda
        legend_row = QWidget()
        legend_row.setStyleSheet("background: transparent;")
        legend_h = QHBoxLayout(legend_row)
        legend_h.setContentsMargins(0, 0, 0, 0)
        legend_h.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dot_pred = QLabel("●")
        dot_pred.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: 16px;")
        legend_h.addWidget(dot_pred)
        legend_h.addWidget(QLabel(" Predito  "))

        dot_none = QLabel("●")
        dot_none.setStyleSheet("color: #4a4a60; font-size: 16px;")
        legend_h.addWidget(dot_none)
        legend_h.addWidget(QLabel(" Não predito"))

        right_layout.addWidget(legend_row)
        right_layout.addStretch()

        cols_h.addWidget(right, stretch=1)
        layout.addWidget(cols_row, stretch=1)

        self._load_filters()

    # ── Lógica ─────────────────────────────────────────────────────────────

    def _load_filters(self) -> None:
        try:
            bancas = sorted(self._repo.list_bancas())
            horarios = sorted(self._repo.list_horarios())
            self._banca_cb.clear()
            self._banca_cb.addItems(bancas or ["—"])
            self._hora_cb.clear()
            self._hora_cb.addItems([str(h) for h in horarios] or ["—"])
        except Exception:
            pass

    def _predict(self) -> None:
        from lotinha.analysis.strategies import (
            AtrasoStrategy,
            BancaAwareLGBMWrapper,
            EnsembleStrategy,
            FrequenciaStrategy,
            HybridMarkovWrapper,
            MarkovStrategy,
        )
        from lotinha.core.exceptions import InsufficientDataError

        banca = self._banca_cb.currentText()
        hora_s = self._hora_cb.currentText()
        n = self._n_slider.value()
        strat_name = self._strat_cb.currentText()

        try:
            hora = int(hora_s)
            df_hora = self._repo.get_resultados(banca=banca, hora=hora)
            df_banca = self._repo.get_resultados(banca=banca)
        except Exception as exc:
            self._result_lbl.setText(f"Erro: {exc}")
            self._result_lbl.setStyleSheet(f"color: {COLOR_ERROR}; background: transparent;")
            return

        if df_hora.empty:
            self._result_lbl.setText("Sem dados para os filtros selecionados.")
            self._result_lbl.setStyleSheet(
                f"color: {COLOR_SECONDARY}; background: transparent;"
            )
            return

        hybrid_markov = HybridMarkovWrapper(df_banca)
        aware_lgbm = BancaAwareLGBMWrapper(df_banca, hora)

        strat_map: dict[str, tuple] = {
            "Frequência": (FrequenciaStrategy(), df_hora),
            "Atraso":     (AtrasoStrategy(), df_hora),
            "Markov":     (MarkovStrategy(), df_hora),
            "LightGBM":   (aware_lgbm, df_hora),
            "Ensemble":   (EnsembleStrategy(
                [FrequenciaStrategy(), AtrasoStrategy(), hybrid_markov, aware_lgbm],
                weights=[1.0, 1.0, 1.5, 2.0],
            ), df_hora),
        }

        if strat_name == "Markov":
            strategy = hybrid_markov
            df = df_hora
        else:
            strategy, df = strat_map[strat_name]

        try:
            result = strategy.predict(df, n=n)
        except InsufficientDataError as exc:
            self._result_lbl.setText(f"Dados insuficientes: {exc}")
            self._result_lbl.setStyleSheet(
                f"color: {COLOR_SECONDARY}; background: transparent;"
            )
            return
        except Exception as exc:
            self._result_lbl.setText(f"Erro: {exc}")
            self._result_lbl.setStyleSheet(f"color: {COLOR_ERROR}; background: transparent;")
            return

        self._grid.highlight(result.numeros)
        self._result_lbl.setText(
            f"Estratégia: {strat_name}\n"
            f"Números: {sorted(result.numeros)}\n"
            f"Confiança: {result.confidence:.1%}"
        )
        self._result_lbl.setStyleSheet(f"color: #c0c0d8; background: transparent;")
