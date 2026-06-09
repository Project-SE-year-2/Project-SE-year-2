from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLayout,
    QFrame,
    QPushButton,
    QSizePolicy,
)


# ── Flow layout (wraps chips to the next line when width runs out) ────────────

class _FlowLayout(QLayout):
    """A layout that arranges items left-to-right and wraps to new lines."""

    def __init__(self, parent=None, h_spacing: int = 6, v_spacing: int = 6):
        super().__init__(parent)
        self._items: list = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

    # ── QLayout interface ─────────────────────────────────────────────────────

    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                      margins.top()  + margins.bottom())
        return size

    # ── Layout logic ──────────────────────────────────────────────────────────

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        x = rect.x() + margins.left()
        y = rect.y() + margins.top()
        line_height = 0
        right_edge  = rect.right() - margins.right()

        for item in self._items:
            w = item.widget()
            hint = item.sizeHint()
            next_x = x + hint.width()
            if next_x > right_edge and line_height > 0:
                x           = rect.x() + margins.left()
                y          += line_height + self._v_spacing
                next_x      = x + hint.width()
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x           = next_x + self._h_spacing
            line_height = max(line_height, hint.height())

        return y + line_height - rect.y() + margins.bottom()

from src.presenter.i_app_service import IAppService
from src.views.widgets.program_list_widget import abbreviate_name
import src.styles.theme as th

_MAX_PROGRAMS = 5
_ABBREV_FALLBACK_LEN = 2

# badge metrics
_BADGE_SIZE   = 24
_BADGE_RADIUS = 4


@dataclass(frozen=True)
class CourseItem:
    """View model for one course row (kept for API compatibility)."""
    number:      str
    name:        str
    year:        int | str
    semester:    str
    course_type: str
    evaluation:  str


class CourseFormatter:
    """Converts raw course dicts → CourseItem (kept for API compatibility)."""

    def format(self, course: dict) -> CourseItem:
        return CourseItem(
            number=str(course.get("number", "")).strip(),
            name=str(course.get("name", "")).strip(),
            year=course.get("year", ""),
            semester=str(course.get("semester", "")).strip(),
            course_type=str(course.get("type", "")).strip(),
            evaluation=str(course.get("evaluation", "")).strip(),
        )


# ── Horizontal chip tag ───────────────────────────────────────────────────────

class _ProgramTag(QWidget):
    """
    Compact horizontal chip: [colored badge] Program Name  [×]
    """

    remove_clicked = pyqtSignal(str)   # emits program_id

    def __init__(self, program_id: str, name: str, parent=None):
        super().__init__(parent)
        self.program_id = program_id
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Chip container style
        self.setStyleSheet(
            f"QWidget {{"
            f"  background-color: #FFFFFF;"
            f"  border: 1px solid #E5E7EB;"
            f"  border-radius: 8px;"
            f"}}"
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(6)

        # Program ID label
        id_lbl = QLabel(program_id)
        id_lbl.setAlignment(Qt.AlignCenter)
        id_lbl.setStyleSheet(
            f"QLabel {{"
            f"  background-color: transparent;"
            f"  color: {th.TEXT_MUTED};"
            f"  border: none;"
            f"  font-size: {th.FONT_SIZE_XS}px;"
            f"  font-weight: {th.FONT_WEIGHT_BOLD};"
            f"  font-family: {th.FONT_FAMILY};"
            f"  padding: 2px 4px;"
            f"}}"
        )

        # Program name
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color: {th.TEXT_PRIMARY};"
            f" font-size: {th.FONT_SIZE_SM}px;"
            f" font-family: {th.FONT_FAMILY};"
            f" background: transparent; border: none;"
        )
        name_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # Remove ×
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; border: none;"
            f"  color: {th.TEXT_MUTED};"
            f"  font-size: {th.FONT_SIZE_MD}px;"
            f"  font-weight: {th.FONT_WEIGHT_BOLD};"
            f"  padding: 0px;"
            f"}}"
            f"QPushButton:hover {{ color: {th.DANGER_COLOR}; }}"
        )
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.program_id))

        row.addWidget(id_lbl)
        row.addWidget(name_lbl)
        row.addWidget(remove_btn)


# ── Panel ─────────────────────────────────────────────────────────────────────

class SelectedProgramsPanel(QWidget):
    """
    Shows selected programs as horizontal chips.
    Header: "Selected Program (X / 5)"
    Body:   one row of compact chip tags.
    """

    program_removed = pyqtSignal(str)

    def __init__(
        self,
        service: IAppService,
        formatter: CourseFormatter | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._service   = service
        self._formatter = formatter or CourseFormatter()
        self._courses_cache:       dict[str, list[CourseItem]] = {}
        self._cards_by_program_id: dict[str, _ProgramTag]      = {}
        self._program_ids:         list[str]                    = []
        self._build_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh(self, program_ids: list[str]) -> None:
        self._program_ids = list(program_ids)
        self._rebuild_chips()

    def clear(self) -> None:
        self._program_ids = []
        self._rebuild_chips()

    def clear_cache(self) -> None:
        self._courses_cache.clear()

    def cached_program_ids(self) -> list[str]:
        return list(self._courses_cache.keys())

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, th.SPACING_SMALL, 0, th.SPACING_SMALL)
        layout.setSpacing(th.SPACING_SMALL)

        # Divider on top
        top_line = QFrame()
        top_line.setFrameShape(QFrame.HLine)
        top_line.setStyleSheet(f"color: {th.BORDER_LIGHT};")
        layout.addWidget(top_line)

        # Title "Selected Program (X / 5)"
        self._title_lbl = QLabel(f"Selected Program (0 / {_MAX_PROGRAMS})")
        self._title_lbl.setStyleSheet(
            f"color: {th.TEXT_PRIMARY};"
            f" font-size: {th.FONT_SIZE_MD}px;"
            f" font-weight: {th.FONT_WEIGHT_BOLD};"
            f" font-family: {th.FONT_FAMILY};"
        )
        layout.addWidget(self._title_lbl)

        # Chips area — uses FlowLayout so chips wrap onto a second line
        self._chips_row = QWidget()
        self._chips_row.setStyleSheet("background: transparent;")
        self._chips_layout = _FlowLayout(
            self._chips_row,
            h_spacing=th.SPACING_SMALL,
            v_spacing=th.SPACING_SMALL,
        )
        self._chips_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._chips_row, stretch=1)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _rebuild_chips(self) -> None:
        # Remove existing chips
        for tag in self._cards_by_program_id.values():
            self._chips_layout.removeWidget(tag)
            tag.deleteLater()
        self._cards_by_program_id.clear()

        # Remove stretch
        while self._chips_layout.count():
            self._chips_layout.takeAt(0)

        count = len(self._program_ids)
        self._title_lbl.setText(f"Selected Program ({count} / {_MAX_PROGRAMS})")

        for pid in self._program_ids:
            # Populate cache (so cached_program_ids() is accurate after refresh)
            self._get_courses_for_program(pid)
            name = self._resolve_name(pid)
            tag  = _ProgramTag(pid, name)
            tag.remove_clicked.connect(self.program_removed.emit)
            self._chips_layout.addWidget(tag)
            self._cards_by_program_id[pid] = tag

    def _resolve_name(self, program_id: str) -> str:
        if not hasattr(self._service, "get_available_programs"):
            return program_id
        for p in self._service.get_available_programs():
            if str(p.get("id", "")) == program_id:
                name = str(p.get("name", "")).strip()
                return name if name else program_id
        return program_id

    def _get_courses_for_program(self, program_id: str) -> list[CourseItem]:
        if program_id not in self._courses_cache:
            raw = self._service.get_courses(program_id)
            self._courses_cache[program_id] = self._to_course_items(raw)
        return self._courses_cache[program_id]

    def _to_course_items(self, courses: Iterable[dict]) -> list[CourseItem]:
        items = []
        for c in courses:
            item = self._formatter.format(c)
            if item.number:
                items.append(item)
        return items
