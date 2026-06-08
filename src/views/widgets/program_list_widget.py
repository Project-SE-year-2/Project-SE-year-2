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
    QHBoxLayout,
    QLineEdit,
)

from src.presenter.i_app_service import IAppService
import src.styles.theme as th

# ── Badge metrics ───────────────
_BADGE_SIZE = 28      
_BADGE_RADIUS = 4
_ABBREV_MAX_LEN = 2
_ROW_MIN_HEIGHT = 42


def badge_color_for(program_id: str) -> str:
    """Deterministically pick a badge color from the theme palette."""
    return th.PROGRAM_BADGE_COLORS[hash(program_id) % len(th.PROGRAM_BADGE_COLORS)]


def abbreviate_name(name: str) -> str:
    """Return up-to-2-letter abbreviation from first letters of each word."""
    return "".join(w[0].upper() for w in name.split() if w)[:_ABBREV_MAX_LEN]


@dataclass(frozen=True)
class ProgramItem:
    """View model for one program row."""

    program_id: str
    name: str


class ProgramRowWidget(QWidget):
    """
    Clickable row showing a colored badge and program name.
    Exposes .text() and .click() for test compatibility.
    """

    clicked = pyqtSignal()

    def __init__(self, program: ProgramItem, parent=None):
        super().__init__(parent)
        self.program = program
        self._selected = False
        # Exact "ID - Name" format preserved for test compatibility
        self._text = f"{program.program_id} - {program.name}"

        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(_ROW_MIN_HEIGHT)
        # Required so QWidget paints its background-color from the stylesheet
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            th.SPACING_SMALL, th.SPACING_SMALL,
            th.SPACING_MEDIUM, th.SPACING_SMALL,
        )
        layout.setSpacing(th.SPACING_SMALL)

        abbrev = abbreviate_name(program.name) or program.program_id[:_ABBREV_MAX_LEN]
        self._badge = QLabel(abbrev)
        self._badge.setFixedSize(_BADGE_SIZE, _BADGE_SIZE)
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setStyleSheet(
            f"QLabel {{"
            f" background-color: {th.PRIMARY_LIGHT}; color: {th.PRIMARY_COLOR};"
            f" border-radius: {_BADGE_RADIUS}px;"
            f" font-size: {th.FONT_SIZE_XS}px; font-weight: {th.FONT_WEIGHT_BOLD};"
            f" font-family: {th.FONT_FAMILY};"
            f"}}"
        )

        self._name_lbl = QLabel(program.name)
        self._name_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(self._badge)
        layout.addWidget(self._name_lbl, stretch=1)

        self._apply_style()

    # ── QPushButton-compatible API used by tests ──────────────────────────────

    def text(self) -> str:
        return self._text

    def click(self) -> None:
        if self.isEnabled():
            self.clicked.emit()

    # ── Public state API ──────────────────────────────────────────────────────

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    def setDisabled(self, disabled: bool) -> None:  # noqa: N802
        super().setDisabled(disabled)
        self._apply_style()

    # ── Mouse events for hover highlight ─────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        if self.isEnabled() and not self._selected:
            self.setStyleSheet(
                f"QWidget {{ background-color: {th.BG_HOVER};"
                f" border-bottom: 1px solid {th.BORDER_LIGHT}; }}"
            )
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self.isEnabled() and not self._selected:
            self._apply_normal_style()
        super().leaveEvent(event)

    # ── Styles ────────────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        if not self.isEnabled():
            self._name_lbl.setStyleSheet(
                f"color: {th.DISABLED_TEXT}; font-size: {th.FONT_SIZE_MD}px;"
                f" font-family: {th.FONT_FAMILY}; background: transparent;"
            )
            self.setStyleSheet(
                f"QWidget {{ background-color: {th.DISABLED_BG};"
                f" border-bottom: 1px solid {th.BORDER_LIGHT}; }}"
            )
            return

        if self._selected:
            self._name_lbl.setStyleSheet(
                f"color: {th.TEXT_PRIMARY}; font-size: {th.FONT_SIZE_MD}px;"
                f" font-weight: {th.FONT_WEIGHT_MEDIUM}; font-family: {th.FONT_FAMILY};"
                f" background: transparent;"
            )
            self.setStyleSheet(
                f"QWidget {{ background-color: {th.PRIMARY_SOFT};"
                f" border-bottom: 1px solid {th.BORDER_LIGHT}; }}"
            )
            return

        self._apply_normal_style()

    def _apply_normal_style(self) -> None:
        self._name_lbl.setStyleSheet(
            f"color: {th.TEXT_SECONDARY}; font-size: {th.FONT_SIZE_MD}px;"
            f" font-family: {th.FONT_FAMILY}; background: transparent;"
        )
        self.setStyleSheet(
            f"QWidget {{ background-color: {th.BG_CARD};"
            f" border-bottom: 1px solid {th.BORDER_LIGHT}; }}"
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

    def remove_selection(self, program_id: str) -> None:
        """Deselect a single program by id and emit programs_selected."""
        if program_id in self._selected_ids:
            self._selected_ids.discard(program_id)
            selected = self.selected_programs()
            self._service.select_programs(selected)
            self._update_row_states()
            self.programs_selected.emit(selected)

    # Private methods

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(th.SPACING_SMALL)

        # Header row
        header_row = QHBoxLayout()
        self._title_label = QLabel("Programs")
        self._title_label.setStyleSheet(
            f"font-family: {th.FONT_FAMILY}; "
            f"font-weight: {th.FONT_WEIGHT_BOLD}; "
            f"font-size: {th.FONT_SIZE_LG}px;"
            f"color: {th.TEXT_PRIMARY};"
        )
        self._hint_label = QLabel(f"Select up to {self._max_selection}")
        self._hint_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; font-family: {th.FONT_FAMILY};"
            f"font-size: {th.FONT_SIZE_SM}px;"
        )
        header_row.addWidget(self._title_label)
        header_row.addStretch()
        header_row.addWidget(self._hint_label)
        layout.addLayout(header_row)

        # Search bar
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search and select programs")
        self._search_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {th.BG_CARD};
                border: 1px solid {th.BORDER_LIGHT};
                border-radius: {th.BUTTON_BORDER_RADIUS}px;
                padding: {th.SPACING_SMALL}px {th.SPACING_MEDIUM}px;
                font-family: {th.FONT_FAMILY};
                font-size: {th.FONT_SIZE_SM}px;
                color: {th.TEXT_PRIMARY};
                min-height: {th.BUTTON_MIN_HEIGHT_SM}px;
            }}
            QLineEdit:focus {{
                border-color: {th.PRIMARY_COLOR};
            }}
            QLineEdit::placeholder {{
                color: {th.TEXT_MUTED};
            }}
            """
        )
        self._search_input.textChanged.connect(self._apply_search_filter)
        layout.addWidget(self._search_input)

        self._empty_label = QLabel("No programs loaded yet.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; "
            f"padding: {th.SPACING_MEDIUM}px; "
            f"font-family: {th.FONT_FAMILY};"
        )

        # Rows sit in a white container so the list background is clean
        self._rows_container = QWidget()
        self._rows_container.setStyleSheet(
            f"QWidget {{ background-color: {th.BG_CARD}; }}"
        )
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._rows_layout.addWidget(self._empty_label)
        self._rows_layout.addStretch()

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setStyleSheet(
            f"QScrollArea {{ background: transparent;"
            f" border: 1px solid {th.BORDER_LIGHT};"
            f" border-radius: {th.BUTTON_BORDER_RADIUS}px; }}"
            f"QScrollBar:vertical {{ width: 6px; background: {th.BG_HOVER}; border-radius: 3px; }}"
            f"QScrollBar::handle:vertical {{ background: #CBD5E1; border-radius: 3px; min-height: 20px; }}"
            f"QScrollBar::add-line:vertical {{ height: 0px; }}"
            f"QScrollBar::sub-line:vertical {{ height: 0px; }}"
        )
        self._scroll_area.setWidget(self._rows_container)

        layout.addWidget(self._scroll_area, stretch=1)

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

    # Show or hide rows based on the current search text.
    def _apply_search_filter(self, text: str) -> None:
        text = text.strip().lower()
        for program_id, row in self._rows_by_id.items():
            if text:
                match = (
                    text in program_id.lower()
                    or text in row.program.name.lower()
                )
                row.setVisible(match)
            else:
                row.setVisible(True)