"""Tab 3 — Análise: frequências, atraso e co-ocorrências."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class AnalysisView(ctk.CTkFrame):
    def __init__(self, master: Any, repo: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._repo = repo
        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text="Análise Estatística",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, pady=(20, 8))

        # Filtros
        filt = ctk.CTkFrame(self)
        filt.grid(row=1, column=0, padx=30, pady=4, sticky="ew")

        ctk.CTkLabel(filt, text="Banca:").pack(side="left", padx=(12, 4))
        self._banca_var = ctk.StringVar(value="Todas")
        self._banca_cb = ctk.CTkComboBox(filt, variable=self._banca_var,
                                          values=["Todas"], width=200)
        self._banca_cb.pack(side="left", padx=4)

        ctk.CTkLabel(filt, text="Horário:").pack(side="left", padx=(12, 4))
        self._hora_var = ctk.StringVar(value="Todos")
        self._hora_cb = ctk.CTkComboBox(filt, variable=self._hora_var,
                                         values=["Todos"], width=100)
        self._hora_cb.pack(side="left", padx=4)

        ctk.CTkLabel(filt, text="Janela:").pack(side="left", padx=(12, 4))
        self._janela_var = ctk.StringVar(value="Todos")
        ctk.CTkComboBox(filt, variable=self._janela_var,
                        values=["Todos", "30", "60", "90", "180"],
                        width=100).pack(side="left", padx=4)

        ctk.CTkButton(filt, text="Analisar", command=self._analisar).pack(
            side="left", padx=16)

        # Tipo de gráfico
        tipo_frame = ctk.CTkFrame(self)
        tipo_frame.grid(row=2, column=0, padx=30, pady=4, sticky="w")
        ctk.CTkLabel(tipo_frame, text="Exibir:").pack(side="left", padx=(12, 4))
        self._tipo_var = ctk.StringVar(value="Frequência")
        ctk.CTkComboBox(tipo_frame, variable=self._tipo_var,
                        values=["Frequência", "Atraso"],
                        width=160, command=lambda _: self._analisar()).pack(
            side="left", padx=4)

        # Matplotlib canvas
        fig = Figure(figsize=(9, 4), dpi=96, tight_layout=True)
        self._ax = fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(fig, master=self)
        self._canvas.get_tk_widget().grid(
            row=3, column=0, padx=20, pady=10, sticky="nsew")

        self._status = ctk.CTkLabel(self, text="Selecione os filtros e clique em Analisar.",
                                     text_color="gray")
        self._status.grid(row=4, column=0, pady=4)

        self._load_filters()

    # ── Lógica ─────────────────────────────────────────────────────────────

    def _load_filters(self) -> None:
        try:
            bancas = self._repo.list_bancas()
            horarios = self._repo.list_horarios()
            self._banca_cb.configure(values=["Todas", *sorted(bancas)])
            self._hora_cb.configure(
                values=["Todos", *(str(h) for h in sorted(horarios))])
        except Exception:
            pass

    def _analisar(self) -> None:
        from lotinha.analysis.statistics import atraso, frequencia

        banca = self._banca_var.get()
        hora_s = self._hora_var.get()
        janela_s = self._janela_var.get()

        banca_filter = None if banca == "Todas" else banca
        hora_filter = None if hora_s == "Todos" else int(hora_s)
        janela = None if janela_s == "Todos" else int(janela_s)

        try:
            df = self._repo.get_resultados(
                banca=banca_filter,
                hora=hora_filter,
            )
        except Exception as exc:
            self._status.configure(text=f"Erro: {exc}", text_color="red")
            return

        if df.empty:
            self._status.configure(text="Sem dados para os filtros selecionados.",
                                    text_color="orange")
            return

        tipo = self._tipo_var.get()
        self._ax.clear()

        if tipo == "Frequência":
            scores = frequencia(df, janela)
            self._ax.bar(scores.index, scores.values, color="#2CC985", edgecolor="none")
            self._ax.set_title(f"Frequência relativa — {banca} / {hora_s}h")
            self._ax.set_xlabel("Número")
            self._ax.set_ylabel("Frequência")
            self._ax.axhline(15 / 25, color="red", linestyle="--",
                              linewidth=1, label="Esperado (15/25)")
            self._ax.legend(fontsize=8)
        else:
            scores = atraso(df).astype(float)
            self._ax.bar(scores.index, scores.values, color="#F4A000", edgecolor="none")
            self._ax.set_title(f"Atraso (sorteios sem aparecer) — {banca} / {hora_s}h")
            self._ax.set_xlabel("Número")
            self._ax.set_ylabel("Atraso (sorteios)")

        self._ax.set_xticks(range(1, 26))
        self._canvas.draw()
        n = len(df)
        self._status.configure(text=f"{n} sorteios analisados.", text_color="gray")
