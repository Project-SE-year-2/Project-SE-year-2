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
from src.styles.study_programs_style import STUDY_PROGRAMS_STYLE

# ── Badge metrics ───────────────────────────────
_BADGE_SIZE = 28
_BADGE_RADIUS = 4
_ABBREV_MAX_LEN = 2
_ROW_MIN_HEIGHT = 48


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
    Clickable row showing a colored badge, program name, course count,
    and an Add / arrow action button.

    Signals:
        clicked        – emitted when the Add/arrow button is pressed
                         (toggles generation selection — backward-compatible).
        view_requested – emitted when the row body is clicked
                         (requests showing courses in the middle panel).
    """

    clicked = pyqtSignal()
    view_requested = pyqtSignal()

    def __init__(self, program: ProgramItem, parent=None):
        super().__init__(parent)
        self.program = program
        self._selected = False   # selected for schedule generation
        self._viewed = False     # currently shown in course table
        # Exact "ID - Name" format preserved for test compatibility
        self._text = f"{program.program_id} - {program.name}"

        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(_ROW_MIN_HEIGHT)
        # Required so QWidget paints its background-color from the stylesheet
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(STUDY_PROGRAMS_STYLE)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            th.SPACING_SMALL, th.SPACING_SMALL,
            th.SPACING_SMALL, th.SPACING_SMALL,
        )
        layout.setSpacing(th.SPACING_SMALL)

        # Name + program_id side by side (name first, then id in muted color)
        self._name_lbl = QLabel(program.name)
        self._name_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._id_lbl = QLabel(program.program_id)
        self._id_lbl.setStyleSheet(
            f"color: {th.TEXT_MUTED}; font-size: {th.FONT_SIZE_XS}px;"
            f" font-family: {th.FONT_FAMILY}; background: transparent;"
        )
        self._id_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Course count label
        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("courseCountLabel")
        self._count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Add / Remove button
        self._action_btn = QPushButton("+ Add")
        self._action_btn.setObjectName("addBtn")
        self._action_btn.setCursor(Qt.PointingHandCursor)
        self._action_btn.setFocusPolicy(Qt.NoFocus)
        self._action_btn.clicked.connect(self._on_action_clicked)

        layout.addWidget(self._name_lbl)
        layout.addWidget(self._id_lbl)
        layout.addStretch()
        layout.addWidget(self._count_lbl)
        layout.addWidget(self._action_btn)

        self._apply_style()

    # ── QPushButton-compatible API used by tests ──────────────────────────────

    def text(self) -> str:
        return self._text

    def click(self) -> None:
        if self.isEnabled():
            self.clicked.emit()

    # ── Public state API ──────────────────────────────────────────────────────

    def set_course_count(self, count: int) -> None:
        self._count_lbl.setText(f"{count} Courses")

    def set_viewed(self, viewed: bool) -> None:
        """Highlight this row as the currently viewed program."""
        self._viewed = viewed
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._action_btn.setObjectName("addBtnSelected" if selected else "addBtn")
        self._action_btn.setText("- Remove" if selected else "+ Add")
        self._action_btn.style().unpolish(self._action_btn)
        self._action_btn.style().polish(self._action_btn)
        self._apply_style()

    def setDisabled(self, disabled: bool) -> None:  # noqa: N802
        super().setDisabled(disabled)
        self._apply_style()

    # ── Mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.view_requested.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        if self.isEnabled() and not self._viewed:
            self.setStyleSheet(
                STUDY_PROGRAMS_STYLE +
                f"QWidget {{ background-color: {th.BG_HOVER};"
                f" border-bottom: 1px solid {th.BORDER_LIGHT}; }}"
            )
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self.isEnabled() and not self._viewed:
            self._apply_normal_style()
        super().leaveEvent(event)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_action_clicked(self) -> None:
        """Add/arrow button clicked → toggle generation selection."""
        self.clicked.emit()

    # ── Styles ────────────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        if not self.isEnabled():
            self._name_lbl.setStyleSheet(
                f"color: {th.DISABLED_TEXT}; font-size: {th.FONT_SIZE_MD}px;"
                f" font-family: {th.FONT_FAMILY}; background: transparent;"
            )
            self.setStyleSheet(
                STUDY_PROGRAMS_STYLE +
                f"QWidget {{ background-color: {th.DISABLED_BG};"
                f" border-bottom: 1px solid {th.BORDER_LIGHT}; }}"
            )
            return

        if self._viewed:
            self._name_lbl.setStyleSheet(
                f"color: {th.PRIMARY_COLOR}; font-size: {th.FONT_SIZE_MD}px;"
                f" font-weight: {th.FONT_WEIGHT_MEDIUM}; font-family: {th.FONT_FAMILY};"
                f" background: transparent;"
            )
            self.setStyleSheet(
                STUDY_PROGRAMS_STYLE +
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
            STUDY_PROGRAMS_STYLE +
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

    programs_selected      = pyqtSignal(list)
    program_view_requested = pyqtSignal(str, str)   # (program_id, program_name)

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
        self._viewed_id: str | None = None

        # The program list should not be shown before the user loads the required files.
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

        # ── Title + subtitle ───────────────────────────────────────────────
        self._title_label = QLabel("Study Programs")
        self._title_label.setObjectName("programsPanelTitle")
        self._title_label.setStyleSheet(
            STUDY_PROGRAMS_STYLE +
            f"QLabel#programsPanelTitle {{ font-family: {th.FONT_FAMILY}; }}"
        )
        layout.addWidget(self._title_label)

        self._subtitle_label = QLabel("Select a study program to view its courses  ·  Add up to 5 programs")
        self._subtitle_label.setObjectName("programsPanelSubtitle")
        self._subtitle_label.setStyleSheet(
            STUDY_PROGRAMS_STYLE +
            f"QLabel#programsPanelSubtitle {{ font-family: {th.FONT_FAMILY}; }}"
        )
        layout.addWidget(self._subtitle_label)

        # ── Search bar + semester filter (same row) ────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(th.SPACING_SMALL)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("programSearchInput")
        self._search_input.setPlaceholderText("Search study programs...")
        self._search_input.setStyleSheet(STUDY_PROGRAMS_STYLE)
        self._search_input.textChanged.connect(self._apply_search_filter)

        search_row.addWidget(self._search_input, stretch=1)
        layout.addLayout(search_row)

        # ── Found-count label ──────────────────────────────────────────────
        self._found_lbl = QLabel("")
        self._found_lbl.setObjectName("programsFoundLabel")
        self._found_lbl.setStyleSheet(
            STUDY_PROGRAMS_STYLE +
            f"QLabel#programsFoundLabel {{ font-family: {th.FONT_FAMILY}; }}"
        )
        layout.addWidget(self._found_lbl)

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
            self._found_lbl.setText("")
            return

        valid_ids = {program.program_id for program in programs}
        self._selected_ids.intersection_update(valid_ids)

        for program in programs:
            row = ProgramRowWidget(program)

            # Fetch course count for this program
            try:
                count = len(self._service.get_courses(program.program_id))
                row.set_course_count(count)
            except Exception:
                pass

            row.clicked.connect(
                lambda checked=False, pid=program.program_id: self._on_program_clicked(pid)
            )
            row.view_requested.connect(
                lambda pid=program.program_id, pname=program.name: self._on_view_requested(pid, pname)
            )
            self._rows_by_id[program.program_id] = row
            self._rows_layout.addWidget(row)

        self._rows_layout.addStretch()
        self._found_lbl.setText(f"{len(programs)} Programs Found")
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

    # Handle row body click: set as viewed and emit view signal
    def _on_view_requested(self, program_id: str, program_name: str) -> None:
        self._viewed_id = program_id
        self._update_row_states()
        self.program_view_requested.emit(program_id, program_name)

    # Update the visual state of all rows based on current selection and max limit
    def _update_row_states(self) -> None:
        reached_limit = len(self._selected_ids) >= self._max_selection

        for program_id, row in self._rows_by_id.items():
            is_selected = program_id in self._selected_ids
            is_viewed   = program_id == self._viewed_id
            row.set_selected(is_selected)
            row.set_viewed(is_viewed)
            row.setDisabled(reached_limit and not is_selected)

    # Show or hide rows based on the current search text.
    def _apply_search_filter(self, text: str) -> None:
        text = text.strip().lower()
        visible_count = 0
        for program_id, row in self._rows_by_id.items():
            if text:
                match = (
                    text in program_id.lower()
                    or text in row.program.name.lower()
                )
                row.setVisible(match)
                if match:
                    visible_count += 1
            else:
                row.setVisible(True)
                visible_count += 1
        total = len(self._rows_by_id)
        if text:
            self._found_lbl.setText(f"{visible_count} of {total} Programs Found")
        else:
            self._found_lbl.setText(f"{total} Programs Found")
