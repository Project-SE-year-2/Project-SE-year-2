"""
OutputScreen
============

Layout
------
QVBoxLayout (inside QScrollArea)
├── Toolbar: [← Back]  ·····  [⬇ Download Schedule]
├── SemesterTabsWidget: [🍃 FALL]  [🌸 SPRING]
└── FourMonthOutputWidget (white card)
      ├── Header: icon + title | [מועד א] [מועד ב] | ‹ N of M ›
      ├── Dynamic horizontal months (rebuilt per period date range)
      └── Legend

Navigation model — per-period
------------------------------
Each period stores its own position in _period_indices (UI-owned state).
NEXT/PREV update _period_indices[active_period_id] locally and then call
service.get_period_schedule(period_id, new_index) to fetch the new data.
Only the active period advances; all others remain unchanged.

The navigator counter shows the active period's position ("N of M") using
service.get_schedule_count(period_id=pid) for the accurate per-period total.
Switching tabs loads the stored index for the new period.

Period ID mapping
-----------------
UI semester names → backend Semester enum values via _SEMESTER_TO_ID:
    "FALL"   → "FALL"
    "SPRING" → "SPRI"

Exam filtering — two-layer
--------------------------
Primary:  exam_date in the period's date range from get_periods().
Fallback: if date-range filter yields nothing, filter by the "semester"
          and "moed" metadata fields embedded by _format_schedule_rows.

"No period" banner
------------------
When get_periods() has no entry for the active period_id,
FourMonthOutputWidget.show_no_period() shows a styled warning.

Isolated fetching
-----------------
service.get_period_schedule(period_id, local_index) fetches from disk
(disk mode via ResultsReader) or from _results_by_period (legacy mode).
No Cartesian-product mixing: NEXT on one period never affects another.

Export
------
service.export_current(path) uses ScheduleCombiner to merge all periods
into one unified ExamSchedule and writes it to disk.
"""

from __future__ import annotations

from datetime import date as _date

from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.models.enums import Semester, Moed
from src.views.output_screen.day_detail_dialog import DayDetailDialog
from src.views.output_screen.four_month_output_widget import FourMonthOutputWidget
from src.views.output_screen.semester_tabs_widget import SemesterTabsWidget
from src.views.shared_components.calendar_table_widget import CalendarTableWidget
from src.styles.output_screen_style import OUTPUT_SCREEN_STYLE


# ── Semester-name → backend period-id prefix mapping ─────────────────────────
_SEMESTER_TO_ID: dict[str, str] = {
    "FALL":   "FALL",
    "SPRING": "SPRI",
    "SUMMER": "SUMM",
}


def _to_date(val) -> _date | None:
    """Normalise to datetime.date (handles date, QDate, str)."""
    if isinstance(val, _date):
        return val
    if hasattr(val, "toPyDate"):
        return val.toPyDate()
    if isinstance(val, str):
        try:
            from datetime import datetime
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


class OutputScreen(QWidget):
    """Screen that displays generated exam schedules."""

    switch_to_input = pyqtSignal()

    BATCH_SIZE       = 10
    POLL_INTERVAL_MS = 3_000

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service

        # ── Shared global counter (for legacy compat properties) ──────────────
        self._global_index: int = 0
        self._global_total: int = 0

        # ── Per-period navigation indices ─────────────────────────────────────
        # Keys match backend period_id: "FALL_Aleph", "SPRI_Aleph", etc.
        # Each period tracks its OWN local page so NEXT on one period never
        # touches another period's position.
        self._period_indices: dict[str, int] = {
            f"{sem.value}_{moed.value}": 0
            for sem in Semester
            for moed in Moed
        }

        # ── Active view ───────────────────────────────────────────────────────
        self._current_semester: str = "FALL"
        self._current_moed:     str = "Aleph"

        self._setup_ui()
        self._setup_polling()

    # ── Active period ID ──────────────────────────────────────────────────────

    def _active_period_id(self) -> str:
        """Backend period_id for current semester + moed (e.g. "SPRI_Aleph")."""
        sem_code = _SEMESTER_TO_ID.get(self._current_semester, self._current_semester)
        return f"{sem_code}_{self._current_moed}"

    # ── Backward-compat properties ────────────────────────────────────────────

    @property
    def current_index(self) -> int:
        return self._global_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        self._global_index = value

    @property
    def current_schedules(self) -> list:
        # Backward-compat stub — isolated architecture no longer uses a buffer.
        return []

    @current_schedules.setter
    def current_schedules(self, value: list) -> None:
        pass  # no-op

    @property
    def total_schedules(self) -> int:
        return self._global_total

    @total_schedules.setter
    def total_schedules(self, value: int) -> None:
        self._global_total = value

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setObjectName("outputScreen")
        self.setStyleSheet(OUTPUT_SCREEN_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        content.setObjectName("outputScreen")
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("backBtn")
        self.back_btn.clicked.connect(self._on_back_clicked)

        self.download_btn = QPushButton("⬇  Download Schedule")
        self.download_btn.setObjectName("downloadBtn")
        self.download_btn.clicked.connect(self._on_download_clicked)

        toolbar.addWidget(self.back_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.download_btn)
        main_layout.addLayout(toolbar)

        # Semester tabs
        self.semester_tabs = SemesterTabsWidget()
        self.semester_tabs.semester_changed.connect(self._on_semester_changed)
        main_layout.addWidget(self.semester_tabs)

        # FourMonthOutputWidget
        self.four_month = FourMonthOutputWidget()
        self.four_month.exam_day_clicked.connect(self._on_exam_day_clicked)
        self.four_month.moed_changed.connect(self._on_moed_changed)
        main_layout.addWidget(self.four_month, stretch=1)

        self.navigator   = self.four_month.navigator
        self.navigator.navigate_to.connect(self._on_navigator_index_changed)
        self.navigator.prefetch_needed.connect(self._on_prefetch_needed)
        self.sched_label = self.navigator._counter_lbl

        self._scroll.setWidget(content)
        root.addWidget(self._scroll)

        # Hidden CalendarTableWidget — backward-compat for EP-65 tests
        self.calendar = CalendarTableWidget()
        self.calendar.exams_day_clicked.connect(self._on_exam_day_clicked)
        # exam_clicked intentionally NOT connected (would open dialog twice)

    def _setup_polling(self) -> None:
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_schedule_count)
        self.destroyed.connect(self.poll_timer.stop)

    # ── Qt events ─────────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)

        # Guard: on Windows a modal QMessageBox (e.g. the "download success"
        # popup) re-fires showEvent on the active QStackedWidget page when it
        # closes.  We must NOT reset _period_indices in that case or the user
        # would silently jump back to schedule 0.
        #
        # Rule:
        #   _global_total == 0  → first show before any generation (or after a
        #                         fresh generation reset in _on_generation_finished).
        #                         Reset all state and show a loading indicator.
        #   _global_total  > 0  → data is already loaded; just refresh the
        #                         display at the stored positions and return.
        if self._global_total > 0:
            self._refresh_screen_display()
            self.poll_timer.start(self.POLL_INTERVAL_MS)
            return

        # ── First show / no data yet ──────────────────────────────────────────
        self._global_index = 0
        for key in self._period_indices:
            self._period_indices[key] = 0
        self.semester_tabs.set_enabled_all(False)
        self.four_month.show_loading(self._current_semester)
        self._refresh_screen_display()
        # Re-enable tabs immediately if data already exists (generation finished
        # before the user navigated here — _on_generation_finished won't fire again).
        has_data = any(
            self.service.get_schedule_count(period_id=pid) > 0
            for pid in self._period_indices
        )
        if has_data:
            self.semester_tabs.set_enabled_all(True)
        self.poll_timer.start(self.POLL_INTERVAL_MS)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.poll_timer.stop()

    # ── Semester / moed switching ─────────────────────────────────────────────

    def _on_semester_changed(self, semester: str) -> None:
        """Switch semester tab — restore the stored index for the new period."""
        self._current_semester = semester
        self._global_index = self._period_indices.get(self._active_period_id(), 0)
        self._refresh_screen_display()

    def _on_moed_changed(self, moed: str) -> None:
        """Switch moed — restore the stored index for the new period."""
        self._current_moed = moed
        self._global_index = self._period_indices.get(self._active_period_id(), 0)
        self._refresh_screen_display()

    # ── Central display refresh ───────────────────────────────────────────────

    def _refresh_screen_display(self) -> None:
        """Fetch and render the isolated schedule for the active (semester, moed).

        Uses service.get_period_schedule(period_id, local_index) which reads
        directly from the period's own file (disk mode) or from the in-memory
        per-period cache (legacy mode).  No Cartesian-product mixing occurs.
        """
        sem  = self._current_semester
        moed = self._current_moed
        pid  = self._active_period_id()
        idx  = self._period_indices.get(pid, 0)

        # ── Fetch isolated period schedule ────────────────────────────────────
        try:
            exams = self.service.get_period_schedule(pid, idx)
        except Exception as exc:
            print(f"OutputScreen: get_period_schedule({pid}, {idx}) failed: {exc}")
            exams = []

        # ── Resolve period date range ─────────────────────────────────────────
        start_date: _date | None = None
        end_date:   _date | None = None
        period_found = False
        try:
            for p in self.service.get_periods():
                if p.get("id") == pid:
                    period_found = True
                    start_date = _to_date(p.get("start_date"))
                    end_date   = _to_date(p.get("end_date"))
                    break
        except Exception:
            period_found = True   # service failed → assume period exists

        # ── Period not configured → styled warning ────────────────────────────
        if not period_found:
            self.four_month.show_no_period(sem, moed)
            self._update_navigator()
            return

        # ── Update calendar card ──────────────────────────────────────────────
        if exams:
            self._global_total = max(self._global_total, 1)
            self.four_month.update_schedule(
                exams,
                semester=sem,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            self.four_month.show_empty(sem)

        self._update_navigator()

    # ── Per-period navigator ──────────────────────────────────────────────────

    def _on_navigator_index_changed(self, index: int) -> None:
        """Advance ONLY the active period — other periods stay unchanged.

        The new isolated architecture stores a local index per period and
        fetches that period's schedule directly via get_period_schedule().
        No Cartesian-product scanning or cross-period interference.
        """
        pid = self._active_period_id()
        self._period_indices[pid] = index
        self._global_index = index
        self._refresh_screen_display()

    def _on_prefetch_needed(self, loaded_so_far: int) -> None:
        # No-op in isolated mode — each NEXT fetches on demand.
        pass

    def _update_navigator(self) -> None:
        """Push the active period's local index and exact per-period total.

        When the period has no schedules (total == 0) the navigator shows
        "— of —" and both NEXT and PREV are disabled automatically by
        ScheduleNavigatorWidget.set_state(total=0).
        """
        pid         = self._active_period_id()
        current_idx = self._period_indices.get(pid, 0)

        # get_schedule_count(period_id) is authoritative: 0 = no schedules.
        # Do NOT fall back to _global_total here — a period may genuinely have
        # zero schedules while another period has many.
        try:
            total = self.service.get_schedule_count(period_id=pid)
            if not isinstance(total, int) or total < 0:
                total = 0
        except Exception:
            total = 0

        if total > 0:
            self._global_total = max(self._global_total, total)

        # Hide the entire navigator bar (counter + Prev/Next) when there are
        # no schedules for this period — show it again as soon as data arrives.
        self.navigator.setVisible(total > 0)
        self.navigator.set_state(current=current_idx, total=total, loaded=total)

    # ── Polling ───────────────────────────────────────────────────────────────

    def _poll_schedule_count(self) -> None:
        """Refresh total/display every POLL_INTERVAL_MS.

        Checks whether per-period data has arrived since the last poll.
        When data first appears, re-renders so the loading indicator clears.
        """
        pid = self._active_period_id()

        try:
            count = self.service.get_schedule_count(period_id=pid)
            if isinstance(count, int) and count > 0:
                was_empty = self._global_total == 0
                self._global_total = max(self._global_total, count)
                if was_empty:
                    self.semester_tabs.set_enabled_all(True)
                    self._refresh_screen_display()
                    return
        except Exception:
            pass

        self._update_navigator()

    # ── Exam cell click → DayDetailDialog ────────────────────────────────────

    def _on_exam_day_clicked(self, exams: list, anchor) -> None:
        program_names = self._get_program_names()
        exam_date     = exams[0].get("exam_date") if exams else None
        dialog = DayDetailDialog(
            exams         = exams,
            exam_date     = exam_date,
            program_names = program_names,
            anchor_pos    = anchor,
            parent        = self,
        )
        dialog.exec_()

    def _on_exam_clicked(self, exam_data: dict) -> None:
        """Backward-compat shim."""
        self._on_exam_day_clicked([exam_data], anchor=None)

    def _get_program_names(self) -> dict:
        try:
            return {p["id"]: p["name"] for p in self.service.get_available_programs()}
        except Exception:
            return {}

    # ── EngineListener integration ────────────────────────────────────────────

    _PERIOD_PREFIX_TO_TAB: dict[str, str] = {
        "FALL": "FALL",
        "SPRI": "SPRING",
    }

    def connect_listener(self, listener) -> None:
        זז
        listener.finished.connect(self._on_generation_finished)
        listener.error.connect(self._on_generation_error)

    def _on_period_ready(self, period_id: str) -> None:
        """Called once per exam period when the engine finishes generating it.

        Disk mode:   data is immediately readable via get_period_schedule().
        Legacy mode: _results_by_period[period_id] is populated at this point,
                     so get_period_schedule() can serve it right away.
        """
        prefix = period_id.split("_")[0].upper()
        tab    = self._PERIOD_PREFIX_TO_TAB.get(prefix, "FALL")
        if tab != self._current_semester:
            return

        # Check whether this period matches the active tab
        if period_id != self._active_period_id():
            return

        # Data just arrived for the currently-visible period — update count and render.
        try:
            count = self.service.get_schedule_count(period_id=period_id)
            if isinstance(count, int) and count > 0:
                self._global_total = max(self._global_total, count)
                self._refresh_screen_display()
        except Exception:
            pass

    def _on_generation_finished(self, total: int) -> None:
        """Called when generation is fully complete — all period data available.

        Re-enables tabs, updates the total, resets indices to 0, and renders
        the first schedule for the currently visible period.
        """
        self.semester_tabs.set_enabled_all(True)

        # Update total from the active period's exact count.
        pid = self._active_period_id()
        real_total = total if isinstance(total, int) and total > 0 else 0
        try:
            count = self.service.get_schedule_count(period_id=pid)
            if isinstance(count, int) and count > 0:
                real_total = count
        except Exception:
            pass
        self._global_total = real_total

        # Reset all period indices and render schedule 0 for the active period.
        for key in self._period_indices:
            self._period_indices[key] = 0
        self._global_index = 0
        self._refresh_screen_display()

    def _on_generation_error(self, message: str) -> None:
        self.four_month.show_error(message)
        self.semester_tabs.set_enabled_all(True)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _on_back_clicked(self) -> None:
        self.switch_to_input.emit()

    def _on_download_clicked(self) -> None:
        """Export the currently displayed per-period schedules into one combined file.

        Uses export_by_period_indices() which reads each period at its local
        index — exactly what is shown on screen — and merges them into a single
        human-readable report.
        """
        # Check that at least one period has data.
        has_data = any(
            self.service.get_schedule_count(period_id=pid) > 0
            for pid in self._period_indices
        )
        if not has_data:
            QMessageBox.warning(self, "No Schedule", "No schedule is currently loaded.")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Schedule", "",
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)",
            options=options,
        )
        if not file_path:
            return

        try:
            self.service.export_by_period_indices(self._period_indices, file_path)
            QMessageBox.information(self, "Success", "Schedule exported successfully.")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed", f"Could not export schedule:\n{exc}"
            )
