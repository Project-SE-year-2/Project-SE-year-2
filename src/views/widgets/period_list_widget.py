from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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


@dataclass(frozen=True)
class PeriodItem:
    """View model for one exam period row."""

    period_id: str
    title: str
    start_date: date
    end_date: date


class PeriodFormatter:
    """Formats period dictionaries from IAppService into display-friendly objects."""

    def format(self, period: dict) -> PeriodItem:
        period_id = str(period.get("id", "")).strip()
        semester = str(period.get("semester", "")).strip()
        moed = str(period.get("moed", "")).strip()
        start_date = period["start_date"]
        end_date = period["end_date"]

        title = (
            f"{semester} — {moed} | "
            f"{self._format_date(start_date)} to {self._format_date(end_date)}"
        )

        return PeriodItem(
            period_id=period_id,
            title=title,
            start_date=start_date,
            end_date=end_date,
        )

    # For simplicity, we assume start_date and end_date are date objects. In a real implementation,
    # we might need to handle strings or other formats and add error handling.
    def _format_date(self, value: date) -> str:
        return value.strftime("%d-%m-%Y") if hasattr(value, "strftime") else str(value)


class PeriodRowWidget(QPushButton):
    """Clickable row representing one exam period."""

    def __init__(self, period: PeriodItem, parent=None):
        super().__init__(parent)
        self.period = period
        self._selected = False

        self.setCursor(Qt.PointingHandCursor)
        self.setText(period.title)
        self._apply_style()

    # The caller is responsible for connecting the clicked signal and handling selection state.
    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    # The styles are defined in _apply_style. In a real application, 
    # we might want to use Qt stylesheets or a more robust theming solution.
    def _apply_style(self) -> None:
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


class PeriodListWidget(QWidget):
    """
    Displays available exam periods and emits the selected period id.

    MVP rule:
    The widget talks only to IAppService. It does not import or use engine,
    parser, or model classes directly.
    """

    period_selected = pyqtSignal(str)

    def __init__(
        self,
        service: IAppService,
        formatter: PeriodFormatter | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._service = service
        self._formatter = formatter or PeriodFormatter()
        self._selected_period_id: str | None = None
        self._rows_by_id: dict[str, PeriodRowWidget] = {}

        # The period list should stay hidden until at least one program is selected.
        # InputScreen is responsible for showing this widget and calling refresh()
        # after a valid program selection has been made.
        self._build_ui()

    # The refresh method is public and can be called by the parent screen after program selection.
    def refresh(self) -> None:
        """Reload periods from the service and rebuild the visible rows."""
        periods = self._service.get_periods()
        items = self._to_period_items(periods)
        self._render_periods(items)

    # For testing purposes, we expose the selected period id and a method to clear selection.
    def selected_period_id(self) -> str | None:
        """Return the currently selected period id, if any."""
        return self._selected_period_id

    # This method is not strictly necessary for the widget's functionality, but it allows tests to reset state between cases.
    def clear_selection(self) -> None:
        """Clear the current period selection."""
        self._selected_period_id = None
        self._update_row_states()
 
    def _build_ui(self) -> None:
        self._title_label = QLabel("Exam Periods")
        self._title_label.setStyleSheet(
            f"font-family: {th.FONT_FAMILY}; "
            f"font-weight: {th.FONT_WEIGHT_BOLD}; "
            f"font-size: {th.FONT_SIZE_LG}px;"
        )

        self._hint_label = QLabel("Select an exam period to edit")
        self._hint_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; font-family: {th.FONT_FAMILY};"
        )

        self._empty_label = QLabel("No periods loaded yet.")
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

    # The _to_period_items method converts raw period dictionaries from the service 
    # into PeriodItem objects using the formatter. It also filters out any periods that don't have a valid id.
    def _to_period_items(self, periods: Iterable[dict]) -> list[PeriodItem]:
        items: list[PeriodItem] = []

        for period in periods:
            item = self._formatter.format(period)
            if item.period_id:
                items.append(item)

        return items

    # The _render_periods method takes a list of PeriodItem objects and creates a PeriodRowWidget for each one.
    # It also handles the case where the list is empty by showing a placeholder message.
    def _render_periods(self, periods: list[PeriodItem]) -> None:
        self._clear_rows()
        self._rows_by_id.clear()

        if not periods:
            self._selected_period_id = None
            self._empty_label = QLabel("No exam periods available.")
            self._empty_label.setAlignment(Qt.AlignCenter)
            self._empty_label.setStyleSheet(
                f"color: {th.TEXT_TERTIARY}; "
                f"padding: {th.SPACING_MEDIUM}px; "
                f"font-family: {th.FONT_FAMILY};"
            )
            self._rows_layout.addWidget(self._empty_label)
            self._rows_layout.addStretch()
            return

        valid_ids = {period.period_id for period in periods}
        if self._selected_period_id not in valid_ids:
            self._selected_period_id = None

        for period in periods:
            row = PeriodRowWidget(period)
            row.clicked.connect(
                lambda checked=False, pid=period.period_id: self._on_period_clicked(pid)
            )
            self._rows_by_id[period.period_id] = row
            self._rows_layout.addWidget(row)

        self._rows_layout.addStretch()
        self._update_row_states()

    # The _clear_rows method removes all existing period rows from the layout and deletes them to free resources.
    def _clear_rows(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # The _on_period_clicked method is called when a period row is clicked. 
    # It updates the selected period id, updates the visual state of the rows, and emits the period_selected signal with the new selection.
    def _on_period_clicked(self, period_id: str) -> None:
        self._selected_period_id = period_id
        self._update_row_states()
        self.period_selected.emit(period_id)

    # The _update_row_states method iterates through all the period rows 
    # and updates their selected state based on whether their period id matches the currently selected period id.
    def _update_row_states(self) -> None:
        for period_id, row in self._rows_by_id.items():
            row.set_selected(period_id == self._selected_period_id)
