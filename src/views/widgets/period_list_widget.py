from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QFrame,
    QSizePolicy,
)

from src.presenter.i_app_service import IAppService
import src.styles.theme as th
import src.styles.period_widgets_style as ps


# ── Moed display label mapping ─────────────────────────────────────────────────
_MOED_DISPLAY: dict[str, str] = {
    "Aleph": "Moed A",
    "Bet":   "Moed B",
    "Gimel": "Moed C",
}


@dataclass(frozen=True)
class PeriodItem:
    """View model for one exam period row."""

    period_id:     str
    title:         str          # e.g. "FALL — Aleph"
    subtitle:      str          # e.g. "FALL 2026 — Moed A"
    start_date:    date
    end_date:      date
    program_count: int = 0


class PeriodFormatter:
    """Formats period dictionaries from IAppService into PeriodItem objects."""

    def format(self, period: dict) -> PeriodItem:
        period_id  = str(period.get("id", "")).strip()
        semester   = str(period.get("semester", "")).strip()
        moed       = str(period.get("moed", "")).strip()
        start_date = period["start_date"]
        end_date   = period["end_date"]

        year         = start_date.year if start_date else ""
        moed_display = _MOED_DISPLAY.get(moed, moed)
        subtitle     = f"{semester} {year} — {moed_display}" if year else f"{semester} — {moed_display}"

        programs      = period.get("programs") or []
        program_count = len(programs) if isinstance(programs, (list, tuple)) else 0

        return PeriodItem(
            period_id     = period_id,
            title         = f"{semester} — {moed}",
            subtitle      = subtitle,
            start_date    = start_date,
            end_date      = end_date,
            program_count = program_count,
        )


# ── Period row widget ──────────────────────────────────────────────────────────

class PeriodRowWidget(QFrame):
    """
    Card-style row for one exam period.

    Emits ``clicked`` when the user clicks anywhere on the row.

    API kept compatible with the original QPushButton-based version so that
    existing tests continue to work:
      • .text()  → returns the period title
      • .click() → programmatically emit clicked (used by tests)
    """

    clicked = pyqtSignal()

    def __init__(self, period: PeriodItem, parent=None):
        super().__init__(parent)
        self.period    = period
        self._selected = False

        self.setProperty("periodRow", "true")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._build_ui()
        self._apply_style()

    # ── Test-compatibility shims ───────────────────────────────────────────────

    def text(self) -> str:
        """Return the period title (backward-compat with QPushButton tests)."""
        return self.period.title

    def click(self) -> None:
        """Programmatically emit clicked (backward-compat with QPushButton tests)."""
        self.clicked.emit()

    # ── Selection state ────────────────────────────────────────────────────────

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()
        self._update_indicator()

    # ── Qt override ────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.clicked.emit()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(
            ps.ROW_PADDING_H, ps.ROW_PADDING_V,
            ps.ROW_PADDING_H, ps.ROW_PADDING_V,
        )
        row.setSpacing(ps.ROW_SPACING)

        # ── Selection indicator (circle / checkmark) ────────────────────────
        self._indicator = QLabel()
        self._indicator.setFixedSize(ps.IND_SIZE, ps.IND_SIZE)
        self._indicator.setAlignment(Qt.AlignCenter)
        self._indicator.setAttribute(Qt.WA_TransparentForMouseEvents)
        row.addWidget(self._indicator)
        self._update_indicator()

        # ── Title + subtitle ────────────────────────────────────────────────
        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        self._title_lbl = QLabel(self.period.title)
        self._title_lbl.setStyleSheet(
            f"color: {ps.ROW_TITLE_COLOR}; font-size: {ps.ROW_TITLE_SIZE}px;"
            " font-weight: 700; background: transparent;"
        )
        self._title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._subtitle_lbl = QLabel(self.period.subtitle)
        self._subtitle_lbl.setStyleSheet(
            f"color: {ps.ROW_SUBTITLE_COLOR}; font-size: {ps.ROW_SUBTITLE_SIZE}px;"
            " background: transparent;"
        )
        self._subtitle_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        title_col.addWidget(self._title_lbl)
        title_col.addWidget(self._subtitle_lbl)
        row.addLayout(title_col, stretch=1)

        # ── Date range ──────────────────────────────────────────────────────
        date_w = QWidget()
        date_w.setAttribute(Qt.WA_TransparentForMouseEvents)
        date_w.setStyleSheet("background: transparent;")
        date_l = QHBoxLayout(date_w)
        date_l.setContentsMargins(0, 0, 0, 0)
        date_l.setSpacing(6)

        icon_lbl = QLabel("📅")
        icon_lbl.setStyleSheet(
            f"font-size: 14px; background: transparent;"
        )
        icon_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        start = self.period.start_date.strftime("%d/%m/%Y")
        end   = self.period.end_date.strftime("%d/%m/%Y")
        date_lbl = QLabel(f"{start}  —  {end}")
        date_lbl.setStyleSheet(
            f"color: {ps.ROW_DATE_COLOR}; font-size: {ps.ROW_DATE_SIZE}px;"
            " background: transparent;"
        )

        date_l.addWidget(icon_lbl)
        date_l.addWidget(date_lbl)
        row.addWidget(date_w)

        # ── Programs count (show only when data is available) ───────────────
        if self.period.program_count > 0:
            prog_w = QWidget()
            prog_w.setAttribute(Qt.WA_TransparentForMouseEvents)
            prog_w.setStyleSheet("background: transparent;")
            prog_l = QVBoxLayout(prog_w)
            prog_l.setContentsMargins(0, 0, 0, 0)
            prog_l.setSpacing(0)
            prog_l.setAlignment(Qt.AlignCenter)

            prog_num = QLabel(str(self.period.program_count))
            prog_num.setAlignment(Qt.AlignCenter)
            prog_num.setStyleSheet(
                f"color: {ps.ROW_PROG_NUM_COLOR};"
                f" font-size: {ps.ROW_PROG_NUM_SIZE}px;"
                " font-weight: 700; background: transparent;"
            )
            prog_lbl = QLabel("Programs")
            prog_lbl.setAlignment(Qt.AlignCenter)
            prog_lbl.setStyleSheet(
                f"color: {ps.ROW_PROG_LBL_COLOR};"
                f" font-size: {ps.ROW_PROG_LBL_SIZE}px;"
                " background: transparent;"
            )
            prog_l.addWidget(prog_num)
            prog_l.addWidget(prog_lbl)
            row.addWidget(prog_w)

    def _apply_style(self) -> None:
        if self._selected:
            self.setStyleSheet(ps.ROW_FRAME_STYLE_SELECTED)
        else:
            self.setStyleSheet(ps.ROW_FRAME_STYLE_NORMAL)
        # Force Qt to re-apply the property-based selector
        self.style().unpolish(self)
        self.style().polish(self)

    def _update_indicator(self) -> None:
        if self._selected:
            self._indicator.setText("✓")
            self._indicator.setStyleSheet(ps.IND_CHECKED_STYLE)
        else:
            self._indicator.setText("")
            self._indicator.setStyleSheet(ps.IND_EMPTY_STYLE)


# ── Period list widget ─────────────────────────────────────────────────────────

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

        self._service              = service
        self._formatter            = formatter or PeriodFormatter()
        self._selected_period_id: str | None = None
        self._rows_by_id: dict[str, PeriodRowWidget] = {}

        self._build_ui()

    # ── Public API ─────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload periods from the service and rebuild the visible rows."""
        periods = self._service.get_periods()
        items   = self._to_period_items(periods)
        self._render_periods(items)

    def selected_period_id(self) -> str | None:
        return self._selected_period_id

    def clear_selection(self) -> None:
        self._selected_period_id = None
        self._update_row_states()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(th.SPACING_SMALL)

        # Header: title
        self._title_label = QLabel("Saved Exam Periods")
        self._title_label.setStyleSheet(
            f"color: {th.TEXT_PRIMARY}; font-size: {ps.LIST_TITLE_SIZE}px;"
            " font-weight: 700; background: transparent;"
        )

        self._hint_label = QLabel("Select a period to view or edit")
        self._hint_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; font-size: {ps.LIST_HINT_SIZE}px;"
            " background: transparent;"
        )

        layout.addWidget(self._title_label)
        layout.addWidget(self._hint_label)

        # Scrollable rows area
        self._rows_container = QWidget()
        self._rows_container.setStyleSheet("background: transparent;")
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(th.SPACING_SMALL)

        self._empty_label = QLabel("No periods loaded yet.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; padding: {th.SPACING_MEDIUM}px;"
        )
        self._rows_layout.addWidget(self._empty_label)
        self._rows_layout.addStretch()

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setMinimumHeight(80)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setWidget(self._rows_container)
        layout.addWidget(self._scroll_area, stretch=1)


    # ── Internal helpers ───────────────────────────────────────────────────────

    def _to_period_items(self, periods: Iterable[dict]) -> list[PeriodItem]:
        items: list[PeriodItem] = []
        for period in periods:
            item = self._formatter.format(period)
            if item.period_id:
                items.append(item)
        return items

    def _render_periods(self, periods: list[PeriodItem]) -> None:
        self._clear_rows()
        self._rows_by_id.clear()

        if not periods:
            self._selected_period_id = None
            empty = QLabel("No exam periods available.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color: {th.TEXT_TERTIARY}; padding: {th.SPACING_MEDIUM}px;"
            )
            self._rows_layout.addWidget(empty)
            self._rows_layout.addStretch()
            return

        valid_ids = {p.period_id for p in periods}
        if self._selected_period_id not in valid_ids:
            self._selected_period_id = None

        for period in periods:
            row = PeriodRowWidget(period)
            row.clicked.connect(
                lambda pid=period.period_id: self._on_period_clicked(pid)
            )
            self._rows_by_id[period.period_id] = row
            self._rows_layout.addWidget(row)

        self._rows_layout.addStretch()
        self._update_row_states()

    def _clear_rows(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            w    = item.widget()
            if w is not None:
                w.deleteLater()

    def _on_period_clicked(self, period_id: str) -> None:
        self._selected_period_id = period_id
        self._update_row_states()
        self.period_selected.emit(period_id)

    def _update_row_states(self) -> None:
        for pid, row in self._rows_by_id.items():
            row.set_selected(pid == self._selected_period_id)
