"""
MoedCalendarOutputWidget
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
    QScrollArea,
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
from src.styles.output_screen_style import (
    ALL_SESSIONS_MOED_COLORS,
    ALL_SESSIONS_MOED_LABELS,
    ALL_SESSIONS_MONTH_CARD_STYLE,
    ALL_SESSIONS_SECTION_STYLE_TPL,
    MONTH_NAV_LABEL_SIZE,
    MONTH_NAV_LABEL_WEIGHT,
    SEMESTER_TITLE_COLOR,
)
from src.styles.icons import load_pixmap, SEMESTER_ICON, ICON_CALENDAR
from src.views.shared_components.calendar_widgets import MonthGrid
from src.views.shared_components.calendar_widgets._constants import EN_LOCALE
from src.views.shared_components.schedule_navigator_widget import ScheduleNavigatorWidget


# ── Semester helpers ──────────────────────────────────────────────────────────

_SEMESTER_DEFAULT_MONTHS: dict[str, list[int]] = {
    "FALL":   [9, 10, 11, 12],
    "SPRING": [1,  2,  3,  4],
}

# Maps semester id → icon name (see src/styles/icons.py)
_SEMESTER_ICONS = SEMESTER_ICON  # {"FALL": "fall", "SPRING": "spring", "SUMMER": "summer"}

_MOED_INFO = {
    "Aleph": "You are viewing the first exam session.\nSwitch to see another exam session.",
    "Bet":   "You are viewing the second exam session.\nSwitch to see another exam session.",
    "Gimel": "You are viewing the third exam session.\nSwitch to see another exam session.",
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

_PAGE_NORMAL       = 0
_PAGE_LOADING      = 1
_PAGE_ERROR        = 2
_PAGE_EMPTY        = 3
_PAGE_NO_PERIOD    = 4
_PAGE_ALL_SESSIONS = 5

# ── All-Sessions view constants (imported from styles/output_screen_style.py) ─
# Use ALL_SESSIONS_MOED_COLORS, ALL_SESSIONS_MOED_LABELS, ALL_SESSIONS_CARD_WIDTH,
# ALL_SESSIONS_MONTH_CARD_STYLE, ALL_SESSIONS_SECTION_STYLE_TPL from the style module.

# Local alias kept for the normal month cards (shared between normal and All Sessions pages)
_MONTH_CARD_STYLE = ALL_SESSIONS_MONTH_CARD_STYLE

_MONTH_NAV_LABEL_STYLE = (
    f"color: {SEMESTER_TITLE_COLOR}; font-size: {MONTH_NAV_LABEL_SIZE}px;"
    f" font-weight: {MONTH_NAV_LABEL_WEIGHT}; background: transparent;"
)


class MoedCalendarOutputWidget(QWidget):
    """White card: semester header + moed toggle + horizontal months + legend."""

    exam_day_clicked = pyqtSignal(object, object)   # list[dict], QPoint
    moed_changed     = pyqtSignal(str)              # "Aleph" | "Bet" | "Gimel"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._exams_by_date: dict = {}
        self._unavail_dates: set  = set()
        self._months: list[tuple[int, int]] = []
        self._month_grids:  list[MonthGrid] = []
        self._current_moed: str = "Aleph"
        self._current_month_idx: int = 0
        self._multi_month_mode: bool = False
        self._period_start: _date | None = None
        self._period_end:   _date | None = None
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
        self._stack.addWidget(self._months_page)              # 0 — normal
        self._stack.addWidget(self._build_loading_page())     # 1 — loading
        self._stack.addWidget(self._build_error_page())       # 2 — error
        self._stack.addWidget(self._build_empty_page())       # 3 — empty
        self._stack.addWidget(self._build_no_period_page())   # 4 — no period
        self._stack.addWidget(self._build_all_sessions_page())# 5 — all sessions
        self._stack.setCurrentIndex(_PAGE_NORMAL)
        card_layout.addWidget(self._stack, stretch=1)

        card_layout.addWidget(self._build_legend())
        outer.addWidget(self._card)

    # ── Card header ───────────────────────────────────────────────────────────

    def _build_card_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        # Left block: title stack

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
        self._moed_aleph_btn = QPushButton("Moed A")
        self._moed_aleph_btn.setObjectName("moedBtnSelected")
        self._moed_aleph_btn.setCursor(Qt.PointingHandCursor)
        self._moed_aleph_btn.clicked.connect(lambda: self._on_moed_btn("Aleph"))

        self._moed_bet_btn = QPushButton("Moed B")
        self._moed_bet_btn.setObjectName("moedBtn")
        self._moed_bet_btn.setCursor(Qt.PointingHandCursor)
        self._moed_bet_btn.clicked.connect(lambda: self._on_moed_btn("Bet"))

        self._moed_gimel_btn = QPushButton("Moed C")
        self._moed_gimel_btn.setObjectName("moedBtn")
        self._moed_gimel_btn.setCursor(Qt.PointingHandCursor)
        self._moed_gimel_btn.clicked.connect(lambda: self._on_moed_btn("Gimel"))

        self._moed_all_btn = QPushButton("All Sessions")
        self._moed_all_btn.setObjectName("moedBtn")
        self._moed_all_btn.setCursor(Qt.PointingHandCursor)
        self._moed_all_btn.clicked.connect(lambda: self._on_moed_btn("All"))

        # Left: schedule navigator (hidden automatically in All Sessions mode)
        self.navigator = ScheduleNavigatorWidget()
        row.addWidget(self.navigator)
        row.addSpacing(14)

        row.addWidget(self._moed_aleph_btn)
        row.addSpacing(6)
        row.addWidget(self._moed_bet_btn)
        row.addSpacing(6)
        row.addWidget(self._moed_gimel_btn)
        row.addSpacing(6)
        row.addWidget(self._moed_all_btn)

        return row

    # ── Months page (normal) ──────────────────────────────────────────────────

    def _build_months_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(8)

        # Month navigation bar - shown only in single-month mode when 2+ months exist
        self._month_nav_bar = QWidget()
        nav_row = QHBoxLayout(self._month_nav_bar)
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.setSpacing(8)

        self._prev_month_btn = QPushButton("‹")
        self._prev_month_btn.setObjectName("navArrowBtn")
        self._prev_month_btn.setCursor(Qt.PointingHandCursor)
        self._prev_month_btn.clicked.connect(self._on_prev_month)

        self._month_nav_label = QLabel("")
        self._month_nav_label.setAlignment(Qt.AlignCenter)
        self._month_nav_label.setStyleSheet(_MONTH_NAV_LABEL_STYLE)

        self._next_month_btn = QPushButton("›")
        self._next_month_btn.setObjectName("navArrowBtn")
        self._next_month_btn.setCursor(Qt.PointingHandCursor)
        self._next_month_btn.clicked.connect(self._on_next_month)

        nav_row.addStretch()
        nav_row.addWidget(self._prev_month_btn)
        nav_row.addSpacing(12)
        nav_row.addWidget(self._month_nav_label)
        nav_row.addSpacing(12)
        nav_row.addWidget(self._next_month_btn)
        nav_row.addStretch()

        self._month_nav_bar.setVisible(False)
        page_layout.addWidget(self._month_nav_bar)

        # Month cards - added directly to the layout
        self._months_layout = QHBoxLayout()
        self._months_layout.setSpacing(16)
        self._months_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addLayout(self._months_layout, 1)

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
        # Build inline so we can use a pixmap for the calendar icon
        page   = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")
        pix = load_pixmap(ICON_CALENDAR, size=36)
        if not pix.isNull():
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("📅")
            icon_lbl.setStyleSheet("font-size: 36px; color: #94A3B8; background: transparent;")

        self._empty_lbl = QLabel("No schedules available for this semester.")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        self._empty_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 500; color: #94A3B8; background: transparent;"
        )

        layout.addStretch()
        layout.addWidget(icon_lbl)
        layout.addSpacing(8)
        layout.addWidget(self._empty_lbl)
        layout.addStretch()
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

    def set_active_moed(self, moed: str) -> None:
        """Silently reset the active moed button without emitting moed_changed."""
        self._current_moed = moed
        self._apply_moed_style()
        self.navigator.setVisible(moed != "All")

    def _on_moed_btn(self, moed: str) -> None:
        if moed == self._current_moed:
            return
        self._current_moed = moed
        self._apply_moed_style()
        # Hide the navigator in All Sessions mode (read-only overview, no pagination)
        self.navigator.setVisible(moed != "All")
        self.moed_changed.emit(moed)

    def _apply_moed_style(self) -> None:
        moed = self._current_moed
        self._moed_aleph_btn.setObjectName("moedBtnSelected" if moed == "Aleph" else "moedBtn")
        self._moed_bet_btn.setObjectName("moedBtnSelected"   if moed == "Bet"   else "moedBtn")
        self._moed_gimel_btn.setObjectName("moedBtnSelected" if moed == "Gimel" else "moedBtn")
        self._moed_all_btn.setObjectName("moedBtnSelected"   if moed == "All"   else "moedBtn")
        for btn in (self._moed_aleph_btn, self._moed_bet_btn,
                    self._moed_gimel_btn, self._moed_all_btn):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _on_cell_clicked(self, exams: list, anchor) -> None:
        self.exam_day_clicked.emit(exams, anchor)

    def _rebuild_month_cards(self) -> None:
        """Clear and recreate MonthGrid cards.

        In single-month mode (default) only the card for _current_month_idx is
        rendered and the prev/next nav bar is visible when the period spans
        multiple months.  In multi-month mode all months are rendered side-by-side
        and the nav bar is hidden.
        """
        # Remove all existing widgets from the horizontal layout
        while self._months_layout.count():
            item = self._months_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._month_grids.clear()

        if not self._months:
            self._month_nav_bar.setVisible(False)
            return

        # Clamp index to valid range after period changes
        self._current_month_idx = max(0, min(self._current_month_idx, len(self._months) - 1))

        months_to_show = self._months if self._multi_month_mode else [self._months[self._current_month_idx]]

        pstart = QDate(self._period_start.year, self._period_start.month, self._period_start.day) if self._period_start else None
        pend   = QDate(self._period_end.year,   self._period_end.month,   self._period_end.day)   if self._period_end   else None

        for year, month in months_to_show:
            card = QFrame()
            card.setObjectName("monthCard")
            card.setStyleSheet(_MONTH_CARD_STYLE)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.setSpacing(8)

            if self._multi_month_mode or len(self._months) <= 1:
                title = QLabel(EN_LOCALE.toString(QDate(year, month, 1), "MMMM yyyy"))
                title.setAlignment(Qt.AlignCenter)
                title.setStyleSheet(_MONTH_NAV_LABEL_STYLE)
                cl.addWidget(title)

            mg = MonthGrid(CalendarMode.OUTPUT)
            mg.output_exam_clicked.connect(self._on_cell_clicked)
            mg.populate_output(year, month, self._exams_by_date, self._unavail_dates,
                               period_start=pstart, period_end=pend)
            self._month_grids.append(mg)
            cl.addWidget(mg, stretch=1)

            self._months_layout.addWidget(card)

        self._update_month_nav_bar()

    def _update_month_nav_bar(self) -> None:
        """Refresh the prev/next buttons and month label in the nav bar.

        The nav bar is hidden when in multi-month mode or when the period
        spans only a single month (nothing to navigate to).
        """
        n = len(self._months)
        visible = not self._multi_month_mode and n > 1
        self._month_nav_bar.setVisible(visible)
        if not visible:
            return

        i = self._current_month_idx
        year, month = self._months[i]
        self._month_nav_label.setText(
            f"{EN_LOCALE.toString(QDate(year, month, 1), 'MMMM yyyy')}  ({i + 1} / {n})"
        )
        self._prev_month_btn.setEnabled(i > 0)
        self._next_month_btn.setEnabled(i < n - 1)

    def _on_prev_month(self) -> None:
        if self._current_month_idx > 0:
            self._current_month_idx -= 1
            self._rebuild_month_cards()

    def _on_next_month(self) -> None:
        if self._current_month_idx < len(self._months) - 1:
            self._current_month_idx += 1
            self._rebuild_month_cards()

    def set_display_mode(self, *, multi_month: bool) -> None:
        """Switch between single-month (default) and multi-month display.

        multi_month=False  — one month at a time with ‹ / › navigation.
        multi_month=True   — all months side-by-side (original behaviour).

        Side effects: rebuilds month cards, resets navigation bar visibility,
        and keeps the current month index unchanged.
        """
        if multi_month == self._multi_month_mode:
            return
        self._multi_month_mode = multi_month
        self._rebuild_month_cards()

    def _update_header(self, semester: str, year: int) -> None:
        self._semester_title.setText(f"{semester} {year}")

        if self._period_start and self._period_end:
            qs = QDate(self._period_start.year, self._period_start.month, self._period_start.day)
            qe = QDate(self._period_end.year,   self._period_end.month,   self._period_end.day)
            start = EN_LOCALE.toString(qs, "d MMM yyyy")
            end   = EN_LOCALE.toString(qe, "d MMM yyyy")
            self._semester_subtitle.setText(f"{start} – {end}")
        elif self._months:
            fy, fm = self._months[0]
            ly, lm = self._months[-1]
            start = EN_LOCALE.toString(QDate(fy, fm, 1), "MMMM yyyy")
            end   = EN_LOCALE.toString(QDate(ly, lm, 1), "MMMM yyyy")
            self._semester_subtitle.setText(f"{start} – {end}")
        else:
            self._semester_subtitle.setText("")

    # ── All-Sessions builders ──────────────────────────────────────────────────

    def _build_all_sessions_page(self) -> QScrollArea:
        """Outer scrollable container for the grouped moed sections."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        self._all_sessions_content = QWidget()
        self._all_sessions_content.setStyleSheet("background: transparent;")
        self._all_sessions_vbox = QVBoxLayout(self._all_sessions_content)
        self._all_sessions_vbox.setSpacing(16)
        self._all_sessions_vbox.setContentsMargins(0, 4, 0, 4)
        self._all_sessions_vbox.addStretch()

        scroll.setWidget(self._all_sessions_content)
        return scroll

    def _build_moed_section(
        self,
        moed:       str,
        semester:   str,
        year:       int,
        exams:      list[dict],
        start_date,
        end_date,
    ) -> QFrame:
        """One horizontal row for a single moed inside the All Sessions page."""
        label = ALL_SESSIONS_MOED_LABELS.get(moed, moed)
        color = ALL_SESSIONS_MOED_COLORS.get(moed, "#64748B")

        # Section frame with thick left accent border (style from output_screen_style.py)
        section = QFrame()
        section.setStyleSheet(ALL_SESSIONS_SECTION_STYLE_TPL.format(color=color))

        outer_row = QHBoxLayout(section)
        outer_row.setContentsMargins(0, 0, 0, 0)
        outer_row.setSpacing(0)

        # ── Left info panel ──────────────────────────────────────────────────
        info_w = QWidget()
        info_w.setFixedWidth(145)
        info_w.setStyleSheet("background: transparent; border: none;")
        info_col = QVBoxLayout(info_w)
        info_col.setContentsMargins(16, 16, 12, 16)
        info_col.setSpacing(4)
        info_col.setAlignment(Qt.AlignTop)

        moed_lbl = QLabel(label)
        moed_lbl.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: 700;"
            " background: transparent; border: none;"
        )
        info_col.addWidget(moed_lbl)

        months = _months_from_range(start_date, end_date) if (start_date and end_date) else []
        n = len(months)
        dur_lbl = QLabel(f"{n} month{'s' if n != 1 else ''}" if n else "—")
        dur_lbl.setStyleSheet(
            "color: #64748B; font-size: 11px; background: transparent; border: none;"
        )
        info_col.addWidget(dur_lbl)

        if start_date and end_date:
            qs = QDate(start_date.year, start_date.month, start_date.day)
            qe = QDate(end_date.year,   end_date.month,   end_date.day)
            rng = QLabel(
                f"{EN_LOCALE.toString(qs, 'MMM yyyy')}"
                f" – {EN_LOCALE.toString(qe, 'MMM yyyy')}"
            )
            rng.setStyleSheet(
                "color: #94A3B8; font-size: 10px; background: transparent; border: none;"
            )
            info_col.addWidget(rng)

        info_col.addStretch()
        outer_row.addWidget(info_w)

        # Thin vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: #E5E7EB; border: none;")
        outer_row.addWidget(sep)

        # ── Content area: month cards OR empty state ─────────────────────────
        if not exams:
            empty_w = QWidget()
            empty_w.setStyleSheet("background: transparent; border: none;")
            empty_col = QVBoxLayout(empty_w)
            empty_col.setAlignment(Qt.AlignCenter)
            empty_col.setContentsMargins(24, 24, 24, 24)

            icon_e = QLabel()
            icon_e.setAlignment(Qt.AlignCenter)
            icon_e.setStyleSheet("background: transparent; border: none;")
            _pix_e = load_pixmap(ICON_CALENDAR, size=26)
            if not _pix_e.isNull():
                icon_e.setPixmap(_pix_e)
            else:
                icon_e.setText("📅")
                icon_e.setStyleSheet("font-size: 26px; background: transparent; border: none;")
            empty_col.addWidget(icon_e)
            empty_col.addSpacing(8)

            msg = QLabel(
                f"No exams scheduled for {label} in {semester} {year}."
            )
            msg.setAlignment(Qt.AlignCenter)
            msg.setWordWrap(True)
            msg.setStyleSheet(
                "color: #94A3B8; font-size: 13px; font-weight: 600;"
                " background: transparent; border: none;"
            )
            empty_col.addWidget(msg)

            sub = QLabel("There are no exam dates in this session.")
            sub.setAlignment(Qt.AlignCenter)
            sub.setStyleSheet(
                "color: #CBD5E1; font-size: 11px; background: transparent; border: none;"
            )
            empty_col.addWidget(sub)
            empty_w.setMinimumHeight(140)
            outer_row.addWidget(empty_w, stretch=1)

        else:
            # Build exams-by-date index
            exams_by_date: dict = {}
            for exam in exams:
                qd = _to_qdate(exam.get("exam_date"))
                if qd.isValid():
                    exams_by_date.setdefault(qd, []).append(exam)

            pstart = QDate(start_date.year, start_date.month, start_date.day) if start_date else None
            pend   = QDate(end_date.year,   end_date.month,   end_date.day)   if end_date   else None

            months_w = QWidget()
            months_w.setStyleSheet("background: transparent; border: none;")
            months_row = QHBoxLayout(months_w)
            months_row.setSpacing(12)
            months_row.setContentsMargins(12, 12, 12, 12)

            for yr_m, mo_m in months:
                card = QFrame()
                card.setObjectName("monthCard")
                card.setStyleSheet(ALL_SESSIONS_MONTH_CARD_STYLE)
                card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                cl = QVBoxLayout(card)
                cl.setContentsMargins(10, 10, 10, 10)
                cl.setSpacing(6)

                title = QLabel(EN_LOCALE.toString(QDate(yr_m, mo_m, 1), "MMMM yyyy"))
                title.setAlignment(Qt.AlignCenter)
                title.setStyleSheet(
                    "color: #111827; font-size: 12px; font-weight: 700;"
                    " background: transparent; border: none;"
                )
                cl.addWidget(title)

                mg = MonthGrid(CalendarMode.OUTPUT)
                mg.output_exam_clicked.connect(self._on_cell_clicked)
                mg.populate_output(
                    yr_m, mo_m, exams_by_date, set(),
                    period_start=pstart, period_end=pend,
                )
                cl.addWidget(mg, stretch=1)
                months_row.addWidget(card)

            months_row.addStretch()
            outer_row.addWidget(months_w, stretch=1)

        return section

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

        self._semester_title.setText(f"{semester}" if semester else "—")
        self._semester_subtitle.setText("")
        self._stack.setCurrentIndex(_PAGE_EMPTY)

    def show_schedule(self) -> None:
        self._stack.setCurrentIndex(_PAGE_NORMAL)

    def show_no_period(self, semester: str = "", moed: str = "") -> None:
        """Show 'no schedules' state when the period doesn't exist in the data."""
        name = semester or "this semester"
        self._empty_lbl.setText(f"No schedules available for {name}.")
        self._semester_title.setText(f"{semester}" if semester else "—")
        self._semester_subtitle.setText("")
        self._stack.setCurrentIndex(_PAGE_EMPTY)

    def show_all_sessions(self, semester: str, sections: list[dict]) -> None:
        """Render the All Sessions overview grouped by moed.

        Each entry in *sections* is a dict:
            {
                "moed":       str,           # "Aleph" | "Bet" | "Gimel"
                "exams":      list[dict],    # exam rows (may be empty)
                "start_date": date | None,
                "end_date":   date | None,
            }
        """
        # ── Detect year from any available exam data ──────────────────────────
        year = QDate.currentDate().year()
        for sec in sections:
            for exam in (sec.get("exams") or []):
                qd = _to_qdate(exam.get("exam_date"))
                if qd.isValid():
                    year = qd.year()
                    break
            if year != QDate.currentDate().year():
                break

        # ── Update header ─────────────────────────────────────────────────────
        self._semester_title.setText(f"{semester} {year}")

        # Compute overall date range across all moeds for the subtitle
        earliest: _date | None = None
        latest:   _date | None = None
        for sec in sections:
            sd, ed = sec.get("start_date"), sec.get("end_date")
            if sd and ed:
                if earliest is None or sd < earliest:
                    earliest = sd
                if latest is None or ed > latest:
                    latest = ed

        if earliest and latest:
            qs = QDate(earliest.year, earliest.month, earliest.day)
            qe = QDate(latest.year,   latest.month,   latest.day)
            self._semester_subtitle.setText(
                f"{EN_LOCALE.toString(qs, 'd MMM yyyy')}"
                f" – {EN_LOCALE.toString(qe, 'd MMM yyyy')}"
            )
        else:
            self._semester_subtitle.setText("All Exam Sessions Overview")

        # ── Rebuild section rows ──────────────────────────────────────────────
        # Clear existing widgets from the vbox (keep final stretch)
        while self._all_sessions_vbox.count() > 1:
            item = self._all_sessions_vbox.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for sec in sections:
            section_widget = self._build_moed_section(
                moed       = sec["moed"],
                semester   = semester,
                year       = year,
                exams      = sec.get("exams") or [],
                start_date = sec.get("start_date"),
                end_date   = sec.get("end_date"),
            )
            # Insert before the trailing stretch
            self._all_sessions_vbox.insertWidget(
                self._all_sessions_vbox.count() - 1, section_widget
            )

        self._stack.setCurrentIndex(_PAGE_ALL_SESSIONS)

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

        # Store period bounds for graying out-of-range days
        self._period_start = start_date
        self._period_end   = end_date

        # Determine months to show
        if start_date is not None and end_date is not None:
            self._months = _months_from_range(start_date, end_date)
        else:
            self._months = self._compute_months_from_exams(semester)

        # Reset to the first month whenever new schedule data is loaded
        self._current_month_idx = 0

        # Determine semester name + year for the header
        sem, year = _detect_semester_and_year(self._exams_by_date)
        sem = semester or sem

        self._update_header(sem, year)
        self._rebuild_month_cards()
        self.show_schedule()
