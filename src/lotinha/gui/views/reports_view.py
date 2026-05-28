"""Tab 6 — Relatórios: PDF de predições e Excel do histórico."""

from __future__ import annotations

import queue
import threading
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from lotinha.user_prefs import UserPrefs

_ROOT_FOLDER = "RELATÓRIOS DE PREDIÇÃO - LOTINHA"
_EXCEL_SUBFOLDER = "1 - PREDIÇÕES EXCEL"
_PDF_SUBFOLDER = "2 - PREDIÇÕES PDF"


class ReportsView(ctk.CTkFrame):
    def __init__(self, master: Any, repo: Any, settings: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._repo = repo
        self._settings = settings
        self._prefs = UserPrefs()
        self._q: queue.Queue = queue.Queue()
        self._running = False
        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Relatórios",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, pady=(20, 8))

        # ── Seção: Pasta de relatórios ──────────────────────────────────────
        dir_frame = ctk.CTkFrame(self)
        dir_frame.grid(row=1, column=0, padx=30, pady=(0, 8), sticky="ew")
        dir_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(dir_frame, text="Pasta de Relatórios",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#4FC3F7").grid(
            row=0, column=0, columnspan=4, padx=12, pady=(10, 6), sticky="w")

        ctk.CTkLabel(dir_frame, text="Pasta base:", anchor="w").grid(
            row=1, column=0, padx=12, pady=6, sticky="w")
        self._dir_var = ctk.StringVar(value=self._prefs.reports_dir)
        ctk.CTkEntry(dir_frame, textvariable=self._dir_var, width=360).grid(
            row=1, column=1, padx=(0, 4), pady=6, sticky="ew")
        ctk.CTkButton(dir_frame, text="...", width=36,
                      command=self._browse_dir).grid(row=1, column=2, padx=(0, 4))
        ctk.CTkButton(dir_frame, text="Salvar", width=72,
                      command=self._save_dir).grid(row=1, column=3, padx=(0, 12))

        self._dir_info = ctk.CTkLabel(
            dir_frame,
            text=self._dir_info_text(),
            font=ctk.CTkFont(size=10),
            text_color="gray60",
            anchor="w",
        )
        self._dir_info.grid(row=2, column=0, columnspan=4, padx=12, pady=(0, 8), sticky="w")

        # ── Seção PDF de Predições ──────────────────────────────────────────
        pdf_frame = ctk.CTkFrame(self)
        pdf_frame.grid(row=2, column=0, padx=30, pady=(0, 8), sticky="ew")
        pdf_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(pdf_frame, text="PDF de Predições",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#2CC985").grid(
            row=0, column=0, columnspan=3, padx=12, pady=(10, 6), sticky="w")

        ctk.CTkLabel(pdf_frame, text="Data alvo:", anchor="w").grid(
            row=1, column=0, padx=12, pady=6, sticky="w")
        self._data_entry = ctk.CTkEntry(pdf_frame, placeholder_text="YYYY-MM-DD", width=160)
        self._data_entry.insert(0, str(date.today() + timedelta(days=1)))
        self._data_entry.grid(row=1, column=1, padx=12, pady=6, sticky="w")

        ctk.CTkLabel(pdf_frame, text="Estratégia:", anchor="w").grid(
            row=2, column=0, padx=12, pady=6, sticky="w")
        self._strat_var = ctk.StringVar(value="Ensemble")
        ctk.CTkComboBox(pdf_frame, variable=self._strat_var,
                        values=["Frequência", "Atraso", "Markov", "Ensemble"],
                        width=160).grid(row=2, column=1, padx=12, pady=6, sticky="w")

        ctk.CTkLabel(pdf_frame, text="N preditos:", anchor="w").grid(
            row=3, column=0, padx=12, pady=6, sticky="w")
        self._n_var = ctk.StringVar(value="23")
        ctk.CTkComboBox(pdf_frame, variable=self._n_var,
                        values=["17", "18", "19", "20", "21", "22", "23"],
                        width=80).grid(row=3, column=1, padx=12, pady=6, sticky="w")

        self._btn_pdf = ctk.CTkButton(pdf_frame, text="Gerar PDF", width=160,
                                       command=self._start_pdf)
        self._btn_pdf.grid(row=4, column=0, columnspan=3, pady=12)

        # ── Seção Excel do Histórico ────────────────────────────────────────
        xls_frame = ctk.CTkFrame(self)
        xls_frame.grid(row=3, column=0, padx=30, pady=(0, 8), sticky="ew")
        xls_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(xls_frame, text="Excel do Histórico",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#F4A000").grid(
            row=0, column=0, columnspan=3, padx=12, pady=(10, 6), sticky="w")

        self._btn_xls = ctk.CTkButton(
            xls_frame, text="Gerar Excel", width=160,
            fg_color="#F4A000", hover_color="#B07000",
            command=self._start_excel,
        )
        self._btn_xls.grid(row=1, column=0, columnspan=3, pady=12)

        # ── Status e log ────────────────────────────────────────────────────
        self._status = ctk.CTkLabel(self, text="", text_color="gray")
        self._status.grid(row=4, column=0, pady=(4, 0))

        self._progress = ctk.CTkProgressBar(self, width=500)
        self._progress.grid(row=5, column=0, padx=30, pady=4)
        self._progress.set(0)

        self._log = ctk.CTkTextbox(self, height=120, state="disabled")
        self._log.grid(row=6, column=0, padx=30, pady=(4, 20), sticky="ew")

    # ── Pasta base ──────────────────────────────────────────────────────────

    def _dir_info_text(self) -> str:
        base = Path(self._dir_var.get()) if hasattr(self, "_dir_var") else Path(self._prefs.reports_dir)
        root = base / _ROOT_FOLDER
        return (
            f"Arquivos gerados em: {root}/\n"
            f"  PDF  → {_PDF_SUBFOLDER}/     Excel  → {_EXCEL_SUBFOLDER}/"
        )

    def _browse_dir(self) -> None:
        path = filedialog.askdirectory(initialdir=self._dir_var.get())
        if path:
            self._dir_var.set(path)
            self._dir_info.configure(text=self._dir_info_text())

    def _save_dir(self) -> None:
        new_dir = self._dir_var.get().strip()
        if not new_dir:
            self._log_line("Caminho inválido.", color="red")
            return
        self._prefs.reports_dir = new_dir
        self._dir_info.configure(text=self._dir_info_text())
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
        from datetime import datetime
        try:
            data_alvo = datetime.strptime(self._data_entry.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            self._log_line("Data inválida. Use o formato YYYY-MM-DD.", color="red")
            return

        estrategia = self._strat_var.get()
        output = self._pdf_output(data_alvo, estrategia)

        self._running = True
        self._btn_pdf.configure(state="disabled", text="Gerando PDF...")
        self._btn_xls.configure(state="disabled")
        self._progress.set(0)
        self._status.configure(text="Calculando predições...", text_color="gray")

        threading.Thread(
            target=self._run_pdf,
            args=(data_alvo, output, estrategia, int(self._n_var.get())),
            daemon=True,
        ).start()
        self.after(200, self._poll)

    def _run_pdf(self, data_alvo: date, output: Path,
                 estrategia: str, n: int) -> None:
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
        self._btn_pdf.configure(state="disabled")
        self._btn_xls.configure(state="disabled", text="Gerando Excel...")
        self._progress.set(0)
        self._status.configure(text="Exportando dados...", text_color="gray")

        threading.Thread(
            target=self._run_excel, args=(output,), daemon=True
        ).start()
        self.after(200, self._poll)

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
                    self._progress.set(1.0)
                    self._status.configure(text="PDF gerado!", text_color="#2CC985")
                    self._log_line(f"PDF salvo: {path}  ({n_ok} predições geradas)")
                    self._finish()
                    return
                elif kind == "done_excel":
                    _, path, total = item
                    self._progress.set(1.0)
                    self._status.configure(text="Excel gerado!", text_color="#F4A000")
                    self._log_line(f"Excel salvo: {path}  ({total} sorteios exportados)")
                    self._finish()
                    return
                elif kind == "error":
                    self._status.configure(text="Erro.", text_color="red")
                    self._log_line(f"Erro: {item[1]}", color="red")
                    self._finish()
                    return
        except queue.Empty:
            pass
        self._progress.set(self._progress.get() + 0.02 if self._progress.get() < 0.9 else 0.9)
        self.after(200, self._poll)

    def _finish(self) -> None:
        self._running = False
        self._btn_pdf.configure(state="normal", text="Gerar PDF")
        self._btn_xls.configure(state="normal", text="Gerar Excel")

    def _log_line(self, text: str, color: str = "white") -> None:
        from datetime import datetime
        self._log.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.insert("end", f"[{ts}] {text}\n")
        self._log.see("end")
        self._log.configure(state="disabled")
