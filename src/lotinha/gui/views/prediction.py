"""Tab 4 — Predição: gera números recomendados para o próximo sorteio."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import customtkinter as ctk

from lotinha.gui.widgets.number_grid import NumberGrid


class PredictionView(ctk.CTkFrame):
    def __init__(self, master: Any, repo: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._repo = repo
        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Predição de Números",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=(20, 8))

        # Painel esquerdo — controles
        ctrl = ctk.CTkFrame(self)
        ctrl.grid(row=1, column=0, padx=(20, 8), pady=8, sticky="nsew")
        ctrl.columnconfigure(1, weight=1)

        # Filtros
        row = 0
        for label, attr, values, width in [
            ("Banca:", "_banca_var", ["—"], 200),
            ("Horário:", "_hora_var", ["—"], 100),
        ]:
            ctk.CTkLabel(ctrl, text=label, anchor="w").grid(
                row=row, column=0, padx=12, pady=6, sticky="w")
            var = ctk.StringVar(value=values[0])
            setattr(self, attr, var)
            cb = ctk.CTkComboBox(ctrl, variable=var, values=values, width=width)
            cb.grid(row=row, column=1, padx=12, pady=6, sticky="w")
            setattr(self, attr + "_cb", cb)
            row += 1

        ctk.CTkLabel(ctrl, text="Data alvo:", anchor="w").grid(
            row=row, column=0, padx=12, pady=6, sticky="w")
        self._data_entry = ctk.CTkEntry(ctrl, placeholder_text="YYYY-MM-DD", width=160)
        self._data_entry.insert(0, str(date.today() + timedelta(days=1)))
        self._data_entry.grid(row=row, column=1, padx=12, pady=6, sticky="w")
        row += 1

        ctk.CTkLabel(ctrl, text="Estratégia:", anchor="w").grid(
            row=row, column=0, padx=12, pady=6, sticky="w")
        self._strat_var = ctk.StringVar(value="Frequência")
        ctk.CTkComboBox(
            ctrl, variable=self._strat_var,
            values=["Frequência", "Atraso", "Markov", "Ensemble"], width=160,
        ).grid(row=row, column=1, padx=12, pady=6, sticky="w")
        row += 1

        ctk.CTkLabel(ctrl, text="N preditos:", anchor="w").grid(
            row=row, column=0, padx=12, pady=6, sticky="w")
        self._n_var = ctk.IntVar(value=22)
        ctk.CTkSlider(ctrl, variable=self._n_var, from_=17, to=22, number_of_steps=5,
                       command=lambda v: self._n_label.configure(
                           text=str(int(v)))).grid(
            row=row, column=1, padx=12, pady=6, sticky="ew")
        row += 1
        self._n_label = ctk.CTkLabel(ctrl, text="22")
        self._n_label.grid(row=row, column=1, padx=12, sticky="w")
        row += 1

        ctk.CTkButton(ctrl, text="Gerar Predição", command=self._predict).grid(
            row=row, column=0, columnspan=2, pady=16)
        row += 1

        # Resultado texto
        self._result_lbl = ctk.CTkLabel(ctrl, text="", wraplength=280,
                                         justify="left", text_color="gray")
        self._result_lbl.grid(row=row, column=0, columnspan=2, padx=12, sticky="w")

        # Painel direito — grade de números
        right = ctk.CTkFrame(self)
        right.grid(row=1, column=1, padx=(8, 20), pady=8, sticky="nsew")

        ctk.CTkLabel(right, text="Números preditos",
                     font=ctk.CTkFont(size=14)).pack(pady=(12, 4))
        self._grid = NumberGrid(right)
        self._grid.pack(padx=16, pady=8)

        legend = ctk.CTkFrame(right, fg_color="transparent")
        legend.pack(pady=4)
        ctk.CTkLabel(legend, text="■", text_color="#2CC985").pack(side="left")
        ctk.CTkLabel(legend, text=" Predito  ").pack(side="left")
        ctk.CTkLabel(legend, text="■", text_color="gray60").pack(side="left")
        ctk.CTkLabel(legend, text=" Não predito").pack(side="left")

        self._load_filters()

    # ── Lógica ─────────────────────────────────────────────────────────────

    def _load_filters(self) -> None:
        try:
            bancas = sorted(self._repo.list_bancas())
            horarios = sorted(self._repo.list_horarios())
            self._banca_var_cb.configure(values=bancas)  # type: ignore[attr-defined]
            if bancas:
                self._banca_var.set(bancas[0])
            self._hora_var_cb.configure(values=[str(h) for h in horarios])  # type: ignore[attr-defined]
            if horarios:
                self._hora_var.set(str(horarios[0]))
        except Exception:
            pass

    def _predict(self) -> None:
        from lotinha.analysis.strategies import (
            AtrasoStrategy,
            EnsembleStrategy,
            FrequenciaStrategy,
            MarkovStrategy,
        )
        from lotinha.core.exceptions import InsufficientDataError

        banca = self._banca_var.get()
        hora_s = self._hora_var.get()
        n = int(self._n_var.get())
        strat_name = self._strat_var.get()

        try:
            hora = int(hora_s)
            df = self._repo.get_resultados(banca=banca, hora=hora)
        except Exception as exc:
            self._result_lbl.configure(text=f"Erro: {exc}", text_color="red")
            return

        if df.empty:
            self._result_lbl.configure(text="Sem dados para os filtros selecionados.",
                                        text_color="orange")
            return

        strat_map = {
            "Frequência": FrequenciaStrategy(),
            "Atraso": AtrasoStrategy(),
            "Markov": MarkovStrategy(),
            "Ensemble": EnsembleStrategy([
                FrequenciaStrategy(),
                AtrasoStrategy(),
                MarkovStrategy(),
            ]),
        }
        strategy = strat_map[strat_name]

        try:
            result = strategy.predict(df, n=n)
        except InsufficientDataError as exc:
            self._result_lbl.configure(
                text=f"Dados insuficientes: {exc}", text_color="orange")
            return
        except Exception as exc:
            self._result_lbl.configure(text=f"Erro: {exc}", text_color="red")
            return

        self._grid.highlight(result.numeros)
        self._result_lbl.configure(
            text=(
                f"Estratégia: {strat_name}\n"
                f"Números: {sorted(result.numeros)}\n"
                f"Confiança: {result.confidence:.1%}"
            ),
            text_color=("gray10", "gray90"),
        )
