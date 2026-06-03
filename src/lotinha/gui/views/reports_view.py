"""Tab 6 — Relatórios: PDF de predições e Excel do histórico."""

from __future__ import annotations

import queue
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lotinha.gui.theme import (
    BG_PANEL,
    BORDER,
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    TEXT_SECONDARY,
)
from lotinha.user_prefs import UserPrefs

_ROOT_FOLDER = "RELATÓRIOS DE PREDIÇÃO - LOTINHA"
_EXCEL_SUBFOLDER = "1 - PREDIÇÕES EXCEL"
_PDF_SUBFOLDER = "2 - PREDIÇÕES PDF"


class ReportsView(QWidget):
    def __init__(self, repo: Any, settings: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._settings = settings
        self._prefs = UserPrefs()
        self._q: queue.Queue = queue.Queue()
        self._running = False
        self._progress_val: float = 0.0
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
        title = QLabel("Relatórios")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ── Seção: Pasta de relatórios ─────────────────────────────────────
        dir_frame = self._make_card()
        dir_layout = QGridLayout(dir_frame)
        dir_layout.setContentsMargins(20, 16, 20, 16)
        dir_layout.setHorizontalSpacing(8)
        dir_layout.setVerticalSpacing(10)
        dir_layout.setColumnStretch(1, 1)

        sec_title = QLabel("Pasta de Relatórios")
        sec_title.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COLOR_INFO};"
        )
        dir_layout.addWidget(sec_title, 0, 0, 1, 4)

        dir_layout.addWidget(QLabel("Pasta base:"), 1, 0, Qt.AlignmentFlag.AlignLeft)
        self._dir_edit = QLineEdit(self._prefs.reports_dir)
        dir_layout.addWidget(self._dir_edit, 1, 1)

        btn_browse = QPushButton("...")
        btn_browse.setObjectName("btn_small")
        btn_browse.setFixedWidth(36)
        btn_browse.clicked.connect(self._browse_dir)
        dir_layout.addWidget(btn_browse, 1, 2)

        btn_save = QPushButton("Salvar")
        btn_save.setObjectName("btn_small")
        btn_save.setFixedWidth(72)
        btn_save.clicked.connect(self._save_dir)
        dir_layout.addWidget(btn_save, 1, 3)

        self._dir_info_lbl = QLabel(self._dir_info_text())
        self._dir_info_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        self._dir_info_lbl.setWordWrap(True)
        dir_layout.addWidget(self._dir_info_lbl, 2, 0, 1, 4)

        layout.addWidget(dir_frame)

        # ── Seção: PDF de predições ────────────────────────────────────────
        pdf_frame = self._make_card()
        pdf_layout = QGridLayout(pdf_frame)
        pdf_layout.setContentsMargins(20, 16, 20, 16)
        pdf_layout.setHorizontalSpacing(12)
        pdf_layout.setVerticalSpacing(10)
        pdf_layout.setColumnStretch(1, 1)

        pdf_sec = QLabel("PDF de Predições")
        pdf_sec.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COLOR_PRIMARY};"
        )
        pdf_layout.addWidget(pdf_sec, 0, 0, 1, 3)

        pdf_layout.addWidget(QLabel("Data alvo:"), 1, 0, Qt.AlignmentFlag.AlignLeft)
        _amanha = date.today() + timedelta(days=1)
        self._data_edit = QDateEdit()
        self._data_edit.setCalendarPopup(True)
        self._data_edit.setDate(QDate(_amanha.year, _amanha.month, _amanha.day))
        self._data_edit.setDisplayFormat("dd/MM/yyyy")
        self._data_edit.setFixedWidth(160)
        pdf_layout.addWidget(self._data_edit, 1, 1, Qt.AlignmentFlag.AlignLeft)

        pdf_layout.addWidget(QLabel("Estratégia:"), 2, 0, Qt.AlignmentFlag.AlignLeft)
        self._strat_cb = QComboBox()
        self._strat_cb.addItems(["Frequência", "Atraso", "Markov", "Ensemble"])
        self._strat_cb.setCurrentText("Ensemble")
        self._strat_cb.setFixedWidth(160)
        pdf_layout.addWidget(self._strat_cb, 2, 1, Qt.AlignmentFlag.AlignLeft)

        pdf_layout.addWidget(QLabel("N preditos:"), 3, 0, Qt.AlignmentFlag.AlignLeft)
        self._n_cb = QComboBox()
        self._n_cb.addItems(["17", "18", "19", "20", "21", "22", "23"])
        self._n_cb.setCurrentText("23")
        self._n_cb.setFixedWidth(80)
        pdf_layout.addWidget(self._n_cb, 3, 1, Qt.AlignmentFlag.AlignLeft)

        btn_row_pdf = QWidget()
        btn_row_pdf.setStyleSheet("background: transparent;")
        bh = QHBoxLayout(btn_row_pdf)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.addStretch()
        self._btn_pdf = QPushButton("Gerar PDF")
        self._btn_pdf.setFixedWidth(160)
        self._btn_pdf.clicked.connect(self._start_pdf)
        bh.addWidget(self._btn_pdf)
        bh.addStretch()
        pdf_layout.addWidget(btn_row_pdf, 4, 0, 1, 3)

        layout.addWidget(pdf_frame)

        # ── Seção: Excel do histórico ──────────────────────────────────────
        xls_frame = self._make_card()
        xls_layout = QVBoxLayout(xls_frame)
        xls_layout.setContentsMargins(20, 16, 20, 16)
        xls_layout.setSpacing(10)

        xls_sec = QLabel("Excel do Histórico")
        xls_sec.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COLOR_SECONDARY};"
        )
        xls_layout.addWidget(xls_sec)

        btn_xls_row = QWidget()
        btn_xls_row.setStyleSheet("background: transparent;")
        bh2 = QHBoxLayout(btn_xls_row)
        bh2.setContentsMargins(0, 0, 0, 0)
        bh2.addStretch()
        self._btn_xls = QPushButton("Gerar Excel")
        self._btn_xls.setObjectName("btn_orange")
        self._btn_xls.setFixedWidth(160)
        self._btn_xls.clicked.connect(self._start_excel)
        bh2.addWidget(self._btn_xls)
        bh2.addStretch()
        xls_layout.addWidget(btn_xls_row)

        layout.addWidget(xls_frame)

        # ── Status e log ───────────────────────────────────────────────────
        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self._status_lbl)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1000)
        self._progress.setValue(0)
        self._progress.setFixedHeight(10)
        self._progress.setTextVisible(False)
        layout.addWidget(self._progress)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(120)
        layout.addWidget(self._log)

        layout.addStretch()

    def _make_card(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("card")
        frame.setStyleSheet(
            f"QWidget#card {{ background-color: {BG_PANEL}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        return frame

    # ── Pasta base ──────────────────────────────────────────────────────────

    def _dir_info_text(self) -> str:
        base = Path(self._dir_edit.text()) if hasattr(self, "_dir_edit") \
            else Path(self._prefs.reports_dir)
        root = base / _ROOT_FOLDER
        return (
            f"Arquivos gerados em: {root}/\n"
            f"  PDF  → {_PDF_SUBFOLDER}/     Excel  → {_EXCEL_SUBFOLDER}/"
        )

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Selecionar pasta base", self._dir_edit.text()
        )
        if path:
            self._dir_edit.setText(path)
            self._dir_info_lbl.setText(self._dir_info_text())

    def _save_dir(self) -> None:
        new_dir = self._dir_edit.text().strip()
        if not new_dir:
            self._log_line("Caminho inválido.", color=COLOR_ERROR)
            return
        self._prefs.reports_dir = new_dir
        self._dir_info_lbl.setText(self._dir_info_text())
        self._log_line(f"Pasta base salva: {new_dir}")

    # ── Helpers de caminho ──────────────────────────────────────────────────

    def _pdf_output(self, data_alvo: date, estrategia: str) -> Path:
        folder = Path(self._prefs.reports_dir) / _ROOT_FOLDER / _PDF_SUBFOLDER
        folder.mkdir(parents=True, exist_ok=True)
        date_str = data_alvo.strftime("%d-%m-%Y")
        return folder / f"PREDIÇÃO - {estrategia.upper()} - {date_str}.pdf"

    def _excel_output(self) -> Path:
        folder = Path(self._prefs.reports_dir) / _ROOT_FOLDER / _EXCEL_SUBFOLDER
        folder.mkdir(parents=True, exist_ok=True)
        date_str = date.today().strftime("%d-%m-%Y")
        return folder / f"HISTÓRICO - LOTINHA - {date_str}.xlsx"

    # ── PDF de predições ────────────────────────────────────────────────────

    def _start_pdf(self) -> None:
        if self._running:
            return
        data_alvo = self._data_edit.date().toPython()
        estrategia = self._strat_cb.currentText()
        output = self._pdf_output(data_alvo, estrategia)

        self._running = True
        self._progress_val = 0.0
        self._btn_pdf.setEnabled(False)
        self._btn_pdf.setText("Gerando PDF...")
        self._btn_xls.setEnabled(False)
        self._progress.setValue(0)
        self._status_lbl.setText("Calculando predições...")
        self._status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")

        threading.Thread(
            target=self._run_pdf,
            args=(data_alvo, output, estrategia, int(self._n_cb.currentText())),
            daemon=True,
        ).start()
        QTimer.singleShot(200, self._poll)

    def _run_pdf(self, data_alvo: date, output: Path, estrategia: str, n: int) -> None:
        from lotinha.reporting.predictions_pdf import generate_predictions_pdf
        try:
            path, n_ok = generate_predictions_pdf(
                self._repo, output,
                data_alvo=data_alvo,
                estrategia_nome=estrategia,
                n_preditos=n,
            )
            self._q.put(("done_pdf", path, n_ok))
        except Exception as exc:
            self._q.put(("error", str(exc)))

    # ── Excel ───────────────────────────────────────────────────────────────

    def _start_excel(self) -> None:
        if self._running:
            return
        output = self._excel_output()

        self._running = True
        self._progress_val = 0.0
        self._btn_pdf.setEnabled(False)
        self._btn_xls.setEnabled(False)
        self._btn_xls.setText("Gerando Excel...")
        self._progress.setValue(0)
        self._status_lbl.setText("Exportando dados...")
        self._status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")

        threading.Thread(
            target=self._run_excel, args=(output,), daemon=True
        ).start()
        QTimer.singleShot(200, self._poll)

    def _run_excel(self, output: Path) -> None:
        from lotinha.storage.export_import import export_to_excel
        try:
            total = export_to_excel(self._repo, output)
            self._q.put(("done_excel", output, total))
        except Exception as exc:
            self._q.put(("error", str(exc)))

    # ── Poll / log ──────────────────────────────────────────────────────────

    def _poll(self) -> None:
        try:
            while True:
                item = self._q.get_nowait()
                kind = item[0]
                if kind == "done_pdf":
                    _, path, n_ok = item
                    self._progress.setValue(1000)
                    self._status_lbl.setText("PDF gerado!")
                    self._status_lbl.setStyleSheet(f"color: {COLOR_PRIMARY};")
                    self._log_line(f"PDF salvo: {path}  ({n_ok} predições geradas)")
                    self._finish()
                    return
                elif kind == "done_excel":
                    _, path, total = item
                    self._progress.setValue(1000)
                    self._status_lbl.setText("Excel gerado!")
                    self._status_lbl.setStyleSheet(f"color: {COLOR_SECONDARY};")
                    self._log_line(f"Excel salvo: {path}  ({total} sorteios exportados)")
                    self._finish()
                    return
                elif kind == "error":
                    self._status_lbl.setText("Erro.")
                    self._status_lbl.setStyleSheet(f"color: {COLOR_ERROR};")
                    self._log_line(f"Erro: {item[1]}", color=COLOR_ERROR)
                    self._finish()
                    return
        except queue.Empty:
            pass

        # Animação de progresso indeterminado
        self._progress_val = min(self._progress_val + 0.02, 0.9)
        self._progress.setValue(int(self._progress_val * 1000))
        QTimer.singleShot(200, self._poll)

    def _finish(self) -> None:
        self._running = False
        self._btn_pdf.setEnabled(True)
        self._btn_pdf.setText("Gerar PDF")
        self._btn_xls.setEnabled(True)
        self._btn_xls.setText("Gerar Excel")

    def _log_line(self, text: str, color: str = "") -> None:
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        if color:
            self._log.append(f'<span style="color:{color}">[{ts}] {text}</span>')
        else:
            self._log.append(f"[{ts}] {text}")
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())
