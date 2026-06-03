"""Tab 2 — Extração: busca sorteios da API para um intervalo de datas."""

from __future__ import annotations

import queue
import threading
from datetime import date, datetime
from typing import Any

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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
    COLOR_SECONDARY,
    TEXT_SECONDARY,
)


class ExtractionView(QWidget):
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
        title = QLabel("Extração de Dados")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Formulário
        form = QWidget()
        form.setObjectName("card")
        form.setStyleSheet(
            f"QWidget#card {{ background-color: {BG_PANEL}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        form_layout = QGridLayout(form)
        form_layout.setContentsMargins(20, 16, 20, 16)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)
        form_layout.setColumnStretch(1, 1)

        bold_font = QFont()
        bold_font.setBold(False)

        # Datas
        _hoje = date.today()
        _inicio_mes = _hoje.replace(day=1)
        form_layout.addWidget(QLabel("Data início:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        self._inicio = QDateEdit()
        self._inicio.setCalendarPopup(True)
        self._inicio.setDate(QDate(_inicio_mes.year, _inicio_mes.month, _inicio_mes.day))
        self._inicio.setDisplayFormat("dd/MM/yyyy")
        self._inicio.setFixedWidth(160)
        form_layout.addWidget(self._inicio, 0, 1, Qt.AlignmentFlag.AlignLeft)

        form_layout.addWidget(QLabel("Data fim:"), 1, 0, Qt.AlignmentFlag.AlignLeft)
        self._fim = QDateEdit()
        self._fim.setCalendarPopup(True)
        self._fim.setDate(QDate(_hoje.year, _hoje.month, _hoje.day))
        self._fim.setDisplayFormat("dd/MM/yyyy")
        self._fim.setFixedWidth(160)
        form_layout.addWidget(self._fim, 1, 1, Qt.AlignmentFlag.AlignLeft)

        # Checkboxes
        self._skip_cb = QCheckBox("Pular datas já presentes")
        self._skip_cb.setChecked(True)
        form_layout.addWidget(self._skip_cb, 2, 0, 1, 2)

        self._backup_cb = QCheckBox("Criar backup antes de extrair")
        self._backup_cb.setChecked(True)
        form_layout.addWidget(self._backup_cb, 3, 0, 1, 2)

        layout.addWidget(form)

        # Botões
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_h = QHBoxLayout(btn_row)
        btn_h.setContentsMargins(0, 0, 0, 0)
        btn_h.setSpacing(12)
        btn_h.addStretch()

        self._btn = QPushButton("Extrair")
        self._btn.setFixedWidth(160)
        self._btn.clicked.connect(self._start)
        btn_h.addWidget(self._btn)

        self._btn_recover = QPushButton("Recuperar Lacunas")
        self._btn_recover.setObjectName("btn_orange")
        self._btn_recover.setFixedWidth(180)
        self._btn_recover.clicked.connect(self._start_recover)
        btn_h.addWidget(self._btn_recover)

        btn_h.addStretch()
        layout.addWidget(btn_row)

        # Progresso
        self._progress = QProgressBar()
        self._progress.setRange(0, 1000)
        self._progress.setValue(0)
        self._progress.setFixedHeight(10)
        self._progress.setTextVisible(False)
        layout.addWidget(self._progress)

        self._progress_lbl = QLabel("")
        self._progress_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self._progress_lbl)

        # Log
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(200)
        layout.addWidget(self._log)

        layout.addStretch()

    # ── Lógica ─────────────────────────────────────────────────────────────

    def _start(self) -> None:
        if self._running:
            return
        d_inicio = self._inicio.date().toPython()
        d_fim = self._fim.date().toPython()

        if d_inicio > d_fim:
            self._log_line("Data início deve ser ≤ data fim.", color=COLOR_ERROR)
            return

        self._running = True
        self._btn.setEnabled(False)
        self._btn.setText("Extraindo...")
        self._progress.setValue(0)
        self._progress_lbl.setText("Iniciando...")

        thread = threading.Thread(
            target=self._run_extraction,
            args=(d_inicio, d_fim),
            daemon=True,
        )
        thread.start()
        QTimer.singleShot(150, self._poll)

    def _run_extraction(self, d_inicio: date, d_fim: date) -> None:
        from lotinha.extraction.api_client import ApiClient
        from lotinha.extraction.orchestrator import ExtractionOrchestrator

        api = ApiClient(
            base_url=str(self._settings.api_base_url),
            rate_limit=float(self._settings.api_rate_limit),
        )
        orchestrator = ExtractionOrchestrator(
            api_client=api,
            repo=self._repo,
            db_path=self._settings.db_path,
        )

        def progress(atual: int, total: int, data: date) -> None:
            self._q.put(("progress", atual, total, data))

        try:
            report = orchestrator.extract_range(
                inicio=d_inicio,
                fim=d_fim,
                skip_existing=self._skip_cb.isChecked(),
                backup_before=self._backup_cb.isChecked(),
                progress_callback=progress,
            )
            self._q.put(("done", report))
        except Exception as exc:
            self._q.put(("error", str(exc)))

    def _poll(self) -> None:
        try:
            while True:
                item = self._q.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, atual, total, data = item
                    frac = atual / total if total else 0
                    self._progress.setValue(int(frac * 1000))
                    self._progress_lbl.setText(f"[{atual}/{total}] {data}")
                elif kind == "done":
                    report = item[1]
                    self._progress.setValue(1000)
                    if report.total_dias == 0:
                        self._progress_lbl.setText("Nenhuma lacuna encontrada.")
                        self._log_line("Nenhuma lacuna para recuperar.")
                    else:
                        self._progress_lbl.setText("Concluído.")
                        self._log_line(
                            f"Extraídos={report.extraidos}  "
                            f"já_presentes={report.ja_presentes}  "
                            f"vazios={report.vazios}  "
                            f"falhas={report.falhas}"
                        )
                    if report.backup_path:
                        self._log_line(f"Backup: {report.backup_path}")
                    self._finish()
                    return
                elif kind == "error":
                    self._log_line(f"Erro: {item[1]}", color=COLOR_ERROR)
                    self._finish()
                    return
        except queue.Empty:
            pass
        QTimer.singleShot(150, self._poll)

    def _start_recover(self) -> None:
        if self._running:
            return
        self._running = True
        self._btn.setEnabled(False)
        self._btn_recover.setEnabled(False)
        self._btn_recover.setText("Recuperando...")
        self._progress.setValue(0)
        self._progress_lbl.setText("Buscando lacunas...")
        thread = threading.Thread(target=self._run_recover, daemon=True)
        thread.start()
        QTimer.singleShot(150, self._poll)

    def _run_recover(self) -> None:
        from lotinha.extraction.api_client import ApiClient
        from lotinha.extraction.orchestrator import ExtractionOrchestrator

        api = ApiClient(
            base_url=str(self._settings.api_base_url),
            rate_limit=float(self._settings.api_rate_limit),
        )
        orchestrator = ExtractionOrchestrator(
            api_client=api,
            repo=self._repo,
            db_path=self._settings.db_path,
        )

        def progress(atual: int, total: int, data: date) -> None:
            self._q.put(("progress", atual, total, data))

        try:
            report = orchestrator.recover_gaps(progress_callback=progress)
            self._q.put(("done", report))
        except Exception as exc:
            self._q.put(("error", str(exc)))

    def _finish(self) -> None:
        self._running = False
        self._btn.setEnabled(True)
        self._btn.setText("Extrair")
        self._btn_recover.setEnabled(True)
        self._btn_recover.setText("Recuperar Lacunas")

    def _log_line(self, text: str, color: str = "") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        if color:
            self._log.append(
                f'<span style="color:{color}">[{ts}] {text}</span>'
            )
        else:
            self._log.append(f"[{ts}] {text}")
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())
