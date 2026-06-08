"""
_MonthGrid — QGridLayout-based single-month calendar view.

Row 0  : abbreviated day-name headers  (Su Mo Tu We Th Fr Sa)
Rows 1–6: day cells (42 cells total, 6 weeks × 7 days)

Used by CalendarTableWidget for both INPUT and OUTPUT modes.
"""

from __future__ import annotations

from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from src.models.enums import CalendarMode
from src.styles.calendar_table_style import GRID_COLOR
from src.views.shared_components.calendar_widgets._constants import (
    DAY_ABBREVS,
    DAY_COLOR_WEEKEND,
    DAY_HEADER_BG,
    DAY_HEADER_WEEKDAY_COLOR,
)
from src.views.shared_components.calendar_widgets.input_day_cell import InputDayCell
from src.views.shared_components.calendar_widgets.output_day_cell import OutputDayCell


class MonthGrid(QWidget):
    """Single-month grid widget shared between INPUT and OUTPUT modes."""

    input_day_toggled   = pyqtSignal(object)          # QDate
    output_exam_clicked = pyqtSignal(object, object)  # list[dict], QPoint

    def __init__(self, mode: CalendarMode, parent=None):
        super().__init__(parent)
        self._mode = mode
        self._setup_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        # Grey container acts as 1-px grid-line background
        container = QFrame()
        container.setStyleSheet(
            f"QFrame {{ background: {GRID_COLOR}; border-radius: 4px; }}"
        )

        self._grid = QGridLayout(container)
        self._grid.setSpacing(1)
        self._grid.setContentsMargins(1, 1, 1, 1)

        # Row 0: day-name headers
        for col, name in enumerate(DAY_ABBREVS):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedHeight(30)
            color = DAY_COLOR_WEEKEND if col in (0, 6) else DAY_HEADER_WEEKDAY_COLOR
            # Plain inline style (no selector) avoids Qt parse warnings
            lbl.setStyleSheet(
                f"color: {color}; font-size: 11px; font-weight: 700;"
                f" background: {DAY_HEADER_BG}; padding: 4px 0px;"
            )
            self._grid.addWidget(lbl, 0, col)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

    # ── Population — INPUT ────────────────────────────────────────────────────

    def populate_input(self, year: int, month: int,
                       start_date: QDate | None, end_date: QDate | None,
                       unavailable: set) -> None:
        """Fill the grid with InputDayCells for the given month, marking those in the selected range."""
        self._clear_cells()
        first     = QDate(year, month, 1)
        start_col = first.dayOfWeek() % 7   # Sun=0 … Sat=6

        for pos in range(42):
            row   = pos // 7 + 1
            col   = pos  % 7
            qdate = first.addDays(pos - start_col)
            is_other = qdate.month() != month

            cell = InputDayCell(qdate)
            cell.toggled.connect(self.input_day_toggled)

            if is_other:
                state = InputDayCell.STATE_OTHER
            elif qdate == start_date or qdate == end_date:
                state = InputDayCell.STATE_ANCHOR
            elif start_date and end_date and start_date <= qdate <= end_date:
                state = (InputDayCell.STATE_UNAVAIL
                         if qdate in unavailable
                         else InputDayCell.STATE_IN_RANGE)
            else:
                state = InputDayCell.STATE_NORMAL

            cell.set_state(state)
            self._grid.addWidget(cell, row, col)

    # ── Population — OUTPUT ───────────────────────────────────────────────────

    def populate_output(self, year: int, month: int,
                        exams_by_date: dict, unavail_dates: set) -> None:
        """Fill the grid with OutputDayCells for the given month, marking those with exams or unavailable."""
        self._clear_cells()
        first     = QDate(year, month, 1)
        start_col = first.dayOfWeek() % 7

        for pos in range(42):
            row      = pos // 7 + 1
            col      = pos  % 7
            qdate    = first.addDays(pos - start_col)
            is_other   = qdate.month() != month
            is_weekend = col in (0, 6)

            cell = OutputDayCell(qdate, is_other_month=is_other,
                                 is_weekend=is_weekend)
            cell.exam_clicked.connect(self.output_exam_clicked)

            if not is_other and qdate in unavail_dates:
                cell.set_unavailable()
            elif not is_other and qdate in exams_by_date:
                # Pass all exams for the day; OutputDayCell shows up to
                # MAX_VISIBLE_BADGES pills and a "+N" indicator for the rest
                cell.set_exams(exams_by_date[qdate])

            self._grid.addWidget(cell, row, col)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _clear_cells(self) -> None:
        """Remove all day cells from the grid (but keep the day-name headers intact)."""
        for row in range(1, 7):
            for col in range(7):
                item = self._grid.itemAtPosition(row, col)
                if item and item.widget():
                    item.widget().deleteLater()
                    self._grid.removeItem(item)
