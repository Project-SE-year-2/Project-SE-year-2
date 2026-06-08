from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QScrollArea,
)

from src.presenter.i_app_service import IAppService
from src.views.widgets.program_list_widget import badge_color_for, abbreviate_name
import src.styles.theme as th

# minimum visible height for the selected-programs scroll area
_CHIPS_SCROLL_MIN_HEIGHT = 100

# badge metrics — must match ProgramRowWidget for visual consistency
_BADGE_SIZE = 28
_BADGE_RADIUS = 4


@dataclass(frozen=True)
class CourseItem:
    """View model for one course row inside a selected program card."""

    number: str
    name: str
    year: int | str
    semester: str
    course_type: str
    evaluation: str


class CourseFormatter:
    """Converts raw course dictionaries from IAppService into CourseItem objects."""

    def format(self, course: dict) -> CourseItem:
        return CourseItem(
            number=str(course.get("number", "")).strip(),
            name=str(course.get("name", "")).strip(),
            year=course.get("year", ""),
            semester=str(course.get("semester", "")).strip(),
            course_type=str(course.get("type", "")).strip(),
            evaluation=str(course.get("evaluation", "")).strip(),
        )


class ProgramChip(QFrame):
    """
    Card row: [colored badge] [program name] [× remove button].
    Matches the reference design — white background, gray border, LTR layout.
    Emits remove_clicked(program_id) when × is pressed.
    """

    remove_clicked = pyqtSignal(str)

    def __init__(self, program_id: str, name: str, parent=None):
        super().__init__(parent)
        self.program_id = program_id

        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {th.BG_CARD};
                border: 1px solid {th.BORDER_LIGHT};
                border-radius: {th.BUTTON_BORDER_RADIUS}px;
            }}
            QFrame:hover {{
                border-color: #CBD5E1;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            th.SPACING_SMALL, th.SPACING_SMALL,
            th.SPACING_SMALL, th.SPACING_SMALL,
        )
        layout.setSpacing(th.SPACING_SMALL)

        abbrev = abbreviate_name(name) or program_id[:2]
        badge = QLabel(abbrev)
        badge.setFixedSize(_BADGE_SIZE, _BADGE_SIZE)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"QLabel {{"
            f" background-color: {th.PRIMARY_LIGHT}; color: {th.PRIMARY_COLOR};"
            f" border-radius: {_BADGE_RADIUS}px;"
            f" font-size: {th.FONT_SIZE_XS}px; font-weight: {th.FONT_WEIGHT_BOLD};"
            f" font-family: {th.FONT_FAMILY};"
            f"}}"
        )

        # Program name — dark, medium weight
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        name_lbl.setStyleSheet(
            f"color: {th.TEXT_PRIMARY}; font-size: {th.FONT_SIZE_MD}px;"
            f" font-weight: {th.FONT_WEIGHT_MEDIUM}; font-family: {th.FONT_FAMILY};"
            f" background: transparent; border: none;"
        )

        # Remove button — muted ×, turns red on hover
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(22, 22)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {th.TEXT_MUTED};
                border: none;
                font-size: {th.FONT_SIZE_LG}px;
                font-weight: {th.FONT_WEIGHT_BOLD};
                font-family: {th.FONT_FAMILY};
                padding: 0px;
            }}
            QPushButton:hover {{ color: {th.DANGER_COLOR}; }}
            """
        )
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.program_id))

        layout.addWidget(badge)
        layout.addWidget(name_lbl, stretch=1)
        layout.addWidget(remove_btn)


class SelectedProgramsPanel(QWidget):
    """Displays the selected programs as chip cards with a remove button."""

    # Emitted when the user clicks × on a chip - carries the removed program id
    program_removed = pyqtSignal(str)

    def __init__(
        self,
        service: IAppService,
        formatter: CourseFormatter | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._service = service
        self._formatter = formatter or CourseFormatter()
        self._courses_cache: dict[str, list[CourseItem]] = {}
        self._cards_by_program_id: dict[str, ProgramChip] = {}

        # InputScreen should call refresh(selected_program_ids) whenever
        # ProgramListWidget emits programs_selected.
        self._build_ui()

    # The refresh method is called with the currently selected program ids,
    # and it rebuilds the display to show a chip for each program
    def refresh(self, program_ids: list[str]) -> None:
        """Rebuild the panel for the currently selected program ids."""
        self._clear_cards()

        if not program_ids:
            self._show_empty_state("No programs selected yet.")
            return

        for program_id in program_ids:
            # Pre-fetch courses into the cache (keeps service call behaviour identical)
            self._get_courses_for_program(program_id)

            name = self._resolve_name(program_id)
            chip = ProgramChip(program_id, name)
            chip.remove_clicked.connect(self.program_removed.emit)
            self._cards_by_program_id[program_id] = chip
            self._cards_layout.addWidget(chip)

        self._cards_layout.addStretch()

    # The clear method removes all program chips from the display
    def clear(self) -> None:
        """Clear the selected programs display without clearing cached courses."""
        self._clear_cards()
        self._show_empty_state("No programs selected yet.")

    # The clear_cache method empties the internal cache of courses
    def clear_cache(self) -> None:
        """Clear cached courses, useful after loading new files."""
        self._courses_cache.clear()

    # The cached_program_ids method returns a list of program ids in the cache
    def cached_program_ids(self) -> list[str]:
        """Return program ids currently stored in the internal course cache."""
        return list(self._courses_cache.keys())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(th.SPACING_SMALL)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("Selected Programs")
        title.setStyleSheet(
            f"color: {th.TEXT_PRIMARY}; "
            f"font-family: {th.FONT_FAMILY}; "
            f"font-size: {th.FONT_SIZE_MD}px; "
            f"font-weight: {th.FONT_WEIGHT_BOLD};"
        )
        header_row.addWidget(title)
        header_row.addStretch()
        layout.addLayout(header_row)

        self._empty_label = QLabel("No programs selected yet.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; "
            f"padding: {th.SPACING_MEDIUM}px; "
            f"font-family: {th.FONT_FAMILY};"
        )

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(th.SPACING_SMALL)
        self._cards_layout.addWidget(self._empty_label)
        self._cards_layout.addStretch()

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setMinimumHeight(_CHIPS_SCROLL_MIN_HEIGHT)
        self._scroll_area.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QScrollBar:vertical {{ width: 6px; background: {th.BG_HOVER}; border-radius: 3px; }}"
            f"QScrollBar::handle:vertical {{ background: #CBD5E1; border-radius: 3px; min-height: 20px; }}"
            f"QScrollBar::add-line:vertical {{ height: 0px; }}"
            f"QScrollBar::sub-line:vertical {{ height: 0px; }}"
        )
        self._scroll_area.setWidget(self._cards_container)

        layout.addWidget(self._scroll_area)

    # Looks up the human-readable program name from the service; falls back to the id.
    # Uses hasattr so the panel stays usable when the service mock omits this method.
    def _resolve_name(self, program_id: str) -> str:
        if not hasattr(self._service, "get_available_programs"):
            return program_id
        for program in self._service.get_available_programs():
            if str(program.get("id", "")) == program_id:
                name = str(program.get("name", "")).strip()
                return name if name else program_id
        return program_id

    # The get_courses_for_program method retrieves the list of CourseItem objects for a given program id,
    # using the internal cache to avoid redundant calls to the service
    def _get_courses_for_program(self, program_id: str) -> list[CourseItem]:
        if program_id not in self._courses_cache:
            raw_courses = self._service.get_courses(program_id)
            self._courses_cache[program_id] = self._to_course_items(raw_courses)
        return self._courses_cache[program_id]

    # The to_course_items method converts a list of raw course dictionaries into CourseItem objects
    def _to_course_items(self, courses: Iterable[dict]) -> list[CourseItem]:
        items: list[CourseItem] = []

        for course in courses:
            item = self._formatter.format(course)
            if item.number:
                items.append(item)

        return items

    # The clear_cards method removes all chips and clears the internal mapping.
    def _clear_cards(self) -> None:
        self._cards_by_program_id.clear()

        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # The show_empty_state method displays a placeholder message
    def _show_empty_state(self, message: str) -> None:
        self._empty_label = QLabel(message)
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; "
            f"padding: {th.SPACING_MEDIUM}px; "
            f"font-family: {th.FONT_FAMILY};"
        )
        self._cards_layout.addWidget(self._empty_label)
        self._cards_layout.addStretch()
