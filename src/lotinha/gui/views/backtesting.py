"""Tab 5 — Backtesting: valida estratégias com walk-forward + Wilcoxon."""

from __future__ import annotations

import queue
import threading
from typing import Any

import customtkinter as ctk


class BacktestingView(ctk.CTkFrame):
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

        ctk.CTkLabel(self, text="Backtesting Walk-Forward",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, pady=(20, 8))

        # Configuração
        cfg = ctk.CTkFrame(self)
        cfg.grid(row=1, column=0, padx=30, pady=8, sticky="ew")
        cfg.columnconfigure(1, weight=1)
        cfg.columnconfigure(3, weight=1)

        # Linha 0
        ctk.CTkLabel(cfg, text="Banca:", anchor="w").grid(
            row=0, column=0, padx=12, pady=6, sticky="w")
        self._banca_var = ctk.StringVar(value="—")
        self._banca_cb = ctk.CTkComboBox(cfg, variable=self._banca_var,
                                          values=["—"], width=220)
        self._banca_cb.grid(row=0, column=1, padx=12, pady=6, sticky="w")

        ctk.CTkLabel(cfg, text="Horário:", anchor="w").grid(
            row=0, column=2, padx=12, pady=6, sticky="w")
        self._hora_var = ctk.StringVar(value="—")
        self._hora_cb = ctk.CTkComboBox(cfg, variable=self._hora_var,
                                         values=["—"], width=100)
        self._hora_cb.grid(row=0, column=3, padx=12, pady=6, sticky="w")

        # Linha 1
        ctk.CTkLabel(cfg, text="Estratégia:", anchor="w").grid(
            row=1, column=0, padx=12, pady=6, sticky="w")
        self._strat_var = ctk.StringVar(value="Frequência")
        ctk.CTkComboBox(cfg, variable=self._strat_var,
                        values=["Frequência", "Atraso", "Markov", "Ensemble"],
                        width=160).grid(row=1, column=1, padx=12, pady=6, sticky="w")

        ctk.CTkLabel(cfg, text="N preditos:", anchor="w").grid(
            row=1, column=2, padx=12, pady=6, sticky="w")
        self._n_var = ctk.StringVar(value="22")
        ctk.CTkComboBox(cfg, variable=self._n_var,
                        values=["17", "18", "19", "20", "21", "22"],
                        width=80).grid(row=1, column=3, padx=12, pady=6, sticky="w")

        # Linha 2
        ctk.CTkLabel(cfg, text="Treino mín (draws):", anchor="w").grid(
            row=2, column=0, padx=12, pady=6, sticky="w")
        self._train_entry = ctk.CTkEntry(cfg, width=80)
        self._train_entry.insert(0, "60")
        self._train_entry.grid(row=2, column=1, padx=12, pady=6, sticky="w")

        # Prêmios rápidos
        ctk.CTkLabel(cfg, text="Prêmios (11..15 acertos), separados por vírgula:",
                     anchor="w").grid(row=3, column=0, columnspan=2, padx=12, pady=4,
                                       sticky="w")
        self._premios_entry = ctk.CTkEntry(cfg, width=320,
                                            placeholder_text="ex: 5,20,50,200,1000")
        self._premios_entry.grid(row=4, column=0, columnspan=2, padx=12, pady=4,
                                  sticky="ew")

        ctk.CTkLabel(cfg, text="Custo por aposta (R$):", anchor="w").grid(
            row=3, column=2, padx=12, pady=4, sticky="w")
        self._custo_entry = ctk.CTkEntry(cfg, width=100)
        self._custo_entry.insert(0, "2.00")
        self._custo_entry.grid(row=4, column=2, columnspan=2, padx=12, pady=4,
                                sticky="w")

        # Botão
        self._btn = ctk.CTkButton(self, text="Executar Backtest", width=200,
                                   command=self._start)
        self._btn.grid(row=2, column=0, pady=12)

        # Progresso
        self._progress = ctk.CTkProgressBar(self, width=500)
        self._progress.grid(row=3, column=0, padx=30)
        self._progress.set(0)
        self._prog_lbl = ctk.CTkLabel(self, text="", text_color="gray")
        self._prog_lbl.grid(row=4, column=0)

        # Resultados
        res_frame = ctk.CTkFrame(self)
        res_frame.grid(row=5, column=0, padx=30, pady=8, sticky="ew")
        res_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self._res_labels: dict[str, ctk.CTkLabel] = {}
        metrics = [
            ("Média acertos (estratégia)", "acertos_strat"),
            ("Média acertos (aleatório)", "acertos_rand"),
            ("ROI estratégia", "roi_strat"),
            ("p-value (Wilcoxon)", "pvalue"),
        ]
        for col, (text, key) in enumerate(metrics):
            ctk.CTkLabel(res_frame, text=text, font=ctk.CTkFont(size=11),
                         text_color="gray").grid(row=0, column=col, padx=8, pady=(8, 2))
            lbl = ctk.CTkLabel(res_frame, text="—", font=ctk.CTkFont(size=18, weight="bold"))
            lbl.grid(row=1, column=col, padx=8, pady=(2, 8))
            self._res_labels[key] = lbl

        # Aviso honesto
        self._warning_frame = ctk.CTkFrame(self, fg_color=("#FFE5E5", "#4A1010"),
                                            corner_radius=8)
        self._warning_lbl = ctk.CTkLabel(
            self._warning_frame, text="", wraplength=640,
            text_color=("#CC0000", "#FF8080"), font=ctk.CTkFont(size=13, weight="bold"),
            justify="center",
        )
        self._warning_lbl.pack(padx=16, pady=12)

        self._load_filters()

    # ── Lógica ─────────────────────────────────────────────────────────────

    def _load_filters(self) -> None:
        try:
            bancas = sorted(self._repo.list_bancas())
            horarios = sorted(self._repo.list_horarios())
            self._banca_cb.configure(values=bancas or ["—"])
            if bancas:
                self._banca_var.set(bancas[0])
            self._hora_cb.configure(values=[str(h) for h in horarios] or ["—"])
            if horarios:
                self._hora_var.set(str(horarios[0]))
        except Exception:
            pass

    def _parse_premios(self) -> dict[int, float]:
        text = self._premios_entry.get().strip()
        if not text:
            return {}
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 5:
            raise ValueError("Informe exatamente 5 valores separados por vírgula (11..15 acertos)")
        return {11 + i: float(p) for i, p in enumerate(parts)}

    def _start(self) -> None:
        if self._running:
            return
        try:
            premios = self._parse_premios()
            custo = float(self._custo_entry.get().strip())
            train_size = int(self._train_entry.get().strip())
            n_preditos = int(self._n_var.get())
        except ValueError as exc:
            self._prog_lbl.configure(text=f"Parâmetro inválido: {exc}", text_color="red")
            return

        self._running = True
        self._btn.configure(state="disabled", text="Executando...")
        self._progress.set(0)
        self._warning_frame.grid_forget()

        thread = threading.Thread(
            target=self._run_backtest,
            args=(premios, custo, train_size, n_preditos),
            daemon=True,
        )
        thread.start()
        self.after(200, self._poll)

    def _run_backtest(self, premios: dict[int, float], custo: float,
                      train_size: int, n_preditos: int) -> None:
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
        strategy = strat_map[self._strat_var.get()]
        banca = self._banca_var.get()
        hora_s = self._hora_var.get()

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
            result = bt.run(df, strategy, n_preditos=n_preditos,
                             train_size=train_size, progress_callback=progress)
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
                    self._progress.set(atual / total if total else 0)
                    self._prog_lbl.configure(text=f"[{atual}/{total}]",
                                              text_color="gray")
                elif kind == "done":
                    self._show_result(item[1])
                    self._finish()
                    return
                elif kind == "error":
                    self._prog_lbl.configure(text=f"Erro: {item[1]}", text_color="red")
                    self._finish()
                    return
        except queue.Empty:
            pass
        self.after(200, self._poll)

    def _show_result(self, result: Any) -> None:
        self._progress.set(1.0)
        self._prog_lbl.configure(text=f"Concluído — {result.n_draws_tested} draws testados.",
                                  text_color="gray")
        self._res_labels["acertos_strat"].configure(
            text=f"{result.mean_acertos_strategy:.2f}")
        self._res_labels["acertos_rand"].configure(
            text=f"{result.mean_acertos_random:.2f}")
        roi_str = f"{result.roi_strategy:+.1%}"
        roi_color = "#2CC985" if result.roi_strategy >= 0 else "#FF5555"
        self._res_labels["roi_strat"].configure(text=roi_str, text_color=roi_color)
        p_str = f"{result.p_value:.3f}" if result.p_value is not None else "N/A"
        self._res_labels["pvalue"].configure(text=p_str)

        if result.warning:
            self._warning_lbl.configure(text=result.warning)
            self._warning_frame.grid(row=6, column=0, padx=30, pady=8, sticky="ew")
        else:
            self._warning_frame.grid_forget()

    def _finish(self) -> None:
        self._running = False
        self._btn.configure(state="normal", text="Executar Backtest")
