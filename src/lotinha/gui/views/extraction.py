"""Tab 2 — Extração: busca sorteios da API para um intervalo de datas."""

from __future__ import annotations

import queue
import threading
from datetime import date, datetime
from typing import Any

import customtkinter as ctk


class ExtractionView(ctk.CTkFrame):
    def __init__(self, master: Any, repo: Any, settings: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._repo = repo
        self._settings = settings
        self._q: queue.Queue = queue.Queue()
        self._running = False
        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Extração de Dados",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, pady=(20, 10))

        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, padx=30, pady=8, sticky="ew")
        form.columnconfigure(1, weight=1)

        # Datas
        ctk.CTkLabel(form, text="Data início:", anchor="w").grid(
            row=0, column=0, padx=12, pady=8, sticky="w")
        self._inicio = ctk.CTkEntry(form, placeholder_text="YYYY-MM-DD", width=160)
        self._inicio.grid(row=0, column=1, padx=12, pady=8, sticky="w")
        self._inicio.insert(0, str(date.today().replace(day=1)))

        ctk.CTkLabel(form, text="Data fim:", anchor="w").grid(
            row=1, column=0, padx=12, pady=8, sticky="w")
        self._fim = ctk.CTkEntry(form, placeholder_text="YYYY-MM-DD", width=160)
        self._fim.grid(row=1, column=1, padx=12, pady=8, sticky="w")
        self._fim.insert(0, str(date.today()))

        # Opções
        self._skip_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(form, text="Pular datas já presentes",
                        variable=self._skip_var).grid(
            row=2, column=0, columnspan=2, padx=12, pady=4, sticky="w")

        self._backup_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(form, text="Criar backup antes de extrair",
                        variable=self._backup_var).grid(
            row=3, column=0, columnspan=2, padx=12, pady=4, sticky="w")

        # Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=12)
        self._btn = ctk.CTkButton(btn_frame, text="Extrair", width=160, command=self._start)
        self._btn.pack(side="left", padx=8)
        self._btn_recover = ctk.CTkButton(
            btn_frame, text="Recuperar Lacunas", width=180,
            fg_color="#F4A000", hover_color="#B07000",
            command=self._start_recover,
        )
        self._btn_recover.pack(side="left", padx=8)

        # Progresso
        self._progress = ctk.CTkProgressBar(self, width=500)
        self._progress.grid(row=3, column=0, padx=30, pady=4)
        self._progress.set(0)

        self._progress_label = ctk.CTkLabel(self, text="", text_color="gray")
        self._progress_label.grid(row=4, column=0)

        # Log
        self._log = ctk.CTkTextbox(self, height=200, state="disabled")
        self._log.grid(row=5, column=0, padx=30, pady=(8, 20), sticky="ew")

    # ── Lógica ─────────────────────────────────────────────────────────────

    def _start(self) -> None:
        if self._running:
            return
        try:
            d_inicio = datetime.strptime(self._inicio.get().strip(), "%Y-%m-%d").date()
            d_fim = datetime.strptime(self._fim.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            self._log_line("Datas inválidas. Use o formato YYYY-MM-DD.", color="red")
            return

        if d_inicio > d_fim:
            self._log_line("Data início deve ser ≤ data fim.", color="red")
            return

        self._running = True
        self._btn.configure(state="disabled", text="Extraindo...")
        self._progress.set(0)
        self._progress_label.configure(text="Iniciando...")

        thread = threading.Thread(
            target=self._run_extraction,
            args=(d_inicio, d_fim),
            daemon=True,
        )
        thread.start()
        self.after(150, self._poll)

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
                skip_existing=self._skip_var.get(),
                backup_before=self._backup_var.get(),
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
                    self._progress.set(frac)
                    self._progress_label.configure(
                        text=f"[{atual}/{total}] {data}")
                elif kind == "done":
                    report = item[1]
                    self._progress.set(1.0)
                    if report.total_dias == 0:
                        self._progress_label.configure(text="Nenhuma lacuna encontrada.")
                        self._log_line("Nenhuma lacuna para recuperar.")
                    else:
                        self._progress_label.configure(text="Concluído.")
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
                    self._log_line(f"Erro: {item[1]}", color="red")
                    self._finish()
                    return
        except queue.Empty:
            pass
        self.after(150, self._poll)

    def _start_recover(self) -> None:
        if self._running:
            return
        self._running = True
        self._btn.configure(state="disabled")
        self._btn_recover.configure(state="disabled", text="Recuperando...")
        self._progress.set(0)
        self._progress_label.configure(text="Buscando lacunas...")
        thread = threading.Thread(target=self._run_recover, daemon=True)
        thread.start()
        self.after(150, self._poll)

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
        self._btn.configure(state="normal", text="Extrair")
        self._btn_recover.configure(state="normal", text="Recuperar Lacunas")

    def _log_line(self, text: str, color: str = "white") -> None:
        self._log.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.insert("end", f"[{ts}] {text}\n")
        self._log.see("end")
        self._log.configure(state="disabled")
