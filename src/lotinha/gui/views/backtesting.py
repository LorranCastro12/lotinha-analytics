"""Tab 5 — Backtesting: valida estratégias com walk-forward + Wilcoxon."""

from __future__ import annotations

import queue
import threading
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
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


class BacktestingView(QWidget):
    def __init__(self, repo: Any, settings: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._settings = settings
        self._q: queue.Queue = queue.Queue()
        self._running = False
        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(14)
        scroll.setWidget(content)

        # Título
        title = QLabel("Backtesting Walk-Forward")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ── Configuração ──────────────────────────────────────────────────
        cfg = QWidget()
        cfg.setObjectName("card")
        cfg.setStyleSheet(
            f"QWidget#card {{ background-color: {BG_PANEL}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        cfg_layout = QGridLayout(cfg)
        cfg_layout.setContentsMargins(20, 16, 20, 16)
        cfg_layout.setHorizontalSpacing(14)
        cfg_layout.setVerticalSpacing(10)

        # Linha 0: Banca + Horário
        cfg_layout.addWidget(QLabel("Banca:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        self._banca_cb = QComboBox()
        self._banca_cb.addItem("—")
        self._banca_cb.setFixedWidth(220)
        cfg_layout.addWidget(self._banca_cb, 0, 1, Qt.AlignmentFlag.AlignLeft)

        cfg_layout.addWidget(QLabel("Horário:"), 0, 2, Qt.AlignmentFlag.AlignLeft)
        self._hora_cb = QComboBox()
        self._hora_cb.addItem("—")
        self._hora_cb.setFixedWidth(100)
        cfg_layout.addWidget(self._hora_cb, 0, 3, Qt.AlignmentFlag.AlignLeft)

        # Linha 1: Estratégia + N preditos
        cfg_layout.addWidget(QLabel("Estratégia:"), 1, 0, Qt.AlignmentFlag.AlignLeft)
        self._strat_cb = QComboBox()
        self._strat_cb.addItems(["Frequência", "Atraso", "Markov", "Ensemble"])
        self._strat_cb.setFixedWidth(160)
        cfg_layout.addWidget(self._strat_cb, 1, 1, Qt.AlignmentFlag.AlignLeft)

        cfg_layout.addWidget(QLabel("N preditos:"), 1, 2, Qt.AlignmentFlag.AlignLeft)
        self._n_cb = QComboBox()
        self._n_cb.addItems(["17", "18", "19", "20", "21", "22"])
        self._n_cb.setCurrentText("22")
        self._n_cb.setFixedWidth(80)
        cfg_layout.addWidget(self._n_cb, 1, 3, Qt.AlignmentFlag.AlignLeft)

        # Linha 2: Treino mín
        cfg_layout.addWidget(QLabel("Treino mín (draws):"), 2, 0, Qt.AlignmentFlag.AlignLeft)
        self._train_edit = QLineEdit("60")
        self._train_edit.setFixedWidth(80)
        cfg_layout.addWidget(self._train_edit, 2, 1, Qt.AlignmentFlag.AlignLeft)

        # Linha 3-4: Prêmios
        lbl_premios = QLabel("Prêmios (11..15 acertos), separados por vírgula:")
        lbl_premios.setStyleSheet(f"color: {TEXT_SECONDARY};")
        cfg_layout.addWidget(lbl_premios, 3, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)

        self._premios_edit = QLineEdit()
        self._premios_edit.setPlaceholderText("ex: 5,20,50,200,1000")
        self._premios_edit.setFixedWidth(320)
        cfg_layout.addWidget(self._premios_edit, 4, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)

        cfg_layout.addWidget(QLabel("Custo por aposta (R$):"), 3, 2, Qt.AlignmentFlag.AlignLeft)
        self._custo_edit = QLineEdit("2.00")
        self._custo_edit.setFixedWidth(100)
        cfg_layout.addWidget(self._custo_edit, 4, 2, 1, 2, Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(cfg)

        # Botão
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_h = QHBoxLayout(btn_row)
        btn_h.setContentsMargins(0, 0, 0, 0)
        btn_h.addStretch()
        self._btn = QPushButton("Executar Backtest")
        self._btn.setFixedWidth(200)
        self._btn.clicked.connect(self._start)
        btn_h.addWidget(self._btn)
        btn_h.addStretch()
        layout.addWidget(btn_row)

        # Progresso
        self._progress = QProgressBar()
        self._progress.setRange(0, 1000)
        self._progress.setValue(0)
        self._progress.setFixedHeight(10)
        self._progress.setTextVisible(False)
        layout.addWidget(self._progress)

        self._prog_lbl = QLabel("")
        self._prog_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._prog_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self._prog_lbl)

        # ── Métricas ──────────────────────────────────────────────────────
        metrics_frame = QWidget()
        metrics_frame.setObjectName("card")
        metrics_frame.setStyleSheet(
            f"QWidget#card {{ background-color: {BG_PANEL}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        metrics_layout = QGridLayout(metrics_frame)
        metrics_layout.setContentsMargins(16, 12, 16, 12)
        metrics_layout.setHorizontalSpacing(20)
        metrics_layout.setVerticalSpacing(6)

        small_font = QFont()
        small_font.setPointSize(10)
        big_bold = QFont()
        big_bold.setPointSize(18)
        big_bold.setBold(True)

        self._res_labels: dict[str, QLabel] = {}
        metrics = [
            ("Média acertos (estratégia)", "acertos_strat"),
            ("Média acertos (aleatório)", "acertos_rand"),
            ("ROI estratégia", "roi_strat"),
            ("p-value (Wilcoxon)", "pvalue"),
        ]
        for col, (text, key) in enumerate(metrics):
            lbl_text = QLabel(text)
            lbl_text.setFont(small_font)
            lbl_text.setStyleSheet(f"color: {TEXT_SECONDARY};")
            lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metrics_layout.addWidget(lbl_text, 0, col)

            lbl_val = QLabel("—")
            lbl_val.setFont(big_bold)
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metrics_layout.addWidget(lbl_val, 1, col)
            self._res_labels[key] = lbl_val

        layout.addWidget(metrics_frame)

        # Aviso honesto
        self._warning_frame = QWidget()
        self._warning_frame.setObjectName("card")
        self._warning_frame.setStyleSheet(
            "QWidget#card { background-color: #2a0f0f; "
            "border: 1px solid #5a1515; border-radius: 10px; }"
        )
        warning_layout = QVBoxLayout(self._warning_frame)
        warning_layout.setContentsMargins(16, 12, 16, 12)
        self._warning_lbl = QLabel("")
        self._warning_lbl.setWordWrap(True)
        self._warning_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._warning_lbl.setStyleSheet("color: #FF8080; font-weight: bold; font-size: 13px;")
        warning_layout.addWidget(self._warning_lbl)
        self._warning_frame.hide()
        layout.addWidget(self._warning_frame)

        layout.addStretch()

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

    def _parse_premios(self) -> dict[int, float]:
        text = self._premios_edit.text().strip()
        if not text:
            return {}
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 5:
            raise ValueError(
                "Informe exatamente 5 valores separados por vírgula (11..15 acertos)"
            )
        return {11 + i: float(p) for i, p in enumerate(parts)}

    def _start(self) -> None:
        if self._running:
            return
        try:
            premios = self._parse_premios()
            custo = float(self._custo_edit.text().strip())
            train_size = int(self._train_edit.text().strip())
            n_preditos = int(self._n_cb.currentText())
        except ValueError as exc:
            self._prog_lbl.setText(f"Parâmetro inválido: {exc}")
            self._prog_lbl.setStyleSheet(f"color: {COLOR_ERROR};")
            return

        self._running = True
        self._btn.setEnabled(False)
        self._btn.setText("Executando...")
        self._progress.setValue(0)
        self._warning_frame.hide()

        thread = threading.Thread(
            target=self._run_backtest,
            args=(premios, custo, train_size, n_preditos),
            daemon=True,
        )
        thread.start()
        QTimer.singleShot(200, self._poll)

    def _run_backtest(
        self, premios: dict[int, float], custo: float, train_size: int, n_preditos: int
    ) -> None:
        from lotinha.analysis.backtester import Backtester
        from lotinha.analysis.strategies import (
            AtrasoStrategy,
            EnsembleStrategy,
            FrequenciaStrategy,
            MarkovStrategy,
        )

        strat_map = {
            "Frequência": FrequenciaStrategy(),
            "Atraso": AtrasoStrategy(),
            "Markov": MarkovStrategy(),
            "Ensemble": EnsembleStrategy([
                FrequenciaStrategy(), AtrasoStrategy(), MarkovStrategy(),
            ]),
        }
        strategy = strat_map[self._strat_cb.currentText()]
        banca = self._banca_cb.currentText()
        hora_s = self._hora_cb.currentText()

        try:
            hora = int(hora_s)
            df = self._repo.get_resultados(banca=banca, hora=hora)
        except Exception as exc:
            self._q.put(("error", str(exc)))
            return

        def progress(atual: int, total: int) -> None:
            self._q.put(("progress", atual, total))

        bt = Backtester(premios=premios, custo=custo, seed=42)
        try:
            result = bt.run(
                df, strategy, n_preditos=n_preditos,
                train_size=train_size, progress_callback=progress,
            )
            self._q.put(("done", result))
        except Exception as exc:
            self._q.put(("error", str(exc)))

    def _poll(self) -> None:
        try:
            while True:
                item = self._q.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, atual, total = item
                    self._progress.setValue(int(atual / total * 1000) if total else 0)
                    self._prog_lbl.setText(f"[{atual}/{total}]")
                    self._prog_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
                elif kind == "done":
                    self._show_result(item[1])
                    self._finish()
                    return
                elif kind == "error":
                    self._prog_lbl.setText(f"Erro: {item[1]}")
                    self._prog_lbl.setStyleSheet(f"color: {COLOR_ERROR};")
                    self._finish()
                    return
        except queue.Empty:
            pass
        QTimer.singleShot(200, self._poll)

    def _show_result(self, result: Any) -> None:
        self._progress.setValue(1000)
        self._prog_lbl.setText(
            f"Concluído — {result.n_draws_tested} draws testados."
        )
        self._prog_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")

        self._res_labels["acertos_strat"].setText(f"{result.mean_acertos_strategy:.2f}")
        self._res_labels["acertos_rand"].setText(f"{result.mean_acertos_random:.2f}")

        roi_str = f"{result.roi_strategy:+.1%}"
        roi_color = COLOR_PRIMARY if result.roi_strategy >= 0 else COLOR_ERROR
        self._res_labels["roi_strat"].setText(roi_str)
        self._res_labels["roi_strat"].setStyleSheet(
            f"color: {roi_color}; font-size: 18px; font-weight: bold;"
        )

        p_str = f"{result.p_value:.3f}" if result.p_value is not None else "N/A"
        self._res_labels["pvalue"].setText(p_str)

        if result.warning:
            self._warning_lbl.setText(result.warning)
            self._warning_frame.show()
        else:
            self._warning_frame.hide()

    def _finish(self) -> None:
        self._running = False
        self._btn.setEnabled(True)
        self._btn.setText("Executar Backtest")
