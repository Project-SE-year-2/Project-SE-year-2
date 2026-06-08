"""
_InputDayCell — single day cell for CalendarMode.INPUT.

States
------
normal      : current month, outside the selected date range  → grey, not clickable
in_range    : inside the range, not marked                    → indigo, clickable
anchor      : the start or end date itself                    → filled indigo circle
unavailable : user-marked forbidden day                       → red, clickable
other_month : day that belongs to the previous/next month     → grey, not clickable
"""

from __future__ import annotations

from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from src.styles.calendar_table_style import (
    ANCHOR_BG,
    ANCHOR_TEXT,
    CELL_BG,
    CELL_DISABLED_BG,
    IN_RANGE_BG,
    IN_RANGE_TEXT,
    OTHER_MONTH_TEXT,
    OUT_RANGE_TEXT,
    UNAVAIL_IN_BG,
    UNAVAIL_IN_BORDER,
    UNAVAIL_IN_TEXT,
)


class InputDayCell(QFrame):
    """Single day cell for INPUT mode: circle-style day number."""

    toggled = pyqtSignal(object)   # emits QDate when clicked

    # Cell states
    STATE_NORMAL   = "normal"
    STATE_IN_RANGE = "in_range"
    STATE_ANCHOR   = "anchor"
    STATE_UNAVAIL  = "unavailable"
    STATE_OTHER    = "other_month"

    def __init__(self, qdate: QDate, parent=None):
        super().__init__(parent)
        self._qdate = qdate
        self._state = self.STATE_OTHER
        self._setup_ui()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(36, 40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setAlignment(Qt.AlignCenter)

        self._circle = QFrame()
        self._circle.setFixedSize(32, 32)
        self._circle.setObjectName("dayCircle")

        inner = QVBoxLayout(self._circle)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setAlignment(Qt.AlignCenter)

        self._num_lbl = QLabel(str(self._qdate.day()))
        self._num_lbl.setAlignment(Qt.AlignCenter)
        inner.addWidget(self._num_lbl)

        layout.addWidget(self._circle, 0, Qt.AlignCenter)
        self._apply_style()

    def _apply_style(self) -> None:
        """Set the cell's visual appearance according to its state."""
        s = self._state

        if s == self.STATE_ANCHOR:
            bg, fg, radius, cell_bg = ANCHOR_BG, ANCHOR_TEXT, "16px", CELL_BG
            cursor = Qt.PointingHandCursor
        elif s == self.STATE_UNAVAIL:
            bg, fg, radius, cell_bg = UNAVAIL_IN_BG, UNAVAIL_IN_TEXT, "6px", CELL_BG
            cursor = Qt.PointingHandCursor
        elif s == self.STATE_IN_RANGE:
            bg, fg, radius, cell_bg = IN_RANGE_BG, IN_RANGE_TEXT, "16px", CELL_BG
            cursor = Qt.PointingHandCursor
        elif s == self.STATE_OTHER:
            bg, fg, radius, cell_bg = CELL_DISABLED_BG, OTHER_MONTH_TEXT, "0px", CELL_DISABLED_BG
            cursor = Qt.ForbiddenCursor
        else:   # NORMAL — current month but outside selected range
            bg, fg, radius, cell_bg = CELL_DISABLED_BG, OUT_RANGE_TEXT, "0px", CELL_DISABLED_BG
            cursor = Qt.ArrowCursor

        self.setStyleSheet(f"QFrame {{ background: {cell_bg}; }}")

        circle_style = (
            f"QFrame#dayCircle {{ background: {UNAVAIL_IN_BG};"
            f" border: 1px solid {UNAVAIL_IN_BORDER}; border-radius: {radius}; }}"
            if s == self.STATE_UNAVAIL
            else f"QFrame#dayCircle {{ background: {bg}; border-radius: {radius}; }}"
        )
        self._circle.setStyleSheet(circle_style)
        self._num_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600;"
            f" background: transparent; color: {fg};"
        )
        self.setCursor(cursor)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        """Set the cell's state and update its appearance."""
        self._state = state
        self._apply_style()

    @property
    def is_interactive(self) -> bool:
        """Whether the cell is clickable."""
        return self._state in (self.STATE_IN_RANGE, self.STATE_UNAVAIL, self.STATE_ANCHOR)

    # ── Events ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        """Emit toggled signal with the cell's date if left-clicked and interactive."""
        if event.button() == Qt.LeftButton and self.is_interactive:
            self.toggled.emit(self._qdate)
        super().mousePressEvent(event)
