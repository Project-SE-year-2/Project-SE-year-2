from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QScrollArea,
    QFrame,
)

from src.presenter.i_app_service import IAppService
import src.styles.theme as th


# This file contains the ProgramListWidget and related classes.
@dataclass(frozen=True)
class ProgramItem:
    """View model for one program row."""

    program_id: str
    name: str


class ProgramRowWidget(QPushButton):
    """Clickable row representing a single academic program."""

    def __init__(self, program: ProgramItem, parent=None):
        super().__init__(parent)
        self.program = program
        self._selected = False

        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setText(f"{program.program_id} - {program.name}")
        self._apply_style()

    # Override setChecked to keep _selected in sync
    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setChecked(selected)
        self._apply_style()

    # Override setDisabled to update style when disabled
    def setDisabled(self, disabled: bool) -> None:  # noqa: N802 - Qt naming convention
        super().setDisabled(disabled)
        self._apply_style()

    # Apply styles based on selected and disabled state
    def _apply_style(self) -> None:
        if not self.isEnabled():
            self.setStyleSheet(
                f"""
                QPushButton {{
                    text-align: left;
                    padding: {th.SPACING_SMALL}px;
                    border-radius: {th.BADGE_RADIUS}px;
                    background-color: {th.DISABLED_BG};
                    color: {th.DISABLED_TEXT};
                    border: 1px solid {th.DISABLED_BORDER};
                    font-family: {th.FONT_FAMILY};
                }}
                """
            )
            return

        if self._selected:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    text-align: left;
                    padding: {th.SPACING_SMALL}px;
                    border-radius: {th.BADGE_RADIUS}px;
                    background-color: {th.PRIMARY_COLOR};
                    color: {th.TEXT_PRIMARY};
                    border: 1px solid {th.SPINNER_COLOR};
                    font-family: {th.FONT_FAMILY};
                    font-weight: {th.FONT_WEIGHT_BOLD};
                }}
                """
            )
            return

        self.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left;
                padding: {th.SPACING_SMALL}px;
                border-radius: {th.BADGE_RADIUS}px;
                background-color: {th.BG_DARK_SECONDARY};
                color: {th.TEXT_SECONDARY};
                border: 1px solid {th.BORDER_LIGHT};
                font-family: {th.FONT_FAMILY};
            }}
            QPushButton:hover {{
                background-color: {th.BG_DARK_TERTIARY};
                border: 1px solid {th.SPINNER_COLOR};
            }}
            """
        )


class ProgramListWidget(QWidget):
    """
    Displays all available programs and lets the user select up to max_selection.

    MVP rule:
    The widget talks only to IAppService. It does not import or use engine,
    parser, or model classes directly.
    """

    programs_selected = pyqtSignal(list)

    def __init__(
        self,
        service: IAppService,
        max_selection: int = 5,
        parent=None,
    ):
        super().__init__(parent)

        self._service = service
        self._max_selection = max_selection
        self._selected_ids: set[str] = set()
        self._rows_by_id: dict[str, ProgramRowWidget] = {}

        # The program list should not be shown before the user loads the required files.
        # InputScreen is responsible for displaying this widget and refreshing its data
        # once the file loading process has completed successfully.
        self._build_ui()

    # Public API
    def refresh(self) -> None:
        """Reload programs from the service and rebuild the visible rows."""
        programs = self._service.get_available_programs()
        items = self._to_program_items(programs)
        self._render_programs(items)
    
    def selected_programs(self) -> list[str]:
        """Return selected program ids in display order."""
        return [
            program_id
            for program_id in self._rows_by_id
            if program_id in self._selected_ids
        ]

    def clear_selection(self) -> None:
        """Clear all selected programs and notify the service."""
        self._selected_ids.clear()
        self._service.select_programs([])
        self._update_row_states()
        self.programs_selected.emit([])

    # Private methods
    def _build_ui(self) -> None:
        self._title_label = QLabel("Programs")
        self._title_label.setStyleSheet(
            f"font-family: {th.FONT_FAMILY}; "
            f"font-weight: {th.FONT_WEIGHT_BOLD}; "
            f"font-size: {th.FONT_SIZE_LG}px;"
        )

        self._hint_label = QLabel(f"Select up to {self._max_selection} programs")
        self._hint_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; font-family: {th.FONT_FAMILY};"
        )

        self._empty_label = QLabel("No programs loaded yet.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; "
            f"padding: {th.SPACING_MEDIUM}px; "
            f"font-family: {th.FONT_FAMILY};"
        )

        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(8)
        self._rows_layout.addWidget(self._empty_label)
        self._rows_layout.addStretch()

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setWidget(self._rows_container)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addWidget(self._hint_label)
        layout.addWidget(self._scroll_area)

    # Convert raw program dicts from the service into ProgramItem view models
    def _to_program_items(self, programs: Iterable[dict]) -> list[ProgramItem]:
        items: list[ProgramItem] = []

        for program in programs:
            program_id = str(program.get("id", "")).strip()
            name = str(program.get("name", program_id)).strip() or program_id

            if program_id:
                items.append(ProgramItem(program_id=program_id, name=name))

        return items

    # Render the list of ProgramItems as clickable rows in the UI
    def _render_programs(self, programs: list[ProgramItem]) -> None:
        self._clear_rows()
        self._rows_by_id.clear()

        if not programs:
            self._empty_label = QLabel("No programs available.")
            self._empty_label.setAlignment(Qt.AlignCenter)
            self._empty_label.setStyleSheet(
                f"color: {th.TEXT_TERTIARY}; "
                f"padding: {th.SPACING_MEDIUM}px; "
                f"font-family: {th.FONT_FAMILY};"
            )
            self._rows_layout.addWidget(self._empty_label)
            self._rows_layout.addStretch()
            return

        valid_ids = {program.program_id for program in programs}
        self._selected_ids.intersection_update(valid_ids)

        for program in programs:
            row = ProgramRowWidget(program)
            row.clicked.connect(
                lambda checked=False, pid=program.program_id: self._on_program_clicked(pid)
            )
            self._rows_by_id[program.program_id] = row
            self._rows_layout.addWidget(row)

        self._rows_layout.addStretch()
        self._update_row_states()

    # Remove all program rows from the UI
    def _clear_rows(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # Handle clicks on program rows: toggle selection, notify service, and emit signal
    def _on_program_clicked(self, program_id: str) -> None:
        if program_id in self._selected_ids:
            self._selected_ids.remove(program_id)
        elif len(self._selected_ids) < self._max_selection:
            self._selected_ids.add(program_id)

        selected = self.selected_programs()
        self._service.select_programs(selected)
        self._update_row_states()
        self.programs_selected.emit(selected)

    # Update the visual state of all rows based on current selection and max limit
    def _update_row_states(self) -> None:
        reached_limit = len(self._selected_ids) >= self._max_selection

        for program_id, row in self._rows_by_id.items():
            is_selected = program_id in self._selected_ids
            row.set_selected(is_selected)
            row.setDisabled(reached_limit and not is_selected)
