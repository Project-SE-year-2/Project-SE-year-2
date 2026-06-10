from __future__ import annotations

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy,
)

import src.styles.theme as th
from src.styles.study_programs_style import STUDY_PROGRAMS_STYLE
from src.presenter.i_app_service import IAppService
from src.styles.icons import load_pixmap, ICON_CALENDAR

_ROWS_PER_PAGE = 10

# Column indices
_COL_NUM      = 0
_COL_CODE     = 1
_COL_NAME     = 2
_COL_YEAR     = 3
_COL_SEMESTER = 4
_COL_EXAM     = 5   # evaluation field
_COL_TYPE     = 6   # badge, no header text

_HEADERS = ["#", "Course Code", "Course Name", "Year", "Semester", "Evaluation", ""]

_TYPE_BADGE_OBJ = {
    "obligatory": "typeBadgeObligatory",
    "elective":   "typeBadgeElective",
}


class CourseTableWidget(QWidget):
    """
    Right column of the Study Programs tab.
    Shows a paginated table of courses for the selected program.

    Columns: #, Course Code, Course Name, Year, Semester, Exam (evaluation), [type badge]

    The semester filter is driven externally via set_semester_filter().
    """

    course_selected = pyqtSignal(dict)

    def __init__(self, service: IAppService, parent=None):
        super().__init__(parent)
        self._service           = service
        self._all_courses: list[dict] = []
        self._filtered:    list[dict] = []
        self._program_name  = ""
        self._current_page  = 0
        self._semester_filter = "All Semesters"
        self.setStyleSheet(STUDY_PROGRAMS_STYLE)
        self._build_ui()
        self._show_empty()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_program(self, program_id: str, program_name: str) -> None:
        """Fetch and display courses for the given program."""
        self._program_name = program_name
        self._all_courses  = self._service.get_courses(program_id)
        self._current_page = 0
        self._apply_filter()

    def set_semester_filter(self, value: str) -> None:
        """Called by the left panel when the 'All Semesters' combo changes."""
        self._semester_filter = value
        self._current_page = 0
        self._apply_filter()

    def clear(self) -> None:
        self._all_courses = []
        self._filtered    = []
        self._program_name = ""
        self._current_page = 0
        self._show_empty()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(th.SPACING_SMALL)

        # ── Header row ─────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(th.SPACING_SMALL)

        title_block = QWidget()
        title_block.setStyleSheet("background: transparent;")
        tb_l = QVBoxLayout(title_block)
        tb_l.setContentsMargins(0, 0, 0, 0)
        tb_l.setSpacing(2)

        self._title_lbl = QLabel("")
        self._title_lbl.setObjectName("coursesTableTitle")

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("coursesFoundLabel")

        tb_l.addWidget(self._title_lbl)
        tb_l.addWidget(self._count_lbl)

        hdr.addWidget(title_block)
        hdr.addStretch()
        layout.addLayout(hdr)

        # ── Table ──────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setObjectName("coursesTable")
        self._table.setColumnCount(len(_HEADERS))
        self._table.setHorizontalHeaderLabels(_HEADERS)

        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(_COL_NUM,      QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(_COL_CODE,     QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(_COL_NAME,     QHeaderView.Stretch)
        hh.setSectionResizeMode(_COL_YEAR,     QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(_COL_SEMESTER, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(_COL_EXAM,     QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(_COL_TYPE,     QHeaderView.ResizeToContents)

        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setShowGrid(False)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.setAlternatingRowColors(False)
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._table.cellClicked.connect(self._on_row_clicked)
        layout.addWidget(self._table, stretch=1)

        # ── Pagination bar ─────────────────────────────────────────────────
        self._pag_w = QWidget()
        self._pag_w.setStyleSheet("background: transparent;")
        self._pag_l = QHBoxLayout(self._pag_w)
        self._pag_l.setContentsMargins(0, th.SPACING_SMALL, 0, 0)
        self._pag_l.setSpacing(4)

        self._prev_btn = QPushButton("‹")
        self._prev_btn.setObjectName("pageNavBtn")
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.clicked.connect(self._go_prev)

        self._next_btn = QPushButton("›")
        self._next_btn.setObjectName("pageNavBtn")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(self._go_next)

        self._info_lbl = QLabel("")
        self._info_lbl.setObjectName("paginationInfoLabel")

        self._page_btns: list[QPushButton] = []
        layout.addWidget(self._pag_w)

        # ── Empty-state ────────────────────────────────────────────────────
        self._empty_w = QWidget()
        self._empty_w.setStyleSheet("background: transparent;")
        el = QVBoxLayout(self._empty_w)
        el.setAlignment(Qt.AlignCenter)
        el.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(load_pixmap(ICON_CALENDAR, size=56))
        icon_lbl.setStyleSheet("background: transparent;")

        lbl = QLabel("Select a program to view its courses")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"color: {th.TEXT_MUTED}; font-size: 28px;"
            f" font-family: {th.FONT_FAMILY};"
        )

        el.addWidget(icon_lbl)
        el.addWidget(lbl)
        layout.addWidget(self._empty_w, stretch=1)

    # ── Filter ────────────────────────────────────────────────────────────────

    def _apply_filter(self) -> None:
        if self._semester_filter == "All Semesters":
            self._filtered = list(self._all_courses)
        else:
            self._filtered = [
                c for c in self._all_courses
                if str(c.get("semester", "")) == self._semester_filter
            ]
        self._render_page()

    # ── Render ────────────────────────────────────────────────────────────────

    def _show_empty(self) -> None:
        self._table.setVisible(False)
        self._pag_w.setVisible(False)
        self._empty_w.setVisible(True)
        self._title_lbl.setText("")
        self._count_lbl.setText("")

    def _render_page(self) -> None:
        total = len(self._filtered)

        if not self._program_name:
            self._show_empty()
            return

        self._empty_w.setVisible(False)
        self._table.setVisible(True)
        self._pag_w.setVisible(True)
        self._title_lbl.setText(f"Courses in {self._program_name}")
        self._count_lbl.setText(f"{total} courses found")

        total_pages = max(1, (total + _ROWS_PER_PAGE - 1) // _ROWS_PER_PAGE)
        self._current_page = max(0, min(self._current_page, total_pages - 1))

        start = self._current_page * _ROWS_PER_PAGE
        end   = min(start + _ROWS_PER_PAGE, total)
        page  = self._filtered[start:end]

        self._table.setRowCount(len(page))

        for i, course in enumerate(page):
            self._table.setRowHeight(i, 56)

            def _item(text: str, align=Qt.AlignLeft | Qt.AlignVCenter,
                      color: str = "#111827") -> QTableWidgetItem:
                it = QTableWidgetItem(text)
                it.setTextAlignment(align)
                it.setForeground(QColor(color))
                return it

            # # — row number
            self._table.setItem(i, _COL_NUM,
                _item(str(start + i + 1), Qt.AlignCenter, "#111827"))

            # Course Code
            self._table.setItem(i, _COL_CODE,
                _item(str(course.get("number", "")), Qt.AlignLeft | Qt.AlignVCenter, "#111827"))

            # Course Name — explicit left alignment so text sits under the header
            name_item = QTableWidgetItem(str(course.get("name", "")))
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            name_item.setForeground(QColor("#111827"))
            self._table.setItem(i, _COL_NAME, name_item)

            # Year
            self._table.setItem(i, _COL_YEAR,
                _item(str(course.get("year", "")), Qt.AlignCenter, "#111827"))

            # Semester
            self._table.setItem(i, _COL_SEMESTER,
                _item(str(course.get("semester", "")), Qt.AlignCenter, "#111827"))

            # Exam (evaluation field)
            self._table.setItem(i, _COL_EXAM,
                _item(str(course.get("evaluation", "")), Qt.AlignCenter, "#111827"))

            # Type badge widget
            type_str  = str(course.get("type", ""))
            badge_key = type_str.lower()
            badge     = QLabel(type_str)
            badge.setObjectName(_TYPE_BADGE_OBJ.get(badge_key, "typeBadgeElective"))
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(self.styleSheet())   # inherit sheet
            cell_w = QWidget()
            cell_w.setStyleSheet("background: transparent;")
            cl = QHBoxLayout(cell_w)
            cl.setContentsMargins(6, 2, 6, 2)
            cl.addWidget(badge)
            cl.setAlignment(Qt.AlignCenter)
            self._table.setCellWidget(i, _COL_TYPE, cell_w)

        self._rebuild_pagination(total_pages, start + 1, end, total)

    def _rebuild_pagination(
        self, total_pages: int, s: int, e: int, total: int
    ) -> None:
        # Clear layout
        while self._pag_l.count():
            self._pag_l.takeAt(0)
        for btn in self._page_btns:
            btn.deleteLater()
        self._page_btns.clear()

        self._pag_l.addWidget(self._prev_btn)

        for p in range(total_pages):
            btn = QPushButton(str(p + 1))
            btn.setObjectName(
                "pageNumBtnActive" if p == self._current_page else "pageNumBtn"
            )
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(32, 32)
            btn.clicked.connect(lambda _, pg=p: self._go_to_page(pg))
            self._pag_l.addWidget(btn)
            self._page_btns.append(btn)

        self._pag_l.addWidget(self._next_btn)
        self._pag_l.addStretch()
        self._info_lbl.setText(f"Showing {s} to {e} of {total}")
        self._info_lbl.hide()

        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled(self._current_page < total_pages - 1)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_prev(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._render_page()

    def _go_next(self) -> None:
        pages = max(1, (len(self._filtered) + _ROWS_PER_PAGE - 1) // _ROWS_PER_PAGE)
        if self._current_page < pages - 1:
            self._current_page += 1
            self._render_page()

    def _go_to_page(self, page: int) -> None:
        self._current_page = page
        self._render_page()

    # ── Row click ─────────────────────────────────────────────────────────────

    def _on_row_clicked(self, row: int, _col: int) -> None:
        idx = self._current_page * _ROWS_PER_PAGE + row
        if 0 <= idx < len(self._filtered):
            self.course_selected.emit(self._filtered[idx])
