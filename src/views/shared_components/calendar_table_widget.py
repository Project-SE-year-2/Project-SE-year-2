"""
CalendarTableWidget — EP-36 / EP-47
====================================
Shared calendar widget used by both the Input screen (period selector)
and the Output screen (schedule viewer).

Two modes
---------
CalendarMode.INPUT
    • Two-column layout: date pickers + Save button on the left,
      dual-month grid on the right.
    • Navigation arrows sit inline with the month titles:
        [‹]  June 2026    July 2026  [›]
    • Days inside the selected range are highlighted in indigo.
    • Clicking any in-range day toggles it as Unavailable (red).
    • Days outside the range / belonging to another month → grey cell.
    • Signals:
        day_clicked(QDate)              — day toggled
        date_range_changed(QDate, QDate)
        unavailable_changed(set[QDate])
        save_requested(QDate, QDate, set[QDate])

CalendarMode.OUTPUT
    • Single-month grid.
    • Weekday numbers → black.  Weekend (Sa/Su) numbers → red.
    • Unavailable days  → red day number + rose badge pill.
    • Exam cells        → indigo/green badge pill with course code + name.
    • Clicking a badge emits day_clicked(dict) → caller opens DayDetailDialog.
    • Call set_month_schedule(year, month, exams, unavailable_dates).

Internal sub-widgets live in the calendar_widgets/ sub-package:
    InputDayCell  — input_day_cell.py
    OutputDayCell — output_day_cell.py
    MonthGrid     — month_grid.py
"""

from __future__ import annotations

from datetime import date as _date_type

from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.models.enums import CalendarMode
from src.styles.calendar_table_style import (
    CALENDAR_CARD_STYLE,
    DATE_EDIT_STYLE,
    DATE_LABEL_STYLE,
    INPUT_LEGEND_ITEMS,
    LEGEND_DOT_STYLE_TPL,
    LEGEND_TEXT_STYLE,
    MONTH_TITLE_STYLE,
    NAV_BTN_STYLE,
    OUTPUT_LEGEND_ITEMS,
    SAVE_BTN_STYLE,
    SEPARATOR_COLOR,
)
from src.views.shared_components.calendar_widgets import InputDayCell, MonthGrid, OutputDayCell
from src.views.shared_components.calendar_widgets._constants import EN_LOCALE


# ===========================================================================
# CalendarTableWidget
# ===========================================================================

class CalendarTableWidget(QWidget):
    """
    Shared calendar widget.  See module docstring for full public API.
    """
    # INPUT signals
    day_clicked         = pyqtSignal(object)           # QDate of the toggled day
    date_range_changed  = pyqtSignal(object, object)   # start, end QDate
    unavailable_changed = pyqtSignal(object)            # set[QDate]
    save_requested      = pyqtSignal(object, object, object)  # start, end, unavailable

    # OUTPUT signals
    # exams_day_clicked — full list + anchor (for DayDetailDialog).
    exams_day_clicked   = pyqtSignal(object, object)   # list[dict], QPoint
    # exam_clicked — single exam dict (first in list); kept for backward
    #                compatibility with OutputScreen._on_exam_clicked.
    exam_clicked        = pyqtSignal(object)            # dict

    def __init__(self, mode: CalendarMode = CalendarMode.OUTPUT, parent=None):
        super().__init__(parent)
        self._mode = mode

        # INPUT state
        self._start_date: QDate | None = None
        self._end_date:   QDate | None = None
        self._unavailable: set         = set()

        # OUTPUT state
        self._exams_by_date: dict = {}
        self._unavail_out:   set  = set()

        # Current display page 
        self._page_year  = QDate.currentDate().year()
        self._page_month = QDate.currentDate().month()

        self._month_titles: list[QLabel]    = []
        self._month_grids:  list[MonthGrid] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the static UI elements.  Dynamic content is populated in _refresh()."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        card = QFrame()
        card.setObjectName("calendarCard")
        card.setStyleSheet(CALENDAR_CARD_STYLE)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        if self._mode == CalendarMode.INPUT:
            card_layout.addLayout(self._build_input_body())
        else:
            card_layout.addLayout(self._build_nav_header())
            card_layout.addLayout(self._build_grids_row())

        card_layout.addWidget(self._build_legend())
        outer.addWidget(card)

    # ── INPUT body: two-column layout ────────────────────────────────────────

    def _build_input_body(self) -> QHBoxLayout:
        """
        Left column : date pickers + Save button
        Right column: nav header (← Month1 Month2 →) + grids
        """
        main_row = QHBoxLayout()
        main_row.setSpacing(20)

        # ── Left column ───────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(12)
        left.setContentsMargins(0, 0, 0, 0)

        for label_text, attr in [("Start Date", "_start_edit"),
                                  ("End Date",   "_end_edit")]:
            col = QVBoxLayout()
            col.setSpacing(4)

            lbl = QLabel(label_text)
            lbl.setStyleSheet(DATE_LABEL_STYLE)

            edit = QDateEdit()
            edit.setStyleSheet(DATE_EDIT_STYLE)
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("dd/MM/yyyy")
            edit.setMinimumWidth(140)
            edit.setDate(QDate.currentDate())
            setattr(self, attr, edit)

            col.addWidget(lbl)
            col.addWidget(edit)
            left.addLayout(col)

        self._start_edit.dateChanged.connect(self._on_start_changed)
        self._end_edit.dateChanged.connect(self._on_end_changed)

        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet(SAVE_BTN_STYLE)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.setMinimumWidth(140)
        left.addWidget(self.save_btn)
        left.addStretch()

        main_row.addLayout(left)

        # ── Vertical separator ────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"QFrame {{ color: {SEPARATOR_COLOR}; }}")
        main_row.addWidget(sep)

        # ── Right column: nav + grids ─────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(8)
        right.addLayout(self._build_nav_header())
        right.addLayout(self._build_grids_row())
        main_row.addLayout(right, stretch=1)

        return main_row

    # ── Shared: nav header row  [‹]  Month1  Month2  [›] ─────────────────────

    def _build_nav_header(self) -> QHBoxLayout:
        """Row containing the month titles and navigation arrows (‹ ›)."""
        row = QHBoxLayout()
        row.setSpacing(6)

        self._prev_btn = QPushButton("‹")
        self._prev_btn.setStyleSheet(NAV_BTN_STYLE)
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.clicked.connect(self._on_prev_month)
        row.addWidget(self._prev_btn)

        n_months = 2 if self._mode == CalendarMode.INPUT else 1
        for _ in range(n_months):
            title = QLabel()
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet(MONTH_TITLE_STYLE)
            self._month_titles.append(title)
            row.addWidget(title, stretch=1)

        self._next_btn = QPushButton("›")
        self._next_btn.setStyleSheet(NAV_BTN_STYLE)
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(self._on_next_month)
        row.addWidget(self._next_btn)

        return row

    def _build_grids_row(self) -> QHBoxLayout:
        """Row containing one (OUTPUT) or two (INPUT) MonthGrid widgets."""
        row = QHBoxLayout()
        row.setSpacing(12)

        n_months = 2 if self._mode == CalendarMode.INPUT else 1
        for _ in range(n_months):
            grid = MonthGrid(self._mode)
            grid.input_day_toggled.connect(self._on_day_toggled)
            grid.output_exam_clicked.connect(self._on_exam_clicked)
            self._month_grids.append(grid)
            row.addWidget(grid)

        return row

    # ── Legend bar ────────────────────────────────────────────────────────────

    def _build_legend(self) -> QFrame:
        bar = QFrame()
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 6, 0, 0)
        row.setSpacing(0)
        row.addStretch()

        items = (INPUT_LEGEND_ITEMS if self._mode == CalendarMode.INPUT
                 else OUTPUT_LEGEND_ITEMS)

        for i, (color, label) in enumerate(items):
            dot = QLabel("●")
            dot.setStyleSheet(LEGEND_DOT_STYLE_TPL.format(color=color))
            lbl = QLabel(label)
            lbl.setStyleSheet(LEGEND_TEXT_STYLE)
            row.addWidget(dot)
            row.addSpacing(4)
            row.addWidget(lbl)
            if i < len(items) - 1:
                row.addSpacing(20)

        row.addStretch()
        return bar

    # ── Refresh ───────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        for i, grid in enumerate(self._month_grids):
            m = self._page_month + i
            y = self._page_year
            while m > 12:
                m -= 12
                y += 1

            self._month_titles[i].setText(
                EN_LOCALE.toString(QDate(y, m, 1), "MMMM yyyy")
            )

            if self._mode == CalendarMode.INPUT:
                grid.populate_input(y, m, self._start_date, self._end_date,
                                    self._unavailable)
            else:
                grid.populate_output(y, m, self._exams_by_date,
                                     self._unavail_out)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_prev_month(self) -> None:
        """Go to the previous month, adjusting the year if needed, and refresh the display."""
        self._page_month -= 1
        if self._page_month < 1:
            self._page_month = 12
            self._page_year -= 1
        self._refresh()

    def _on_next_month(self) -> None:
        """Go to the next month, adjusting the year if needed, and refresh the display."""
        self._page_month += 1
        if self._page_month > 12:
            self._page_month = 1
            self._page_year += 1
        self._refresh()

    # ── INPUT slots ───────────────────────────────────────────────────────────

    def _on_start_changed(self, qdate: QDate) -> None:
        """Set the start date, refresh the grid, and emit date_range_changed if end date is set."""
        self._start_date = qdate
        self._page_year  = qdate.year()
        self._page_month = qdate.month()
        self._refresh()
        if self._end_date:
            self.date_range_changed.emit(self._start_date, self._end_date)

    def _on_end_changed(self, qdate: QDate) -> None:
        """Set the end date, refresh the grid, and emit date_range_changed if start date is set."""
        self._end_date = qdate
        self._refresh()
        if self._start_date:
            self.date_range_changed.emit(self._start_date, self._end_date)

    def _on_day_toggled(self, qdate: QDate) -> None:
        """Toggle the given day as unavailable (red) or available, and emit signals."""
        if qdate == self._start_date or qdate == self._end_date:
            return
        if qdate in self._unavailable:
            self._unavailable.discard(qdate)
        else:
            self._unavailable.add(qdate)
        self._refresh()
        self.day_clicked.emit(qdate)
        self.unavailable_changed.emit(self._unavailable)

    def _on_save_clicked(self) -> None:
        """
        Emit save_requested so the parent widget can persist the changes.

        TODO (EP-54 — InputScreen):
            Wire this signal in InputScreen to call:
                service.shift_period(period_id, start.toPyDate(), end.toPyDate())
            and sync forbidden days via:
                service.toggle_day(period_id, day.toPyDate())
            for every day whose unavailable status changed since the last save.
        """
        if self._start_date and self._end_date:
            self.save_requested.emit(
                self._start_date,
                self._end_date,
                set(self._unavailable),   # defensive copy
            )

    # ── OUTPUT slot ───────────────────────────────────────────────────────────

    def _on_exam_clicked(self, exams: list, anchor) -> None:
        """Forward the full exam list + anchor position up so the parent can open DayDetailDialog."""
        self.exams_day_clicked.emit(exams, anchor)
        # Also emit the single-exam signal so OutputScreen._on_exam_clicked still works.
        if exams:
            self.exam_clicked.emit(exams[0])

    # ── Public API — INPUT ────────────────────────────────────────────────────

    def set_date_range(self, start: QDate, end: QDate) -> None:
        """Set the selected date range, which should be within the currently displayed month(s)."""
        self._start_date = start
        self._end_date   = end
        if hasattr(self, "_start_edit"):
            self._start_edit.blockSignals(True)
            self._end_edit.blockSignals(True)
            self._start_edit.setDate(start)
            self._end_edit.setDate(end)
            self._start_edit.blockSignals(False)
            self._end_edit.blockSignals(False)
        self._page_year  = start.year()
        self._page_month = start.month()
        self._refresh()

    def set_unavailable_days(self, days: list) -> None:
        """Set the unavailable days, which should be a list of QDate or datetime.date objects."""
        self._unavailable.clear()
        for d in days:
            if isinstance(d, QDate):
                self._unavailable.add(d)
            elif isinstance(d, _date_type):
                self._unavailable.add(QDate(d.year, d.month, d.day))
        self._refresh()

    def get_unavailable_days(self) -> list:
        return list(self._unavailable)

    # ── Shared helper ─────────────────────────────────────────────────────────

    def _to_qdate(self, value) -> QDate:
        """Convert QDate / datetime.date / 'yyyy-MM-dd' string → QDate.
        Returns an invalid QDate for any unrecognised value."""
        if isinstance(value, QDate):
            return value
        if isinstance(value, _date_type):
            return QDate(value.year, value.month, value.day)
        if isinstance(value, str):
            return QDate.fromString(value, "yyyy-MM-dd")
        return QDate()

    # ── Public API — OUTPUT ───────────────────────────────────────────────────

    @property
    def exams_by_date(self) -> dict:
        """Public read-only view of the internal date → exams mapping."""
        return self._exams_by_date

    def set_month_schedule(self, year: int, month: int, exams: list,
                           unavailable_dates: list | None = None) -> None:
        """Set the data for the given month, which must match the currently displayed page."""
        self._page_year  = year
        self._page_month = month

        self._exams_by_date.clear()
        for exam in exams:
            raw = exam.get("exam_date")
            if isinstance(raw, QDate):
                qd = raw
            elif isinstance(raw, _date_type):
                qd = QDate(raw.year, raw.month, raw.day)
            else:
                continue
            self._exams_by_date.setdefault(qd, []).append(exam)

        self._unavail_out.clear()
        for d in (unavailable_dates or []):
            if isinstance(d, QDate):
                self._unavail_out.add(d)
            elif isinstance(d, _date_type):
                self._unavail_out.add(QDate(d.year, d.month, d.day))

        self._refresh()

    def update_schedule(self, schedule_data: list,
                        unavailable_dates: list | None = None) -> None:
        """Convenience wrapper used by OutputScreen.

        Parses a flat list of exam dicts, determines the month to display
        from the first valid exam_date, then delegates to set_month_schedule().
        """
        if not schedule_data:
            self.set_month_schedule(self._page_year, self._page_month,
                                    [], unavailable_dates)
            return

        # Find the first valid date to anchor the display month.
        year, month = self._page_year, self._page_month
        for exam in schedule_data:
            qd = self._to_qdate(exam.get("exam_date"))
            if qd.isValid():
                year, month = qd.year(), qd.month()
                break

        self.set_month_schedule(year, month, schedule_data, unavailable_dates)
