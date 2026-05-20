"""Widget reutilizável: grade 5x5 dos números 1..25."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk


class NumberGrid(ctk.CTkFrame):
    """Grade 5x5 exibindo os números 1..25 com destaque configurável.

    Args:
        master: Widget pai.
        on_click: Callback opcional chamado com o número ao clicar.
    """

    _COL_DEFAULT  = ("gray80", "gray25")
    _COL_SELECTED = ("#2CC985", "#1A8A5A")   # verde
    _COL_TOP      = ("#F4A000", "#B07000")   # laranja (score alto)

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_click: Callable[[int], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_click = on_click
        self._buttons: dict[int, ctk.CTkButton] = {}
        self._highlighted: set[int] = set()
        self._build()

    # ── API pública ────────────────────────────────────────────────────────

    def highlight(self, numbers: list[int], *, top: list[int] | None = None) -> None:
        """Destaca os números da lista.

        Args:
            numbers: Números a destacar (verde).
            top: Subconjunto extra a destacar com cor diferente (laranja).
        """
        top_set = set(top or [])
        for num, btn in self._buttons.items():
            if num in top_set:
                btn.configure(fg_color=self._COL_TOP)
            elif num in numbers:
                btn.configure(fg_color=self._COL_SELECTED)
            else:
                btn.configure(fg_color=self._COL_DEFAULT)
        self._highlighted = set(numbers)

    def clear(self) -> None:
        for btn in self._buttons.values():
            btn.configure(fg_color=self._COL_DEFAULT)
        self._highlighted.clear()

    # ── Internals ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        for i, num in enumerate(range(1, 26)):
            row, col = divmod(i, 5)
            btn = ctk.CTkButton(
                self,
                text=str(num),
                width=52,
                height=52,
                corner_radius=8,
                fg_color=self._COL_DEFAULT,
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda n=num: self._clicked(n),
            )
            btn.grid(row=row, column=col, padx=4, pady=4)
            self._buttons[num] = btn

    def _clicked(self, num: int) -> None:
        if self._on_click:
            self._on_click(num)
