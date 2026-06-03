"""Widget reutilizável: grade 5x5 dos números 1..25."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget


class NumberGrid(QWidget):
    """Grade 5x5 exibindo os números 1..25 com destaque configurável.

    Args:
        parent: Widget pai.
        on_click: Callback opcional chamado com o número ao clicar.
    """

    _STYLE_DEFAULT = (
        "QPushButton {"
        "background-color: #1a1a2a; color: #2CC985; "
        "border: 1px solid #2CC985; border-radius: 8px; "
        "font-size: 16px; font-weight: bold;"
        "}"
        "QPushButton:hover { background-color: #222238; }"
    )
    _STYLE_SELECTED = (
        "QPushButton {"
        "background-color: #2CC985; color: #000000; "
        "border: 2px solid #2CC985; border-radius: 8px; "
        "font-size: 16px; font-weight: bold;"
        "}"
        "QPushButton:hover { background-color: #3ae0a0; }"
    )
    _STYLE_TOP = (
        "QPushButton {"
        "background-color: #F4A000; color: #000000; "
        "border: 2px solid #F4A000; border-radius: 8px; "
        "font-size: 16px; font-weight: bold;"
        "}"
        "QPushButton:hover { background-color: #ffb822; }"
    )

    def __init__(
        self,
        parent: QWidget | None = None,
        on_click: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_click = on_click
        self._buttons: dict[int, QPushButton] = {}
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
                btn.setStyleSheet(self._STYLE_TOP)
            elif num in numbers:
                btn.setStyleSheet(self._STYLE_SELECTED)
            else:
                btn.setStyleSheet(self._STYLE_DEFAULT)
        self._highlighted = set(numbers)

    def clear(self) -> None:
        for btn in self._buttons.values():
            btn.setStyleSheet(self._STYLE_DEFAULT)
        self._highlighted.clear()

    # ── Internals ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        layout = QGridLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(4, 4, 4, 4)

        font = QFont()
        font.setPointSize(13)
        font.setBold(True)

        for i, num in enumerate(range(1, 26)):
            row, col = divmod(i, 5)
            btn = QPushButton(str(num))
            btn.setFont(font)
            btn.setFixedSize(62, 62)
            btn.setStyleSheet(self._STYLE_DEFAULT)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, n=num: self._clicked(n))
            layout.addWidget(btn, row, col)
            self._buttons[num] = btn

    def _clicked(self, num: int) -> None:
        if self._on_click:
            self._on_click(num)
