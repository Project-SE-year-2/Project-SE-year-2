from __future__ import annotations

from copy import error
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.models.enums import CalendarMode
from src.presenter.i_app_service import IAppService
from src.views.shared_components.calendar_table_widget import CalendarTableWidget
import src.styles.theme as th
import src.styles.period_widgets_style as ps


# ── Moed display label mapping ─────────────────────────────────────────────────
_MOED_DISPLAY: dict[str, str] = {
    "Aleph": "Moed A",
    "Bet":   "Moed B",
    "Gimel": "Moed C",
}


@dataclass(frozen=True)
class EditablePeriod:
    """View model for one editable exam period."""

    period_id:    str
    title:        str          # e.g. "FALL — Aleph"
    subtitle:     str          # e.g. "FALL 2026 — Moed A"
    start_date:   date
    end_date:     date
    forbidden_days: tuple[date, ...]


class EditablePeriodFormatter:
    """Converts raw period dictionaries from IAppService into EditablePeriod objects."""

    def format(self, period: dict) -> EditablePeriod:
        period_id  = str(period.get("id", "")).strip()
        semester   = str(period.get("semester", "")).strip()
        moed       = str(period.get("moed", "")).strip()
        start_date = period["start_date"]
        end_date   = period["end_date"]
        forbidden_days = tuple(period.get("forbidden_days", []) or [])

        year         = start_date.year if start_date else ""
        moed_display = _MOED_DISPLAY.get(moed, moed)
        subtitle     = (
            f"{semester} {year} — {moed_display}"
            if year else
            f"{semester} — {moed_display}"
        )

        return EditablePeriod(
            period_id      = period_id,
            title          = f"{semester} — {moed}",
            subtitle       = subtitle,
            start_date     = start_date,
            end_date       = end_date,
            forbidden_days = forbidden_days,
        )


class PeriodEditorWidget(QWidget):
    """
    Edits one selected exam period.

    The widget communicates only with IAppService.
    It does not import parsers, algorithm classes, or datastore classes directly.
    """

    def __init__(
        self,
        service: IAppService,
        formatter: EditablePeriodFormatter | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._service              = service
        self._formatter            = formatter or EditablePeriodFormatter()
        self._current_period_id: str | None = None
        self._periods_by_id: dict[str, EditablePeriod] = {}
        self._is_loading_period    = False

        self._build_ui()
        self._connect_signals()

    # ── Public API ─────────────────────────────────────────────────────────────

    def load_period(self, period_id: str) -> None:
        """Load a selected period by id and render it inside the editor."""
        self._refresh_periods_cache()

        if period_id not in self._periods_by_id:
            self._current_period_id = None
            self._show_message(f"Error: Period '{period_id}' was not found.")
            return

        self._current_period_id = period_id
        self._render_period(self._periods_by_id[period_id])

    def clear(self) -> None:
        """Clear the editor and reset to the initial no-selection state."""
        self._is_loading_period = True
        self._current_period_id = None
        self._title_label.setText("No period selected")
        self._subtitle_label.setText("")
        self._status_label.setText("")
        self._calendar.set_date_range(QDate.currentDate(), QDate.currentDate())
        self._calendar.set_unavailable_days([])
        self._is_loading_period = False

    def current_period_id(self) -> str | None:
        """Return the id of the period currently shown in the editor."""
        return self._current_period_id

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(th.SPACING_SMALL)

        # ── Section header: "Edit Exam Period" ─────────────────────────────
        header_w = QWidget()
        header_w.setStyleSheet("background: transparent;")
        header_l = QVBoxLayout(header_w)
        header_l.setContentsMargins(0, 0, 0, 0)
        header_l.setSpacing(2)

        section_lbl = QLabel("Edit Exam Period")
        section_lbl.setStyleSheet(
            f"color: {ps.EDITOR_SECTION_TITLE_COLOR};"
            f" font-size: {ps.EDITOR_SECTION_TITLE_SIZE}px;"
            " font-weight: 600; letter-spacing: 0.5px;"
            " background: transparent;"
        )

        hint_lbl = QLabel("Make changes to the calendar and manage unavailable days")
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet(
            f"color: {ps.EDITOR_SECTION_HINT_COLOR};"
            f" font-size: {ps.EDITOR_SECTION_HINT_SIZE}px;"
            " background: transparent;"
        )

        header_l.addWidget(section_lbl)
        header_l.addWidget(hint_lbl)
        layout.addWidget(header_w)

        # Thin divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"color: {ps.EDITOR_DIVIDER_COLOR};")
        layout.addWidget(divider)

        # ── Period title block (large "FALL — Aleph" + subtitle) ──────────
        period_title_w = QWidget()
        period_title_w.setStyleSheet("background: transparent;")
        period_title_l = QVBoxLayout(period_title_w)
        period_title_l.setContentsMargins(0, th.SPACING_SMALL, 0, 0)
        period_title_l.setSpacing(2)

        # _title_label is kept with this exact name for test compatibility:
        # tests assert "FALL" and "Aleph" are in _title_label.text()
        self._title_label = QLabel("No period selected")
        self._title_label.setStyleSheet(
            f"color: {ps.EDITOR_PERIOD_TITLE_COLOR};"
            f" font-size: {ps.EDITOR_PERIOD_TITLE_SIZE}px;"
            " font-weight: 800; background: transparent;"
        )

        self._subtitle_label = QLabel("")
        self._subtitle_label.setStyleSheet(
            f"color: {ps.EDITOR_PERIOD_SUBTITLE_COLOR};"
            f" font-size: {ps.EDITOR_PERIOD_SUBTITLE_SIZE}px;"
            " background: transparent;"
        )

        period_title_l.addWidget(self._title_label)
        period_title_l.addWidget(self._subtitle_label)
        layout.addWidget(period_title_w)

        self._warning_label = QLabel(
            "Note: The start date and end date cannot be marked as unavailable."
        )
        self._warning_label.setWordWrap(True)
        self._warning_label.setStyleSheet(
            f"""
            QLabel {{
                color: {th.DANGER_DARK};
                background-color: {th.DANGER_LIGHT};
                border: 1px solid {th.ERROR_BORDER};
                border-radius: 6px;
                padding: 8px;
                font-family: {th.FONT_FAMILY};
                font-size: {th.FONT_SIZE_SM}px;
                font-weight: {th.FONT_WEIGHT_BOLD};
            }}
            """
        )

        # ── Calendar ───────────────────────────────────────────────────────
        self._calendar = CalendarTableWidget(CalendarMode.INPUT)
        layout.addWidget(self._calendar, stretch=1)

        # ── Status / error message ─────────────────────────────────────────
        self._status_label = QLabel("")
        # self._status_label.setStyleSheet(
        #     f"color: {th.TEXT_TERTIARY}; font-size: {th.FONT_SIZE_SM}px;"
        #     " background: transparent;"
        # layout.addWidget(self._warning_label)
        # )
        layout.addWidget(self._status_label)

    # ── Signal wiring ──────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._calendar.day_clicked.connect(self._on_day_clicked)
        self._calendar.save_requested.connect(self._on_save_requested)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _refresh_periods_cache(self) -> None:
        periods = self._service.get_periods()
        items   = self._to_editable_periods(periods)
        self._periods_by_id = {item.period_id: item for item in items}

    def _to_editable_periods(self, periods: Iterable[dict]) -> list[EditablePeriod]:
        items: list[EditablePeriod] = []
        for period in periods:
            item = self._formatter.format(period)
            if item.period_id:
                items.append(item)
        return items

    def _render_period(self, period: EditablePeriod) -> None:
        self._is_loading_period = True

        self._title_label.setText(period.title)
        self._subtitle_label.setText(period.subtitle)
        self._status_label.setText("")

        self._calendar.set_date_range(
            self._to_qdate(period.start_date),
            self._to_qdate(period.end_date),
        )
        self._calendar.set_unavailable_days(list(period.forbidden_days))

        self._is_loading_period = False

    def _on_day_clicked(self, qdate: QDate) -> None:
        if self._is_loading_period or self._current_period_id is None:
            return
        try:
            self._service.toggle_day(self._current_period_id, qdate.toPyDate())
            self._refresh_periods_cache()
            self._show_message("Day availability updated.")
        except Exception as err:
            self._show_message(f"Error: {err}")
            self.load_period(self._current_period_id)

    def _on_save_requested(
        self,
        start_qdate: QDate,
        end_qdate: QDate,
        unavailable_days: set[QDate],
    ) -> None:
        if self._current_period_id is None:
            return
        start = start_qdate.toPyDate()
        end   = end_qdate.toPyDate()
        try:
            self._service.shift_period(self._current_period_id, start, end)
            self.load_period(self._current_period_id)
            self._show_message("Period saved successfully.")
        except Exception as err:
            self.load_period(self._current_period_id)
            self._show_message(f"Error: {err}")

    def _show_message(self, message: str) -> None:
        self._status_label.setText(message)

    def _to_qdate(self, value: date) -> QDate:
        return QDate(value.year, value.month, value.day)
