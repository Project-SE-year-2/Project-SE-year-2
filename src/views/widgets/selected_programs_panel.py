from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QScrollArea,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from src.presenter.i_app_service import IAppService
from src.views.shared_components.type_badge import TypeBadge
import src.styles.theme as th


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


class SelectedProgramCard(QFrame):
    """Displays one selected program and its courses."""

    HEADERS = ["Number", "Name", "Year", "Semester", "Type", "Evaluation"]

    def __init__(self, program_id: str, courses: list[CourseItem], parent=None):
        super().__init__(parent)
        self.program_id = program_id
        self._courses = courses

        self.setObjectName("selectedProgramCard")
        self._build_ui()

    # The UI is built with a title and a table of courses, styled according to the theme.
    def _build_ui(self) -> None:
        self.setStyleSheet(
            f'''
            QFrame#selectedProgramCard {{
                background-color: {th.BG_DARK_SECONDARY};
                border: 1px solid {th.BORDER_LIGHTER};
                border-radius: {th.BUTTON_BORDER_RADIUS}px;
            }}
            '''
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            th.SPACING_LARGE,
            th.SPACING_LARGE,
            th.SPACING_LARGE,
            th.SPACING_LARGE,
        )
        layout.setSpacing(th.SPACING_MEDIUM)

        title = QLabel(f"Program {self.program_id}")
        title.setStyleSheet(
            f"color: {th.TEXT_PRIMARY}; "
            f"font-family: {th.FONT_FAMILY}; "
            f"font-size: {th.FONT_SIZE_LG}px; "
            f"font-weight: {th.FONT_WEIGHT_BOLD};"
        )
        layout.addWidget(title)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.setRowCount(len(self._courses))
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.setAlternatingRowColors(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self._apply_table_style()
        self._populate_table()

        layout.addWidget(self._table)

    # The table is styled to match the application's dark theme, 
    # with specific colors for background, text, and borders.
    def _apply_table_style(self) -> None:
        self._table.setStyleSheet(
            f'''
            QTableWidget {{
                background-color: {th.BG_DARK_SECONDARY};
                color: {th.TEXT_SECONDARY};
                gridline-color: {th.BORDER_LIGHTER};
                border: 1px solid {th.BORDER_LIGHTER};
                border-radius: {th.BUTTON_BORDER_RADIUS}px;
                font-family: {th.FONT_FAMILY};
                font-size: {th.FONT_SIZE_MD}px;
            }}
            QHeaderView::section {{
                background-color: {th.BG_DARK_TERTIARY};
                color: {th.TEXT_TERTIARY};
                font-family: {th.FONT_FAMILY};
                font-weight: {th.FONT_WEIGHT_BOLD};
                padding: {th.SPACING_SMALL}px;
                border: none;
                border-bottom: 1px solid {th.BORDER_LIGHT};
            }}
            QTableWidget::item {{
                padding: {th.SPACING_SMALL}px;
            }}
            '''
        )

    # The course data is populated into the table, 
    # with the "Type" column using a custom TypeBadge widget for visual distinction.
    def _populate_table(self) -> None:
        for row_index, course in enumerate(self._courses):
            values = [
                course.number,
                course.name,
                str(course.year),
                course.semester,
                course.course_type,
                course.evaluation,
            ]

            for column_index, value in enumerate(values):
                if self.HEADERS[column_index] == "Type":
                    self._table.setCellWidget(row_index, column_index, TypeBadge(value))
                else:
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(Qt.AlignCenter)
                    self._table.setItem(row_index, column_index, item)


class SelectedProgramsPanel(QWidget):
    """Displays the selected programs and their courses."""

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
        self._cards_by_program_id: dict[str, SelectedProgramCard] = {}

        # InputScreen should call refresh(selected_program_ids) whenever
        # ProgramListWidget emits programs_selected.
        self._build_ui()

    # The refresh method is called with the currently selected program ids,
    # and it rebuilds the display to show the corresponding courses for each program.
    def refresh(self, program_ids: list[str]) -> None:
        """Rebuild the panel for the currently selected program ids."""
        self._clear_cards()

        if not program_ids:
            self._show_empty_state("No programs selected yet.")
            return

        for program_id in program_ids:
            courses = self._get_courses_for_program(program_id)
            card = SelectedProgramCard(program_id, courses)
            self._cards_by_program_id[program_id] = card
            self._cards_layout.addWidget(card)

        self._cards_layout.addStretch()
        self._empty_label.setVisible(False)

    # The clear method removes all program cards from the display but keeps the cached courses intact,
    # allowing for quick refresh if the same programs are selected again.
    def clear(self) -> None:
        """Clear the selected programs display without clearing cached courses."""
        self._clear_cards()
        self._show_empty_state("No programs selected yet.")

    # The clear_cache method empties the internal cache of courses, which can be useful when new files are loaded,
    # ensuring that the next refresh will fetch fresh data from the service.
    def clear_cache(self) -> None:
        """Clear cached courses, useful after loading new files."""
        self._courses_cache.clear()

    # The cached_program_ids method returns a list of program ids that currently have their courses stored in the internal cache,
    # which can be used for debugging or optimization purposes.
    def cached_program_ids(self) -> list[str]:
        """Return program ids currently stored in the internal course cache."""
        return list(self._courses_cache.keys())

    # The UI is built with a title and a table of courses, styled according to the theme.
    def _build_ui(self) -> None:
        title = QLabel("Selected Programs")
        title.setStyleSheet(
            f"color: {th.TEXT_PRIMARY}; "
            f"font-family: {th.FONT_FAMILY}; "
            f"font-size: {th.FONT_SIZE_LG}px; "
            f"font-weight: {th.FONT_WEIGHT_BOLD};"
        )

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
        self._cards_layout.setSpacing(th.SPACING_MEDIUM)
        self._cards_layout.addWidget(self._empty_label)
        self._cards_layout.addStretch()

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setWidget(self._cards_container)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self._scroll_area)

    # The get_courses_for_program method retrieves the list of CourseItem objects for a given program id,
    # using the internal cache to avoid redundant calls to the service, and converting raw course data
    # into CourseItem objects using the formatter.
    def _get_courses_for_program(self, program_id: str) -> list[CourseItem]:
        if program_id not in self._courses_cache:
            raw_courses = self._service.get_courses(program_id)
            self._courses_cache[program_id] = self._to_course_items(raw_courses)
        return self._courses_cache[program_id]

    # The to_course_items method converts a list of raw course dictionaries into a list of CourseItem objects,
    # using the CourseFormatter to extract and format the relevant fields for display in the table.
    def _to_course_items(self, courses: Iterable[dict]) -> list[CourseItem]:
        items: list[CourseItem] = []

        for course in courses:
            item = self._formatter.format(course)
            if item.number:
                items.append(item)

        return items

    # The clear_cards method removes all program cards from the display and clears the internal mapping of program ids to cards,
    # but it does not clear the cached courses, allowing for quick refresh if the same programs are selected again.
    def _clear_cards(self) -> None:
        self._cards_by_program_id.clear()

        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # The show_empty_state method displays a message in the center of the panel when no programs are selected,
    # providing feedback to the user about the current state of the selection.
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
