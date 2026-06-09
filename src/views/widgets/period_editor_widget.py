from __future__ import annotations

from copy import error
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.models.enums import CalendarMode
from src.presenter.i_app_service import IAppService
from src.views.shared_components.calendar_table_widget import CalendarTableWidget
import src.styles.theme as th


@dataclass(frozen=True)
class EditablePeriod:
    """View model for one editable exam period."""

    period_id: str
    title: str
    start_date: date
    end_date: date
    forbidden_days: tuple[date, ...]


class EditablePeriodFormatter:
    """Converts raw period dictionaries from IAppService into EditablePeriod objects."""

    # Converts one raw period dictionary into an EditablePeriod view model.
    def format(self, period: dict) -> EditablePeriod:
        period_id = str(period.get("id", "")).strip()
        semester = str(period.get("semester", "")).strip()
        moed = str(period.get("moed", "")).strip()
        start_date = period["start_date"]
        end_date = period["end_date"]
        forbidden_days = tuple(period.get("forbidden_days", []) or [])

        return EditablePeriod(
            period_id=period_id,
            title=f"{semester} — {moed}",
            start_date=start_date,
            end_date=end_date,
            forbidden_days=forbidden_days,
        )


class PeriodEditorWidget(QWidget):
    """
    Edits one selected exam period.

    The widget communicates only with IAppService.
    It does not import parsers, algorithm classes, or datastore classes directly.
    """

    # Initializes the editor, stores dependencies, and builds the UI.
    def __init__(
        self,
        service: IAppService,
        formatter: EditablePeriodFormatter | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._service = service
        self._formatter = formatter or EditablePeriodFormatter()
        self._current_period_id: str | None = None
        self._periods_by_id: dict[str, EditablePeriod] = {}
        self._is_loading_period = False

        self._build_ui()
        self._connect_signals()

    # Loads a selected period by id and renders it inside the editor.
    def load_period(self, period_id: str) -> None:
        self._refresh_periods_cache()

        if period_id not in self._periods_by_id:
            self._current_period_id = None
            self._show_message(f"Error: Period '{period_id}' was not found.")
            return

        self._current_period_id = period_id
        self._render_period(self._periods_by_id[period_id])

    # Clears the editor and resets it to the initial no-selection state.
    def clear(self) -> None:
        self._is_loading_period = True
        self._current_period_id = None
        self._title_label.setText("No period selected")
        self._status_label.setText("")
        self._calendar.set_date_range(QDate.currentDate(), QDate.currentDate())
        self._calendar.set_unavailable_days([])
        self._is_loading_period = False

    # Returns the id of the period currently shown in the editor.
    def current_period_id(self) -> str | None:
        return self._current_period_id

    # Builds the static UI: title, hint text, calendar widget, and status label.
    def _build_ui(self) -> None:
        self._title_label = QLabel("No period selected")
        self._title_label.setStyleSheet(
            f"color: {th.TEXT_PRIMARY}; "
            f"font-family: {th.FONT_FAMILY}; "
            f"font-size: {th.FONT_SIZE_LG}px; "
            f"font-weight: {th.FONT_WEIGHT_BOLD};"
        )

        self._hint_label = QLabel(
            "Select a period above, then click calendar days to mark them as unavailable."
        )
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; "
            f"font-family: {th.FONT_FAMILY}; "
            f"font-size: {th.FONT_SIZE_SM}px;"
        )

        self._calendar = CalendarTableWidget(CalendarMode.INPUT)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; "
            f"font-family: {th.FONT_FAMILY}; "
            f"font-size: {th.FONT_SIZE_SM}px;"
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(th.SPACING_SMALL)
        layout.addWidget(self._title_label)
        layout.addWidget(self._hint_label)
        layout.addWidget(self._calendar)
        layout.addWidget(self._status_label)

    # Connects CalendarTableWidget signals to the editor handlers.
    def _connect_signals(self) -> None:
        self._calendar.day_clicked.connect(self._on_day_clicked)
        self._calendar.save_requested.connect(self._on_save_requested)

    # Reloads all periods from the service and stores them by period id.
    def _refresh_periods_cache(self) -> None:
        periods = self._service.get_periods()
        items = self._to_editable_periods(periods)
        self._periods_by_id = {item.period_id: item for item in items}

    # Converts raw period dictionaries into EditablePeriod view models.
    def _to_editable_periods(self, periods: Iterable[dict]) -> list[EditablePeriod]:
        items: list[EditablePeriod] = []

        for period in periods:
            item = self._formatter.format(period)
            if item.period_id:
                items.append(item)

        return items

    # Updates the UI according to the selected period data.
    def _render_period(self, period: EditablePeriod) -> None:
        self._is_loading_period = True

        self._title_label.setText(period.title)
        self._status_label.setText("")

        self._calendar.set_date_range(
            self._to_qdate(period.start_date),
            self._to_qdate(period.end_date),
        )
        self._calendar.set_unavailable_days(list(period.forbidden_days))

        self._is_loading_period = False

    # Handles a calendar day click by toggling that day through the service.
    def _on_day_clicked(self, qdate: QDate) -> None:
        if self._is_loading_period or self._current_period_id is None:
            return

        try:
            self._service.toggle_day(self._current_period_id, qdate.toPyDate())
            self._refresh_periods_cache()
            self._show_message("Day availability updated.")
        except Exception as error:
            self._show_message(f"Error: {error}")
            self.load_period(self._current_period_id)

    # Handles calendar save by updating the selected period date range.
    def _on_save_requested(
        self,
        start_qdate: QDate,
        end_qdate: QDate,
        unavailable_days: set[QDate],
    ) -> None:
        if self._current_period_id is None:
            return

        start = start_qdate.toPyDate()
        end = end_qdate.toPyDate()

        try:
            self._service.shift_period(self._current_period_id, start, end)
            self.load_period(self._current_period_id)
            self._show_message("Period saved successfully.")
        except Exception as error:
            self.load_period(self._current_period_id)
            self._show_message(f"Error: {error}")

    # Shows a short status or error message at the bottom of the editor.
    def _show_message(self, message: str) -> None:
        self._status_label.setText(message)

    # Converts a Python date object into a QDate for the calendar widget.
    def _to_qdate(self, value: date) -> QDate:
        return QDate(value.year, value.month, value.day)
