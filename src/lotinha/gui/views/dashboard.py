"""Tab 1 — Dashboard: estatísticas gerais do banco."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk


class DashboardView(ctk.CTkFrame):
    def __init__(self, master: Any, repo: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._repo = repo
        self._build()
        self.refresh()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        title = ctk.CTkLabel(self, text="Dashboard", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, pady=(20, 10))

        self._card = ctk.CTkFrame(self)
        self._card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        self._card.columnconfigure(1, weight=1)

        labels = [
            "Total de sorteios",
            "Data mais antiga",
            "Data mais recente",
            "Dias com dados",
            "Bancas disponíveis",
            "Horários disponíveis",
        ]
        self._values: dict[str, ctk.CTkLabel] = {}
        for i, lbl in enumerate(labels):
            ctk.CTkLabel(self._card, text=lbl + ":", anchor="w",
                         font=ctk.CTkFont(weight="bold")).grid(
                row=i, column=0, sticky="w", padx=16, pady=6)
            val = ctk.CTkLabel(self._card, text="—", anchor="w")
            val.grid(row=i, column=1, sticky="w", padx=16, pady=6)
            self._values[lbl] = val

        btn = ctk.CTkButton(self, text="Atualizar", width=140, command=self.refresh)
        btn.grid(row=2, column=0, pady=16)

        self._status = ctk.CTkLabel(self, text="", text_color="gray")
        self._status.grid(row=3, column=0)

    # ── Lógica ─────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        try:
            total = self._repo.count_total()
            latest = self._repo.latest_date()
            bancas = self._repo.list_bancas()
            horarios = self._repo.list_horarios()
            dates = self._repo.dates_with_data()

            self._set("Total de sorteios", str(total))
            self._set("Data mais antiga", str(min(dates)) if dates else "—")
            self._set("Data mais recente", str(latest) if latest else "—")
            self._set("Dias com dados", str(len(dates)))
            self._set("Bancas disponíveis",
                       ", ".join(sorted(bancas)) if bancas else "—")
            self._set("Horários disponíveis",
                       "  ".join(f"{h}h" for h in sorted(horarios)) if horarios else "—")
            self._status.configure(text="Atualizado com sucesso.", text_color="green")
        except Exception as exc:
            self._status.configure(text=f"Erro: {exc}", text_color="red")

    def _set(self, key: str, value: str) -> None:
        self._values[key].configure(text=value)
