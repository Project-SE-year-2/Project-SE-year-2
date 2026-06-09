"""
FourMonthOutputWidget
=====================
White card displaying one exam schedule as a dynamic horizontal row of months.

Layout inside the card
-----------------------
Header row:  [ FALL 2026 / subtitle] 
Content:     <months side-by-side in a QHBoxLayout — rebuilt dynamically on each update>
Legend:      Required Course · Elective Course · Unavailable Day · No Exam

States (QStackedWidget)
-----------------------
Page 0  normal   — horizontal MonthGrid cards
Page 1  loading  — spinner text
Page 2  error    — error message
Page 3  empty    — "No schedules" message

Public API
----------
update_schedule(rows, unavailable_dates, semester, start_date, end_date)
    Load exam rows and rebuild month columns from the period date range.

show_loading(semester)  / show_error(msg) / show_empty(semester)

navigator : ScheduleNavigatorWidget  (exposed for OutputScreen)

Signals
-------
exam_day_clicked(list[dict], QPoint)
moed_changed(str)   — "Aleph" | "Bet"
"""

from __future__ import annotations

from datetime import date as _date

from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.models.enums import CalendarMode
from src.styles.calendar_table_style import (
    LEGEND_DOT_STYLE_TPL,
    LEGEND_TEXT_STYLE,
    OUTPUT_LEGEND_ITEMS,
)
from src.views.shared_components.calendar_widgets import MonthGrid
from src.views.shared_components.calendar_widgets._constants import EN_LOCALE
from src.views.shared_components.schedule_navigator_widget import ScheduleNavigatorWidget


# ── Semester helpers ──────────────────────────────────────────────────────────

_SEMESTER_DEFAULT_MONTHS: dict[str, list[int]] = {
    "FALL":   [9, 10, 11, 12],
    "SPRING": [1,  2,  3,  4],
}

_SEMESTER_ICONS = {
    "FALL":   "🍃",
    "SPRING": "🌸",
}

_MOED_INFO = {
    "Aleph": "You are viewing the first exam session.\nSwitch to see the second exam session.",
    "Bet":   "You are viewing the second exam session.\nSwitch to see the first exam session.",
}


def _to_qdate(value) -> QDate:
    if isinstance(value, QDate):
        return value
    if isinstance(value, _date):
        return QDate(value.year, value.month, value.day)
    if isinstance(value, str):
        return QDate.fromString(value, "yyyy-MM-dd")
    return QDate()


def _months_from_range(start: _date | None, end: _date | None) -> list[tuple[int, int]]:
    """Return (year, month) pairs covering start … end (inclusive)."""
    if start is None or end is None:
        return []
    cur = _date(start.year, start.month, 1)
    fin = _date(end.year,   end.month,   1)
    result: list[tuple[int, int]] = []
    while cur <= fin:
        result.append((cur.year, cur.month))
        # advance one month
        if cur.month == 12:
            cur = _date(cur.year + 1, 1, 1)
        else:
            cur = _date(cur.year, cur.month + 1, 1)
    return result


def _detect_semester_and_year(exams_by_date: dict) -> tuple[str, int]:
    if not exams_by_date:
        return "FALL", QDate.currentDate().year()
    qdates = list(exams_by_date.keys())
    months = {d.month() for d in qdates}
    year   = qdates[0].year()
    for sem, month_list in _SEMESTER_DEFAULT_MONTHS.items():
        if months & set(month_list):
            return sem, year
    return "FALL", year


# ── Page indices ──────────────────────────────────────────────────────────────

_PAGE_NORMAL    = 0
_PAGE_LOADING   = 1
_PAGE_ERROR     = 2
_PAGE_EMPTY     = 3
_PAGE_NO_PERIOD = 4

_MONTH_CARD_STYLE = """
    QFrame#monthCard {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
    }
"""


class FourMonthOutputWidget(QWidget):
    """White card: semester header + moed toggle + horizontal months + legend."""

    exam_day_clicked = pyqtSignal(object, object)   # list[dict], QPoint
    moed_changed     = pyqtSignal(str)              # "Aleph" | "Bet"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._exams_by_date: dict = {}
        self._unavail_dates: set  = set()
        self._months: list[tuple[int, int]] = []
        self._month_grids:  list[MonthGrid] = []
        self._current_moed: str = "Aleph"
        self._setup_ui()

    # ──────────────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._card = QFrame()
        self._card.setObjectName("outputCard")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(16)

        card_layout.addLayout(self._build_card_header())

        self._stack = QStackedWidget()
        self._months_page = self._build_months_page()
        self._stack.addWidget(self._months_page)           # 0 — normal
        self._stack.addWidget(self._build_loading_page())   # 1 — loading
        self._stack.addWidget(self._build_error_page())     # 2 — error
        self._stack.addWidget(self._build_empty_page())     # 3 — empty
        self._stack.addWidget(self._build_no_period_page()) # 4 — no period
        self._stack.setCurrentIndex(_PAGE_NORMAL)
        card_layout.addWidget(self._stack, stretch=1)

        card_layout.addWidget(self._build_legend())
        outer.addWidget(self._card)

    # ── Card header ───────────────────────────────────────────────────────────

    def _build_card_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        # Left block: emoji icon + title stack
        self._icon_lbl = QLabel("🍃")
        self._icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        self._icon_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row.addWidget(self._icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._semester_title    = QLabel("FALL 2026")
        self._semester_title.setObjectName("semesterTitle")
        self._semester_subtitle = QLabel("")
        self._semester_subtitle.setObjectName("semesterSubtitle")
        title_col.addWidget(self._semester_title)
        title_col.addWidget(self._semester_subtitle)
        row.addLayout(title_col)

        row.addStretch()

        # Centre-left: מועד א / מועד ב / מועד ג toggle
        self._moed_aleph_btn = QPushButton("מועד א  📅")
        self._moed_aleph_btn.setObjectName("moedBtnSelected")
        self._moed_aleph_btn.setCursor(Qt.PointingHandCursor)
        self._moed_aleph_btn.clicked.connect(lambda: self._on_moed_btn("Aleph"))

        self._moed_bet_btn = QPushButton("מועד ב  📅")
        self._moed_bet_btn.setObjectName("moedBtn")
        self._moed_bet_btn.setCursor(Qt.PointingHandCursor)
        self._moed_bet_btn.clicked.connect(lambda: self._on_moed_btn("Bet"))

        self._moed_gimel_btn = QPushButton("מועד ג  📅")
        self._moed_gimel_btn.setObjectName("moedBtn")
        self._moed_gimel_btn.setCursor(Qt.PointingHandCursor)
        self._moed_gimel_btn.clicked.connect(lambda: self._on_moed_btn("Gimel"))

        row.addWidget(self._moed_aleph_btn)
        row.addSpacing(6)
        row.addWidget(self._moed_bet_btn)
        row.addSpacing(6)
        row.addWidget(self._moed_gimel_btn)
        row.addSpacing(14)

        # Right: navigator
        self.navigator = ScheduleNavigatorWidget()
        row.addWidget(self.navigator)

        return row

    # ── Months page (normal) ──────────────────────────────────────────────────

    def _build_months_page(self) -> QWidget:
        page = QWidget()
        self._months_layout = QHBoxLayout(page)
        self._months_layout.setSpacing(16)
        self._months_layout.setContentsMargins(0, 0, 0, 0)
        return page

    # ── State pages ───────────────────────────────────────────────────────────

    def _build_state_page(self, icon: str, text: str, color: str) -> QWidget:
        page   = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            f"font-size: 36px; color: {color}; background: transparent;"
        )
        text_lbl = QLabel(text)
        text_lbl.setAlignment(Qt.AlignCenter)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 500; color: {color}; background: transparent;"
        )
        layout.addStretch()
        layout.addWidget(icon_lbl)
        layout.addSpacing(8)
        layout.addWidget(text_lbl)
        layout.addStretch()
        return page

    def _build_loading_page(self) -> QWidget:
        page = self._build_state_page("⏳", "Loading schedules...", "#64748B")
        self._loading_lbl = page.findChildren(QLabel)[1]
        return page

    def _build_error_page(self) -> QWidget:
        page = self._build_state_page("⚠", "Could not load schedules.\nPlease try again.", "#DC2626")
        self._error_lbl = page.findChildren(QLabel)[1]
        return page

    def _build_empty_page(self) -> QWidget:
        page = self._build_state_page("📅", "No schedules available for this semester.", "#94A3B8")
        self._empty_lbl = page.findChildren(QLabel)[1]
        return page

    def _build_no_period_page(self) -> QWidget:
        """Styled warning banner shown when the active period doesn't exist in the loaded data."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setAlignment(Qt.AlignCenter)
        outer.setContentsMargins(32, 32, 32, 32)

        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: #FEF2F2; border: 1.5px solid #FECACA; border-radius: 12px; }"
        )
        banner.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        row = QHBoxLayout(banner)
        row.setContentsMargins(20, 18, 20, 18)
        row.setSpacing(14)

        icon_lbl = QLabel("⚠️")
        icon_lbl.setStyleSheet("font-size: 26px; background: transparent;")
        icon_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row.addWidget(icon_lbl)

        self._no_period_lbl = QLabel("No exam period exists for this semester and session.")
        self._no_period_lbl.setWordWrap(True)
        self._no_period_lbl.setStyleSheet(
            "color: #991B1B; font-size: 14px; font-weight: 600; background: transparent;"
        )
        row.addWidget(self._no_period_lbl, stretch=1)

        outer.addStretch()
        outer.addWidget(banner)
        outer.addStretch()
        return page

    # ── Legend ────────────────────────────────────────────────────────────────

    def _build_legend(self) -> QFrame:
        bar = QFrame()
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(0)
        row.addStretch()

        for i, (color, label_text) in enumerate(OUTPUT_LEGEND_ITEMS):
            swatch = QLabel("■")
            swatch.setStyleSheet(LEGEND_DOT_STYLE_TPL.format(color=color))
            lbl = QLabel(label_text)
            lbl.setStyleSheet(LEGEND_TEXT_STYLE)
            row.addWidget(swatch)
            row.addSpacing(4)
            row.addWidget(lbl)
            if i < len(OUTPUT_LEGEND_ITEMS) - 1:
                row.addSpacing(20)

        row.addStretch()
        return bar

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _on_moed_btn(self, moed: str) -> None:
        if moed == self._current_moed:
            return
        self._current_moed = moed
        self._apply_moed_style()
        self.moed_changed.emit(moed)

    def _apply_moed_style(self) -> None:
        self._moed_aleph_btn.setObjectName(
            "moedBtnSelected" if self._current_moed == "Aleph" else "moedBtn"
        )
        self._moed_bet_btn.setObjectName(
            "moedBtnSelected" if self._current_moed == "Bet" else "moedBtn"
        )
        self._moed_gimel_btn.setObjectName(
            "moedBtnSelected" if self._current_moed == "Gimel" else "moedBtn"
        )
        # Force Qt to re-evaluate the stylesheet (object-name changed)
        for btn in (self._moed_aleph_btn, self._moed_bet_btn, self._moed_gimel_btn):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _on_cell_clicked(self, exams: list, anchor) -> None:
        self.exam_day_clicked.emit(exams, anchor)

    def _rebuild_month_cards(self) -> None:
        """Clear and recreate one MonthGrid card per month in self._months."""
        # Remove all existing widgets from the horizontal layout
        while self._months_layout.count():
            item = self._months_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._month_grids.clear()

        for year, month in self._months:
            card = QFrame()
            card.setObjectName("monthCard")
            card.setStyleSheet(_MONTH_CARD_STYLE)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.setSpacing(8)

            title = QLabel(EN_LOCALE.toString(QDate(year, month, 1), "MMMM yyyy"))
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet(
                "color: #111827; font-size: 13px; font-weight: 700;"
                " background: transparent;"
            )
            cl.addWidget(title)

            mg = MonthGrid(CalendarMode.OUTPUT)
            mg.output_exam_clicked.connect(self._on_cell_clicked)
            mg.populate_output(year, month, self._exams_by_date, self._unavail_dates)
            self._month_grids.append(mg)
            cl.addWidget(mg, stretch=1)

            self._months_layout.addWidget(card)

    def _update_header(self, semester: str, year: int) -> None:
        icon = _SEMESTER_ICONS.get(semester, "📅")
        self._icon_lbl.setText(icon)
        self._semester_title.setText(f"{semester} {year}")

        if self._months:
            fy, fm = self._months[0]
            ly, lm = self._months[-1]
            start = EN_LOCALE.toString(QDate(fy, fm, 1), "MMMM yyyy")
            end   = EN_LOCALE.toString(QDate(ly, lm, 1), "MMMM yyyy")
            self._semester_subtitle.setText(f"{start} – {end}")
        else:
            self._semester_subtitle.setText("")

    def _compute_months_from_exams(self, semester: str) -> list[tuple[int, int]]:
        """Fallback: derive months from exam dates when no date range is given."""
        if not self._exams_by_date:
            y = QDate.currentDate().year()
            return [(y, m) for m in _SEMESTER_DEFAULT_MONTHS.get(semester, [9, 10, 11, 12])]

        qdates   = sorted(self._exams_by_date.keys())
        min_d, max_d = qdates[0], qdates[-1]

        def _idx(qd: QDate) -> int:    return qd.year() * 12 + qd.month()
        def _pair(i: int) -> tuple:
            y, m = divmod(i - 1, 12)
            return y, m + 1

        start_idx = _idx(min_d)
        end_idx   = max(_idx(max_d), start_idx + 3)
        return [_pair(i) for i in range(start_idx, min(end_idx + 1, start_idx + 4))]

    # ──────────────────────────────────────────────────────────────────────────
    # Public API — state switching
    # ──────────────────────────────────────────────────────────────────────────

    def show_loading(self, semester: str = "") -> None:
        name = semester or "schedules"
        self._loading_lbl.setText(f"Loading {name} schedules…")
        self._icon_lbl.setText(_SEMESTER_ICONS.get(semester, "⏳"))
        self._semester_title.setText(semester or "—")
        self._semester_subtitle.setText("")
        self._stack.setCurrentIndex(_PAGE_LOADING)

    def show_error(self, message: str = "") -> None:
        self._error_lbl.setText(
            message or "Could not load schedules.\nPlease try again."
        )
        self._stack.setCurrentIndex(_PAGE_ERROR)

    def show_empty(self, semester: str = "") -> None:
        name = semester or "this semester"
        self._empty_lbl.setText(f"No schedules available for {name}.")
        self._stack.setCurrentIndex(_PAGE_EMPTY)

    def show_schedule(self) -> None:
        self._stack.setCurrentIndex(_PAGE_NORMAL)

    def show_no_period(self, semester: str = "", moed: str = "") -> None:
        """Show 'no schedules' state when the period doesn't exist in the data."""
        # Reuse the same empty-state page so the appearance is consistent.
        name = semester or "this semester"
        self._empty_lbl.setText(f"No schedules available for {name}.")
        self._stack.setCurrentIndex(_PAGE_EMPTY)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API — data loading
    # ──────────────────────────────────────────────────────────────────────────

    def update_schedule(
        self,
        rows: list[dict],
        unavailable_dates: list | None = None,
        semester: str = "",
        start_date: _date | None = None,
        end_date:   _date | None = None,
    ) -> None:
        """Rebuild the calendar from exam rows.

        If ``start_date`` and ``end_date`` are supplied (from the period
        metadata) the columns are determined by the exact date range.
        Otherwise they fall back to auto-detecting months from the exam dates.
        """
        # Index exams by QDate
        self._exams_by_date.clear()
        for exam in rows:
            qd = _to_qdate(exam.get("exam_date"))
            if qd.isValid():
                self._exams_by_date.setdefault(qd, []).append(exam)

        # Index unavailable dates
        self._unavail_dates.clear()
        for d in (unavailable_dates or []):
            qd = _to_qdate(d)
            if qd.isValid():
                self._unavail_dates.add(qd)

        # Determine months to show
        if start_date is not None and end_date is not None:
            self._months = _months_from_range(start_date, end_date)
        else:
            self._months = self._compute_months_from_exams(semester)

        # Determine semester name + year for the header
        sem, year = _detect_semester_and_year(self._exams_by_date)
        sem = semester or sem

        self._update_header(sem, year)
        self._rebuild_month_cards()
        self.show_schedule()
