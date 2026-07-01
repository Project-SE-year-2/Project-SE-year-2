"""
OutputScreen
============

Layout
------
QVBoxLayout (inside QScrollArea)
ג”ג”€ג”€ Toolbar: [ג† Back]  ֲ·ֲ·ֲ·ֲ·ֲ·  [ג¬‡ Download Schedule]
ג”ג”€ג”€ SemesterTabsWidget: [נƒ FALL]  [נ¸ SPRING]
ג””ג”€ג”€ MoedCalendarOutputWidget (white card)
      ג”ג”€ג”€ Header: icon + title | [׳׳•׳¢׳“ ׳] [׳׳•׳¢׳“ ׳‘] | ג€¹ N of M ג€÷
      ג”ג”€ג”€ Dynamic horizontal months (rebuilt per period date range)
      ג””ג”€ג”€ Legend

Navigation model ג€” per-period
------------------------------
Each period stores its own navigation state in _window_states. (UI-owned state).
NEXT/PREV update the active period's WindowState and then call
service.get_period_schedule(period_id, current_index) to fetch the new data.
Only the active period advances; all others remain unchanged.

The navigator counter shows the active period's position ("N of M") using
service.get_schedule_count(period_id=pid) for the accurate per-period total.
Switching tabs loads the stored index for the new period.

Period ID mapping
-----------------
UI semester names ג†’ backend Semester enum values via _SEMESTER_TO_ID:
    "FALL"   ג†’ "FALL"
    "SPRING" ג†’ "SPRI"

Exam filtering ג€” two-layer
--------------------------
Primary:  exam_date in the period's date range from get_periods().
Fallback: if date-range filter yields nothing, filter by the "semester"
          and "moed" metadata fields embedded by _format_schedule_rows.

"No period" banner
------------------
When get_periods() has no entry for the active period_id,
MoedCalendarOutputWidget.show_no_period() shows a styled warning.

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

from copy import deepcopy
from datetime import date as _date

from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from PyQt5.QtGui import QIcon

from src.models.enums import Semester, Moed
from src.styles.icons import load_pixmap, ICON_DOWNLOAD
from src.views.output_screen.day_detail_dialog import DayDetailDialog
from src.views.output_screen.edit_exam_dialog import EditExamDialog
from src.views.output_screen.moed_calendar_output_widget import MoedCalendarOutputWidget
from src.views.output_screen.semester_tabs_widget import SemesterTabsWidget
from src.views.settings_screen.ranking_config_widget import RankingConfigDialog
from src.views.shared_components.calendar_table_widget import CalendarTableWidget
from src.views.shared_components.error_banner import ErrorBanner
from src.styles.output_screen_style import OUTPUT_SCREEN_STYLE
from src.views.output_screen.window_state import WindowState


# ג”€ג”€ Semester-name ג†’ backend period-id prefix mapping ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
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
    POLL_INTERVAL_MS = 150

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service

        # ג”€ג”€ Shared global counter (for legacy compat properties) ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
        self._global_index: int = 0
        self._global_total: int = 0

        # ג”€ג”€ Per-period window states ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
        # Each period has its own WindowState to track history, current pointer.
        # This allows the user to navigate back and forth
        # within each period independently, without affecting other periods.
        self._window_states: dict[str, WindowState] = {
            f"{sem.value}_{moed.value}": WindowState()
            for sem in Semester
            for moed in Moed
        }

        # ג”€ג”€ Active view ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
        self._current_semester: str = "FALL"
        self._current_moed:     str = "Aleph"
        self._check_conflicts_next: bool = False
        self._day_dialog: DayDetailDialog | None = None
        self._edit_dialog: EditExamDialog | None = None
        self._edit_schedule_mode: bool = False
        # Edit mode state (pending changes tracked here until SAVE)
        self._editable_rows: list[dict] = []
        self._original_edit_rows: list[dict] | None = None
        self._edit_period_start: _date | None = None
        self._edit_period_end:   _date | None = None
        self._edit_forbidden_days: set = set()
        self._pending_refresh_while_editing: bool = False
        # True only when the calendar is actually rendering a real schedule.
        # Used by the poll timer to know when a re-render is still needed.
        self._calendar_displaying_data: bool = False

        # EP-149 bug 1: number of schedules the current view reflects. When the
        # active period's count grows past this, the poll timer pops the refresh
        # banner ג€” so newly generated (better-ranked) schedules are offered as
        # early as the next poll tick. Reset to 0 means "recapture on next render".
        self._ranked_baseline: int = 0

        # EP-150: best (rank-1) score last seen per period, for the active sort.
        # When it improves, a strictly better schedule was found ג†’ notify. Empty
        # entry means "re-baseline on next poll" (no false notification).
        self._best_seen: dict[str, float] = {}

        # Delayed empty-state: fires 2 s after we decide there's no data,
        # but is cancelled immediately if real data arrives first.
        self._empty_timer = QTimer(self)
        self._empty_timer.setSingleShot(True)
        self._empty_timer.setInterval(2000)
        self._empty_semester: str = ""

        # Delayed loading-state: fires 2 s after the first show_loading call,
        # but is cancelled immediately if real data arrives first.
        self._loading_timer = QTimer(self)
        self._loading_timer.setSingleShot(True)
        self._loading_timer.setInterval(2000)
        self._loading_semester: str = ""

        self._post_refresh_timer = QTimer(self)
        self._post_refresh_timer.setSingleShot(True)
        self._post_refresh_timer.setInterval(0)
        self._post_refresh_timer.timeout.connect(self._refresh_screen_display)

        self._setup_ui()
        self._setup_polling()
        self._empty_timer.timeout.connect(self._on_empty_timeout)
        self._loading_timer.timeout.connect(self._on_loading_timeout)

    # ג”€ג”€ Active period ID ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    def _active_period_id(self) -> str:
        """Backend period_id for current semester + moed (e.g. "SPRI_Aleph")."""
        sem_code = _SEMESTER_TO_ID.get(self._current_semester, self._current_semester)
        return f"{sem_code}_{self._current_moed}"

    def _active_period_count(self) -> int:
        """Schedule count for the active period, or 0 when unavailable."""
        try:
            c = self.service.get_schedule_count(period_id=self._active_period_id())
            return c if isinstance(c, int) and c > 0 else 0
        except Exception:
            return 0

    def _jump_to_period(self, period_id: str) -> None:
        """Switch the active view to the given period and render it."""
        prefix, _, moed = period_id.partition("_")
        semester = self._PERIOD_PREFIX_TO_TAB.get(prefix.upper())
        if not semester or not moed:
            return
        self._current_semester = semester
        self._current_moed = moed
        self.semester_tabs.set_selected(semester)
        self.four_month.set_active_moed(moed)

    def _select_first_available_period(self) -> None:
        """Switch to the first period that already has generated schedules."""
        try:
            if self.service.get_schedule_count(period_id=self._active_period_id()) > 0:
                return
        except Exception:
            pass

        prefix_to_tab = {
            "FALL": "FALL",
            "SPRI": "SPRING",
            "SUMM": "SUMMER",
        }
        for period_id in self._window_states:
            try:
                if self.service.get_schedule_count(period_id=period_id) <= 0:
                    continue
            except Exception:
                continue

            prefix, _, moed = period_id.partition("_")
            semester = prefix_to_tab.get(prefix.upper())
            if not semester or not moed:
                continue

            self._current_semester = semester
            self._current_moed = moed
            self.semester_tabs.set_selected(semester)
            self.four_month.set_active_moed(moed)
            return

    # ג”€ג”€ Active WindowState ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
    def _active_window_state(self) -> WindowState:
        """Return the WindowState object for the currently active period."""
        pid = self._active_period_id()
        return self._window_states.setdefault(pid, WindowState())

    def _period_index(self, period_id: str) -> int:
        """Return the current schedule index for a period from WindowState."""
        return self._window_states.setdefault(period_id, WindowState()).current()

    def _sync_active_counter_state(self) -> None:
        """Keep legacy counter fields aligned with the active period only."""
        self._global_index = self._active_window_state().current()
        self._global_total = self._active_period_count()

    def _current_export_indices(self) -> dict[str, int]:
        """Return export-compatible period indices derived from WindowState."""
        return {
            pid: state.current()
            for pid, state in self._window_states.items()
        }

    # ג”€ג”€ Backward-compat properties ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    @property
    def current_index(self) -> int:
        return self._active_window_state().current()

    @current_index.setter
    def current_index(self, value: int) -> None:
        self._active_window_state().move_to(value)
        self._sync_active_counter_state()

    @property
    def current_schedules(self) -> list:
        # Backward-compat stub ג€” isolated architecture no longer uses a buffer.
        return []

    @current_schedules.setter
    def current_schedules(self, value: list) -> None:
        pass  # no-op

    @property
    def total_schedules(self) -> int:
        return self._active_period_count()

    @total_schedules.setter
    def total_schedules(self, value: int) -> None:
        self._global_total = max(0, int(value)) if isinstance(value, int) else 0

    # ג”€ג”€ UI construction ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

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
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("backBtn")
        self.back_btn.clicked.connect(self._on_back_clicked)

        self.download_btn = QPushButton("  Download Schedule")
        _dl_pix = load_pixmap(ICON_DOWNLOAD, size=18)
        if not _dl_pix.isNull():
            self.download_btn.setIcon(QIcon(_dl_pix))

        self.download_btn.setObjectName("downloadBtn")
        self.download_btn.clicked.connect(self._on_download_clicked)

        self.sort_settings_btn = QPushButton("Sort Settings")
        self.sort_settings_btn.setObjectName("sortSettingsBtn")
        self.sort_settings_btn.clicked.connect(self._show_sort_settings)

        self.edit_schedule_btn = QPushButton("Edit Schedule")
        self.edit_schedule_btn.setObjectName("editScheduleBtn")
        self.edit_schedule_btn.setCheckable(True)
        self.edit_schedule_btn.clicked.connect(self._on_edit_schedule_toggled)

        toolbar.addWidget(self.back_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.edit_schedule_btn)
        toolbar.addWidget(self.sort_settings_btn)
        toolbar.addWidget(self.download_btn)
        main_layout.addLayout(toolbar)

        # Semester tabs
        self.semester_tabs = SemesterTabsWidget()
        self.semester_tabs.semester_changed.connect(self._on_semester_changed)
        main_layout.addWidget(self.semester_tabs)

        # Conflict banner (hidden by default)
        self._conflict_banner = self._build_conflict_banner()
        self._conflict_banner.setVisible(False)
        main_layout.addWidget(self._conflict_banner)

        # Success banner (hidden by default, auto-hides after 5 s)
        self._success_banner = self._build_success_banner()
        self._success_banner.setVisible(False)
        main_layout.addWidget(self._success_banner)
        self._sorting_update_banner = self._build_sorting_update_banner()
        self._sorting_update_banner.setVisible(False)
        main_layout.addWidget(self._sorting_update_banner)

        # Edit-mode banner (SAVE / CANCEL)
        self._edit_mode_banner = self._build_edit_mode_banner()
        self._edit_mode_banner.setVisible(False)
        main_layout.addWidget(self._edit_mode_banner)

        # Inline error banner for edit-mode drag validation
        self._edit_error_banner = ErrorBanner()
        self._edit_error_banner.setVisible(False)
        main_layout.addWidget(self._edit_error_banner)
        self._success_timer = QTimer(self)
        self._success_timer.setSingleShot(True)
        self._success_timer.timeout.connect(lambda: self._success_banner.setVisible(False))

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(16)

        # MoedCalendarOutputWidget
        self.four_month = MoedCalendarOutputWidget()
        self.four_month.exam_day_clicked.connect(self._on_exam_day_clicked)
        self.four_month.exam_moved.connect(self._on_exam_drag_moved)
        self.four_month.moed_changed.connect(self._on_moed_changed)

        self._sort_dialog = RankingConfigDialog(self)
        self.ranking_panel = self._sort_dialog.ranking_widget
        self.ranking_panel.sort_order_changed.connect(self.on_sort_changed)

        body_layout.addWidget(self.four_month, stretch=1)
        main_layout.addLayout(body_layout, stretch=1)

        self._generation_error_banner = ErrorBanner()
        main_layout.addWidget(self._generation_error_banner)

        self.navigator   = self.four_month.navigator
        self.navigator.navigate_to.connect(self._on_navigator_index_changed)
        self.navigator.prefetch_needed.connect(self._on_prefetch_needed)
        self.sched_label = self.navigator._counter_lbl

        self._scroll.setWidget(content)
        root.addWidget(self._scroll)

        # Hidden CalendarTableWidget ג€” backward-compat for EP-65 tests
        self.calendar = CalendarTableWidget()
        self.calendar.exams_day_clicked.connect(self._on_exam_day_clicked)
        self._apply_edit_mode_ui()
        # exam_clicked intentionally NOT connected (would open dialog twice)

    def _show_sort_settings(self):
        """Open the Sorting Preferences dialog."""
        if self._edit_schedule_mode:
            return
        room_on = self.service.get_constraint_settings().room_scheduling_enabled
        self.ranking_panel.set_room_scheduling_enabled(room_on)
        self._sort_dialog.exec_()

    def _build_conflict_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("conflictBanner")
        banner.setStyleSheet("""
            QFrame#conflictBanner {
                background: #FEF2F2;
                border: 1.5px solid #FECACA;
                border-radius: 10px;
            }
        """)

        row = QHBoxLayout(banner)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)

        icon = QLabel("")
        icon.setStyleSheet("color: #DC2626; font-size: 18px;")
        row.addWidget(icon)

        self._conflict_text = QLabel("")
        self._conflict_text.setWordWrap(True)
        self._conflict_text.setStyleSheet(
            "color: #DC2626; font-size: 13px; font-weight: 700; letter-spacing: 0.3px;"
        )
        row.addWidget(self._conflict_text, stretch=1)

        close_btn = QPushButton("ג•")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #DC2626;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton:hover { color: #991B1B; }
        """)
        close_btn.clicked.connect(self._hide_conflict_banner)
        row.addWidget(close_btn)

        return banner

    def _show_conflict_banner(self, message: str) -> None:
        self._conflict_text.setText(message)
        self._conflict_banner.setVisible(True)

    def _hide_conflict_banner(self) -> None:
        self._conflict_banner.setVisible(False)
        self._conflict_text.setText("")

    def _build_success_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("successBanner")
        banner.setStyleSheet("""
            QFrame#successBanner {
                background: #F0FDF4;
                border: 1.5px solid #BBF7D0;
                border-radius: 10px;
            }
        """)
        row = QHBoxLayout(banner)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)

        icon = QLabel("ג“")
        icon.setStyleSheet("color: #16A34A; font-size: 18px; font-weight: 700;")
        row.addWidget(icon)

        self._success_text = QLabel("")
        self._success_text.setStyleSheet(
            "color: #16A34A; font-size: 13px; font-weight: 700; letter-spacing: 0.3px;"
        )
        row.addWidget(self._success_text, stretch=1)

        return banner
    
    def _build_sorting_update_banner(self) -> QFrame:
        """Build a banner that lets the user refresh when optimized results are available."""
        banner = QFrame()
        banner.setObjectName("sortingUpdateBanner")
        banner.setStyleSheet("""
            QFrame#sortingUpdateBanner {
                background: #EFF6FF;
                border: 1.5px solid #BFDBFE;
                border-radius: 10px;
            }
        """)

        row = QHBoxLayout(banner)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)

        self._sorting_update_label = QLabel("New optimized schedules are available.")
        self._sorting_update_label.setStyleSheet(
            "color: #1D4ED8; font-size: 13px; font-weight: 700;"
        )
        row.addWidget(self._sorting_update_label, stretch=1)

        refresh_btn = QPushButton("Refresh View")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1D4ED8;
            }
        """)
        refresh_btn.clicked.connect(self._on_refresh_pending_clicked)
        row.addWidget(refresh_btn)

        return banner

    def _show_success_banner(self, message: str) -> None:
        self._success_text.setText(message)
        self._success_banner.setVisible(True)
        self._success_timer.start(5000)

    def _show_sorting_update_banner(self, message: str | None = None) -> None:
        """Show the optimized-results pending update banner.

        message overrides the banner text ג€” used by EP-150 to say specifically
        that a *better* schedule was found rather than just "more available".
        """
        if message is not None:
            self._sorting_update_label.setText(message)
        self._sorting_update_banner.setVisible(True)


    def _hide_sorting_update_banner(self) -> None:
        """Hide the optimized-results pending update banner."""
        self._sorting_update_banner.setVisible(False)

    def _setup_polling(self) -> None:
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_schedule_count)
        self.destroyed.connect(self.poll_timer.stop)

    # ג”€ג”€ Qt events ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    def showEvent(self, event) -> None:
        super().showEvent(event)

        # Always reset to FALL ג€” Moed Aleph as the default view.
        self._current_semester = "FALL"
        self._current_moed     = "Aleph"
        self.semester_tabs.set_selected("FALL")
        self.four_month.set_active_moed("Aleph")
        self._select_first_available_period()
        self._hide_conflict_banner()
        self._hide_sorting_update_banner()
        # Recapture the baseline for whatever period we land on.
        self._ranked_baseline = 0
        self._best_seen.clear()

        # Guard: on Windows a modal QMessageBox (e.g. the "download success"
        # popup) re-fires showEvent on the active QStackedWidget page when it
        # closes.  We must NOT reset _window_states in that case or the user
        # would silently jump back to schedule 0.
        #
        # Rule:
        #   active period count == 0  ג†’ first show before any generation (or after a
        #                         fresh generation reset in _on_generation_finished).
        #                         Reset all state and show a loading indicator.
        #   active period count  > 0  ג†’ data is already loaded; just refresh the
        #                         display at the stored positions and return.
        if self._active_period_count() > 0:
            self._sync_active_counter_state()
            self._calendar_displaying_data = False
            self._refresh_screen_display()
            self.poll_timer.start(self.POLL_INTERVAL_MS)
            return

        # ג”€ג”€ First show / no data yet ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
        for state in self._window_states.values():
            state.clear()
        self._sync_active_counter_state()
        self._calendar_displaying_data = False
        self.semester_tabs.set_enabled_all(False)
        self._loading_semester = self._current_semester
        if not self._loading_timer.isActive():
            self._loading_timer.start()

        # Immediately check if data is already available (generation finished
        # before the user arrived here) ג€” render the first schedule right away.
        pid = self._active_period_id()
        try:
            count = self.service.get_schedule_count(period_id=pid)
            if isinstance(count, int) and count > 0:
                self._sync_active_counter_state()
                self.semester_tabs.set_enabled_all(True)
                self._refresh_screen_display()
                self.poll_timer.start(self.POLL_INTERVAL_MS)
                return
        except Exception:
            pass

        self._refresh_screen_display()
        self.poll_timer.start(self.POLL_INTERVAL_MS)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.poll_timer.stop()

    # ג”€ג”€ Semester / moed switching ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    def _on_semester_changed(self, semester: str) -> None:
        """Switch semester tab ג€” restore the stored index for the new period."""
        if self._edit_schedule_mode:
            return
        self._current_semester = semester
        self._sync_active_counter_state()
        self._hide_conflict_banner()
        self._hide_sorting_update_banner()
        self._check_conflicts_next = True
        self._calendar_displaying_data = False
        self._ranked_baseline = 0   # recapture for the newly active period
        self._best_seen.clear()
        self._refresh_screen_display()

    def _on_moed_changed(self, moed: str) -> None:
        """Switch moed, or switch to the read-only All Sessions overview."""
        if self._edit_schedule_mode:
            return
        self._current_moed = moed
        self._hide_conflict_banner()
        self._hide_sorting_update_banner()
        self._calendar_displaying_data = False

        if moed == "All":
            # All Sessions is read-only: no navigation, no conflict checks.
            try:
                if self.service.get_sort_order():
                    self.service.refresh_ranked_view()
            except Exception:
                pass
            self._refresh_all_sessions_display()
            return

        self._sync_active_counter_state()
        self._check_conflicts_next = True
        self._ranked_baseline = 0   # recapture for the newly active moed
        self._best_seen.clear()
        self._refresh_screen_display()

    # ג”€ג”€ Central display refresh ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    def _refresh_all_sessions_display(self) -> None:
        """Fetch and render the read-only All Sessions overview for the active semester.

        Shows one grouped section per moed (A/B/C), each displaying the currently
        selected schedule index for that period.  No navigation is shown.
        """
        sem      = self._current_semester
        sem_code = _SEMESTER_TO_ID.get(sem, sem)
        sections: list[dict] = []
        try:
            sort_active = bool(self.service.get_sort_order())
        except Exception:
            sort_active = False

        for moed in ["Aleph", "Bet", "Gimel"]:
            pid  = f"{sem_code}_{moed}"
            idx = 0 if sort_active else self._period_index(pid)
            exams: list = []
            start_date: _date | None = None
            end_date:   _date | None = None

            try:
                exams = self.service.get_period_schedule(pid, idx) or []
            except Exception:
                pass

            try:
                for p in self.service.get_periods():
                    if p.get("id") == pid:
                        start_date = _to_date(p.get("start_date"))
                        end_date   = _to_date(p.get("end_date"))
                        break
            except Exception:
                pass

            sections.append({
                "moed":       moed,
                "exams":      exams,
                "start_date": start_date,
                "end_date":   end_date,
            })

        self.four_month.show_all_sessions(sem, sections)

    def _clamp_active_index_to_valid_range(self) -> None:
        """Keep the active period's index inside the current valid range."""
        pid = self._active_period_id()
        state = self._active_window_state()
        try:
            total = self.service.get_schedule_count(period_id=pid)
        except Exception:
            total = 0
        if not isinstance(total, int) or total <= 0:
            if state.current() != 0:
                state.move_to(0)
            return
        max_index = max(0, total - 1)
        if state.current() > max_index:
            state.move_to(max_index)

    def _refresh_screen_display(self) -> None:
        """Fetch and render the isolated schedule for the active (semester, moed).

        Uses service.get_period_schedule(period_id, local_index) which reads
        directly from the period's own file (disk mode) or from the in-memory
        per-period cache (legacy mode).  No Cartesian-product mixing occurs.
        """
        # Guard: if "All Sessions" is active, delegate to the dedicated method.
        if self._edit_schedule_mode:
            self._pending_refresh_while_editing = True
            return

        if self._current_moed == "All":
            self._refresh_all_sessions_display()
            return

        self._clamp_active_index_to_valid_range()

        sem  = self._current_semester
        moed = self._current_moed
        pid  = self._active_period_id()
        idx = self._active_window_state().current()

        # ג”€ג”€ Fetch isolated period schedule ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
        try:
            exams = self.service.get_period_schedule(pid, idx)
        except Exception as exc:
            print(f"OutputScreen: get_period_schedule({pid}, {idx}) failed: {exc}")
            exams = []

        # ג”€ג”€ Resolve period date range ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
        start_date: _date | None = None
        end_date:   _date | None = None
        forbidden:  list | None = None
        period_found = False
        try:
            for p in self.service.get_periods():
                if p.get("id") == pid:
                    period_found = True
                    start_date = _to_date(p.get("start_date"))
                    end_date   = _to_date(p.get("end_date"))
                    forbidden  = p.get("forbidden_days", [])
                    break
        except Exception:
            period_found = True   # service failed ג†’ assume period exists

        # ג”€ג”€ Period not configured ג†’ styled warning ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
        if not period_found:
            self.four_month.show_no_period(sem, moed)
            self._update_navigator()
            return

        # ג”€ג”€ Update calendar card ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
        if exams:
            self._empty_timer.stop()
            self._loading_timer.stop()
            self._sync_active_counter_state()
            self._calendar_displaying_data = True
            # Capture the baseline the first time this period shows data, so the
            # poll timer can later detect newly generated schedules.
            if self._ranked_baseline == 0:
                self._ranked_baseline = self._active_period_count()
            self.four_month.update_schedule(
                exams,
                unavailable_dates=forbidden,
                semester=sem,
                start_date=start_date,
                end_date=end_date,
            )
            if self._check_conflicts_next:
                self._check_conflicts_next = False
                self._check_cross_moed_conflicts(sem, moed, exams)
        else:
            # Only show "no schedules" if we are certain there are none.
            # If count > 0 the data simply isn't ready yet ג€” keep loading.
            self._calendar_displaying_data = False
            try:
                still_generating = bool(self.service.is_period_generating(pid))
            except Exception:
                still_generating = False
            try:
                period_count = self.service.get_schedule_count(period_id=pid)
            except Exception:
                period_count = 0
            if still_generating or (isinstance(period_count, int) and period_count > 0):
                self._empty_timer.stop()
                self._loading_semester = sem
                if not self._loading_timer.isActive():
                    self._loading_timer.start()
            else:
                # The period is not generating and no schedules exist, so show
                # the empty state immediately instead of making the user wait.
                self._loading_timer.stop()
                self._empty_timer.stop()
                self._empty_semester = sem
                self.four_month.show_empty(sem)

        self._update_navigator()

    def _current_visible_rows_snapshot(self) -> tuple[list[dict], _date | None, _date | None]:
        """Return the currently displayed schedule rows and active period range."""
        pid = self._active_period_id()
        idx = self._active_window_state().current()

        try:
            rows = self.service.get_period_schedule(pid, idx) or []
        except Exception:
            rows = []

        start_date = None
        end_date = None

        try:
            for p in self.service.get_periods():
                if p.get("id") == pid:
                    start_date = _to_date(p.get("start_date"))
                    end_date = _to_date(p.get("end_date"))
                    break
        except Exception:
            pass

        return rows, start_date, end_date

    def _on_loading_timeout(self) -> None:
        """Called 2 s after generation started ג€” show the loading state if still no data."""
        if not self._calendar_displaying_data:
            self.four_month.show_loading(self._loading_semester)

    def _on_empty_timeout(self) -> None:
        """Called 2 s after we first detected no data ג€” show the empty state."""
        if not self._calendar_displaying_data:
            self.four_month.show_empty(self._empty_semester)

    # ג”€ג”€ Cross-moed conflict detection ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    _MOED_LABEL: dict[str, str] = {"Aleph": "A", "Bet": "B", "Gimel": "C"}
    _ALL_MOEDS = ["Aleph", "Bet", "Gimel"]

    def _check_cross_moed_conflicts(
        self, semester: str, current_moed: str, current_exams: list[dict]
    ) -> None:
        """Warn the user when an exam in the current schedule shares course+date
        with the same course in another moed of the same semester."""
        sem_code = _SEMESTER_TO_ID.get(semester, semester)

        # Build (course_id, date_str) ג†’ course_name map for the current schedule.
        current_pairs: dict[tuple, str] = {}
        for e in current_exams:
            cid  = str(e.get("course_number", ""))
            date = str(e.get("exam_date", ""))
            name = str(e.get("course_name", cid))
            if cid and date:
                current_pairs[(cid, date)] = name

        conflicts: list[str] = []

        for other_moed in self._ALL_MOEDS:
            if other_moed == current_moed:
                continue
            other_pid = f"{sem_code}_{other_moed}"
            other_idx = self._period_index(other_pid)
            try:
                other_exams = self.service.get_period_schedule(other_pid, other_idx)
            except Exception:
                continue

            for e in other_exams:
                cid  = str(e.get("course_number", ""))
                date = str(e.get("exam_date", ""))
                if (cid, date) in current_pairs:
                    label       = self._MOED_LABEL.get(other_moed, other_moed)
                    course_name = current_pairs[(cid, date)]
                    conflicts.append(
                        f"Scheduling Conflict: '{course_name}' ({cid}) is scheduled"
                        f" on the same date ({date}) in Moed {label}."
                    )

        if conflicts:
            self._show_conflict_banner("\n".join(conflicts))

    # ג”€ג”€ Per-period navigator ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    def _on_navigator_index_changed(self, index: int) -> None:
        """Advance ONLY the active period ג€” other periods stay unchanged.

        The new isolated architecture stores a local index per period and
        fetches that period's schedule directly via get_period_schedule().
        No Cartesian-product scanning or cross-period interference.
        """
        if self._edit_schedule_mode:
            return
        pid = self._active_period_id()
        state = self._active_window_state()
        state.move_to(index)

        self._sync_active_counter_state()
        self._hide_conflict_banner()
        self._check_conflicts_next = True
        self._refresh_screen_display()

    def _on_refresh_pending_clicked(self) -> None:
        """Accept pending optimized results and refresh the current display."""
        if self._edit_schedule_mode:
            self._pending_refresh_while_editing = True
            return
        state = self._active_window_state()
        state.accept_pending()
        # A manual refresh means the user wants to see the best/current top
        # result from the updated data, so restart this period's navigation at 0.
        state.clear()
        self._sync_active_counter_state()

        self._hide_sorting_update_banner()
        # The view now reflects every schedule generated so far ג€” move the
        # baseline up so the banner only reappears when newer ones arrive.
        self._ranked_baseline = self._active_period_count()
        # Re-baseline the best score too, so EP-150 only re-fires on a future
        # improvement beyond what the user just accepted.
        self._best_seen.pop(self._active_period_id(), None)
        # Re-query scores.db so the refreshed view uses the latest ranked order.
        self.service.refresh_ranked_view()
        self._refresh_screen_display()

    def _on_prefetch_needed(self, _loaded_so_far: int) -> None:
        # No-op in isolated mode ג€” each NEXT fetches on demand.
        pass

    def _check_better_solution(self, period_id: str) -> None:
        """EP-150: pop the banner when the best-ranked schedule improves.

        Asks the service for the rank-1 value of the active primary sort column.
        Because that optimum only moves toward "better" as more schedules are
        scored, any change from the previously seen value means a strictly better
        schedule was found. The first observation only records a baseline so we
        never notify on the very first poll.
        """
        best = self.service.get_best_score(period_id)
        if best is None:
            return
        previous = self._best_seen.get(period_id)
        self._best_seen[period_id] = best
        if previous is not None and best != previous:
            self._show_sorting_update_banner("A better schedule was found.")

    def _update_navigator(self) -> None:
        """Push the active period's local index and exact per-period total.

        When the period has no schedules (total == 0) the navigator shows
        "ג€” of ג€”" and both NEXT and PREV are disabled automatically by
        ScheduleNavigatorWidget.set_state(total=0).

        Guard: in "All Sessions" mode the navigator is always hidden and
        must not be touched ג€” the overview panel replaces it.
        """
        if self._current_moed == "All":
            return

        pid         = self._active_period_id()
        current_idx = self._period_index(pid)

        # get_schedule_count(period_id) is authoritative: 0 = no schedules.
        # Do NOT fall back to _global_total here ג€” a period may genuinely have
        # zero schedules while another period has many.
        try:
            total = self.service.get_schedule_count(period_id=pid)
            if not isinstance(total, int) or total < 0:
                total = 0
        except Exception:
            total = 0

        self._sync_active_counter_state()

        # Hide the entire navigator bar (counter + Prev/Next) when there are
        # no schedules for this period ג€” show it again as soon as data arrives.
        self.navigator.setVisible(total > 0)
        self.navigator.set_state(current=current_idx, total=total, loaded=total)

    # ג”€ג”€ Polling ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    def _poll_schedule_count(self) -> None:
        """Refresh total/display every POLL_INTERVAL_MS.

        Checks whether per-period data has arrived since the last poll.
        When data first appears, re-renders so the loading indicator clears.

        Guard: in "All Sessions" mode no polling is needed ג€” the view is
        read-only and contains no live navigation counter.
        """
        if self._current_moed == "All":
            return

        pid = self._active_period_id()

        try:
            count = self.service.get_schedule_count(period_id=pid)
            if isinstance(count, int) and count > 0:
                self._sync_active_counter_state()
                if not self._calendar_displaying_data:
                    if self._edit_schedule_mode:
                        self._pending_refresh_while_editing = True
                        return
                    # Calendar is showing empty/loading but data is available ג€”
                    # re-render immediately so the first schedule appears.
                    self.semester_tabs.set_enabled_all(True)
                    self._refresh_screen_display()
                    return
                # Already showing data ג€” re-evaluate the current schedule when
                # new scored results arrive for the active sort, then raise the
                # banner only when a strictly better top-ranked schedule has arrived.
                if self.service.get_sort_order():
                    self._ranked_baseline = max(self._ranked_baseline, count)
        except Exception:
            pass

        self._update_navigator()

    # ג”€ג”€ Edit Schedule mode ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    def is_editing(self) -> bool:
        """Return True when edit-schedule mode is active."""
        return self._edit_schedule_mode

    def _on_edit_schedule_toggled(self, checked: bool) -> None:
        if checked:
            self.enter_edit_mode()
        else:
            # Button un-toggled manually ג€” treat as cancel
            self._on_cancel_edit_clicked()

    # ג”€ג”€ Enter / exit edit mode ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    def enter_edit_mode(self) -> None:
        if self._edit_schedule_mode:
            return

        pid = self._active_period_id()
        idx = self._active_window_state().current()
        try:
            rows = self.service.get_period_schedule(pid, idx) or []
        except Exception:
            rows = []

        start_date = end_date = None
        forbidden: set = set()
        try:
            for p in self.service.get_periods():
                if p.get("id") == pid:
                    start_date = _to_date(p.get("start_date"))
                    end_date   = _to_date(p.get("end_date"))
                    forbidden  = {_to_date(d) for d in p.get("forbidden_days", [])}
                    break
        except Exception:
            pass

        self._original_edit_rows  = deepcopy(rows)
        self._editable_rows       = deepcopy(rows)
        self._edit_period_start   = start_date
        self._edit_period_end     = end_date
        self._edit_forbidden_days = forbidden
        self._edit_schedule_mode  = True
        self._pending_refresh_while_editing = False
        self._apply_edit_mode_ui()

    def exit_edit_mode(self) -> None:
        if not self._edit_schedule_mode and not getattr(self, "_edit_mode", False):
            return
        self._edit_error_banner.hide_error()
        self._edit_schedule_mode = False
        self._edit_mode = False
        self._original_edit_rows = None
        self._editable_rows      = []
        if self._edit_dialog is not None:
            self._edit_dialog.close()
            self._edit_dialog = None
        self._apply_edit_mode_ui()
        if self._pending_refresh_while_editing:
            self._pending_refresh_while_editing = False
            self._refresh_screen_display()

    def _apply_edit_mode_ui(self) -> None:
        legacy_editing = bool(getattr(self, "_edit_mode", False))
        if legacy_editing and not self._edit_schedule_mode:
            self._edit_schedule_mode = True
        editing = self._edit_schedule_mode
        self._edit_mode = editing
        self.edit_schedule_btn.setChecked(editing)
        self.edit_schedule_btn.setText("Exit Edit Mode" if editing else "Edit Schedule")
        self.edit_schedule_btn.setStyleSheet(
            "QPushButton { background: #FEF2F2; color: #DC2626;"
            " border: 1.5px solid #FECACA; border-radius: 8px;"
            " padding: 6px 14px; font-weight: 600; }"
            if editing else ""
        )
        self._edit_mode_banner.setVisible(editing)
        self.navigator.setEnabled(not editing)
        self.sort_settings_btn.setEnabled(not editing)
        self.download_btn.setEnabled(not editing)
        self.four_month.set_edit_mode(editing)

    def _render_edit_rows(self) -> None:
        """Re-render the calendar from the pending editable rows without
        resetting the current month view."""
        self.four_month.update_schedule(
            self._editable_rows,
            semester=self._current_semester,
            start_date=self._edit_period_start,
            end_date=self._edit_period_end,
            preserve_month_index=True,
        )
        # Re-apply edit mode on newly created cells
        self.four_month.set_edit_mode(True)

    # ג”€ג”€ SAVE / CANCEL ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    def _schedule_post_refresh(self) -> None:
        """Refresh the visible schedule on the next UI cycle.

        This helps when sorting or a save-jump depends on the latest ranking
        data being committed to scores.db and visible to the service.
        """
        if not self._post_refresh_timer.isActive():
            self._post_refresh_timer.start()

    def _on_save_edit_clicked(self) -> None:
        """Apply all pending drag moves to disk, then exit edit mode."""
        if not self._original_edit_rows:
            self.exit_edit_mode()
            return

        # Find rows whose date, slot, or room assignment changed.
        original_by_id = {str(r.get("course_number", "")): r
                          for r in self._original_edit_rows}
        moved = [
            r for r in self._editable_rows
            if self._edit_row_changed(
                r,
                original_by_id.get(str(r.get("course_number", "")), {}),
            )
        ]

        if not moved:
            self.exit_edit_mode()
            return

        pid = self._active_period_id()
        idx = self._active_window_state().current()

        original_by_id = {
            str(r.get("course_number", "")): r for r in self._original_edit_rows
        }
        for row in moved:
            original = original_by_id.get(str(row.get("course_number", "")), row)
            errors = self._validate_drag_date(original, _to_date(row.get("exam_date")))
            if errors:
                self._edit_error_banner.show_error("\n".join(errors))
                return

        self.save_edit_btn.setEnabled(False)
        self.save_edit_btn.setText("Saving...")

        self._save_remaining = list(moved)
        self._save_error: str | None = None
        self._pid_for_save = pid
        self._idx_for_save = idx
        self._run_next_save()

    def _run_next_save(self) -> None:
        from src.presenter.save_edit_worker import SaveEditWorker

        if self._save_error or not self._save_remaining:
            self.save_edit_btn.setEnabled(True)
            self.save_edit_btn.setText("SAVE")
            if self._save_error:
                self._edit_error_banner.show_error(self._save_error)
            else:
                new_rank = self.service.rank_of_last_saved_edit(self._pid_for_save)
                self.exit_edit_mode()
                window = self._window_states.get(self._pid_for_save)
                if window is not None and new_rank is not None:
                    window.move_to(new_rank)
                self._schedule_post_refresh()
            return

        row = self._save_remaining.pop(0)
        self._save_worker = SaveEditWorker(
            service       = self.service,
            period_id     = self._pid_for_save,
            index         = self._idx_for_save,
            course_number = str(row.get("course_number", "")),
            new_date      = _to_date(row.get("exam_date")),
            new_time_slot = row.get("time_slot"),
            new_room_keys = list(row.get("room_ids") or []),
            parent        = self,
        )
        self._save_worker.finished.connect(self._run_next_save)
        self._save_worker.error.connect(self._on_save_error)
        self._save_worker.start()

    @staticmethod
    def _edit_row_changed(row: dict, original: dict) -> bool:
        if not original:
            return True
        return (
            str(row.get("exam_date", "")) != str(original.get("exam_date", ""))
            or str(row.get("time_slot", "")) != str(original.get("time_slot", ""))
            or list(row.get("room_ids") or []) != list(original.get("room_ids") or [])
        )

    def _on_save_error(self, msg: str) -> None:
        self._save_error = msg
        self._save_remaining.clear()
        self._run_next_save()

    def _on_cancel_edit_clicked(self) -> None:
        self._edit_error_banner.hide_error()
        if self._original_edit_rows is not None:
            self._editable_rows = deepcopy(self._original_edit_rows)
            self._render_edit_rows()
        self.exit_edit_mode()
        self._refresh_screen_display()

    def _on_edit_exam_clicked(self, exam: dict, anchor) -> None:
        """Open EditExamDialog alongside the day-list panel (which stays open)."""
        if self._edit_dialog is not None:
            self._edit_dialog.close()
            self._edit_dialog = None
        # Day-list dialog intentionally NOT closed ג€” user keeps seeing all exams.

        period_id = self._active_period_id()
        index     = self._active_window_state().current()

        self._edit_dialog = EditExamDialog(
            exam           = exam,
            period_id      = period_id,
            schedule_index = index,
            service        = self.service,
            program_names  = self._get_program_names(),
            anchor_pos     = None,
            parent         = self,
        )
        self._edit_dialog.exam_saved.connect(self._on_exam_edit_saved)
        self._edit_dialog.finished.connect(lambda: setattr(self, "_edit_dialog", None))
        self._edit_dialog.show()
        # Reposition both dialogs side-by-side centered after both are rendered.
        QTimer.singleShot(20, self._reposition_dialogs_side_by_side)

    def _on_exam_drag_moved(self, exam: dict, source_date: str, target_date: str) -> None:
        """Validate and stage a drag move ג€” changes are NOT written to disk yet."""
        if not self._edit_schedule_mode:
            return

        try:
            new_date = _date.fromisoformat(target_date)
        except ValueError:
            return

        # Validate date against period bounds
        errors = self._validate_drag_date(exam, new_date)
        if errors:
            self._edit_error_banner.show_error(errors[0])
            return

        # Apply the move to _editable_rows (in-memory only)
        course_number = str(exam.get("course_number", ""))
        for row in self._editable_rows:
            if str(row.get("course_number", "")) == course_number:
                row["exam_date"] = new_date
                break

        self._edit_error_banner.hide_error()
        self._render_edit_rows()

    def _on_exam_moved(self, exam: dict, source_date: str, target_date: str) -> None:
        """Backward-compatible alias for older edit-mode tests and callers."""
        self._on_exam_drag_moved(exam, source_date, target_date)

    @staticmethod
    def _format_move_errors(course_name: str, errors: list[dict]) -> str:
        """Format manual-move validation errors for the inline edit banner."""
        return "\n".join(
            f"{course_name}: {e.get('reason', str(e))}" for e in errors
        )

    def _validate_drag_date(self, exam: dict, target_date: _date) -> list[str]:
        """Return human-readable error strings for an invalid drag target.

        Delegates to service.validate_manual_move so the same rules
        (period bounds, forbidden days, program collisions) apply both
        for drags and for the EditExamDialog date picker.
        """
        pid = self._active_period_id()
        try:
            errors = self.service.validate_manual_move(
                pid, self._editable_rows, exam, target_date
            )
            course_name = str(exam.get("course_name") or exam.get("course_number", ""))
            formatted = self._format_move_errors(course_name, errors)
            return [line for line in formatted.splitlines() if line.strip()]
        except Exception:
            return []

    def _build_edit_mode_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("editModeBanner")
        banner.setStyleSheet("""
            QFrame#editModeBanner {
                background: #FFFBEB;
                border: 1.5px solid #FBBF24;
                border-radius: 10px;
            }
        """)
        row = QHBoxLayout(banner)
        row.setContentsMargins(16, 10, 16, 10)
        row.setSpacing(12)

        lbl = QLabel("Edit mode is active. Drag exams or click Edit on a day to reschedule.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #92400E; font-size: 13px; font-weight: 600; background: transparent;")
        row.addWidget(lbl, stretch=1)

        self.save_edit_btn = QPushButton("SAVE")
        self.save_edit_btn.setObjectName("saveEditBtn")
        self.save_edit_btn.setStyleSheet(
            "QPushButton { background: #4338CA; color: #FFF; border: none;"
            " border-radius: 8px; padding: 6px 20px; font-weight: 700; }"
            " QPushButton:hover { background: #3730A3; }"
            " QPushButton:disabled { background: #C7D2FE; }"
        )
        self.save_edit_btn.clicked.connect(self._on_save_edit_clicked)
        row.addWidget(self.save_edit_btn)

        self.cancel_edit_btn = QPushButton("CANCEL")
        self.cancel_edit_btn.setObjectName("cancelEditBtn")
        self.cancel_edit_btn.setStyleSheet(
            "QPushButton { background: #FFF; color: #475569; border: 1.5px solid #CBD5E1;"
            " border-radius: 8px; padding: 6px 16px; font-weight: 600; }"
            " QPushButton:hover { background: #F8FAFC; }"
        )
        self.cancel_edit_btn.clicked.connect(self._on_cancel_edit_clicked)
        row.addWidget(self.cancel_edit_btn)

        return banner

    def _reposition_dialogs_side_by_side(self) -> None:
        """Place DayDetailDialog and EditExamDialog adjacent and centered together."""
        from PyQt5.QtWidgets import QApplication as _QApp
        day  = self._day_dialog
        edit = self._edit_dialog
        if day is None or edit is None:
            return
        if not day.isVisible() or not edit.isVisible():
            return

        screen = _QApp.primaryScreen().availableGeometry()
        gap    = 12  # px between the two panels

        dw = day.width()
        ew = edit.width()
        total_w = dw + gap + ew

        # Horizontal: center the pair together
        start_x = screen.left() + (screen.width() - total_w) // 2
        start_x = max(screen.left(), start_x)

        # Vertical: center each independently (they may have different heights)
        day_y  = screen.top() + (screen.height() - day.height())  // 2
        edit_y = screen.top() + (screen.height() - edit.height()) // 2

        day.move(start_x, max(screen.top(), day_y))
        edit.move(start_x + dw + gap, max(screen.top(), edit_y))

    def _on_exam_edit_saved(self, updated_exam: dict) -> None:
        """Called when the user saves changes in EditExamDialog."""
        # Propagate the dialog change into _editable_rows only. Disk persistence
        # happens later when the user clicks the main edit-mode SAVE button.
        course_number = str(updated_exam.get("course_number", ""))
        for row in self._editable_rows:
            if str(row.get("course_number", "")) == course_number:
                row.update(updated_exam)
                break
        self._render_edit_rows()

    # ג”€ג”€ Exam cell click ג†’ DayDetailDialog (or EditExamDialog in edit mode) ג”€ג”€ג”€ג”€

    def _on_exam_day_clicked(self, exams: list, anchor) -> None:
        if not exams:
            return

        # In Edit Schedule mode: show all exams for the day with an Edit button
        # per exam so the user can pick which one to edit.
        if self._edit_schedule_mode:
            if self._day_dialog is not None:
                self._day_dialog.close()
                self._day_dialog = None
            program_names = self._get_program_names()
            exam_date     = exams[0].get("exam_date")
            self._day_dialog = DayDetailDialog(
                exams         = exams,
                exam_date     = exam_date,
                program_names = program_names,
                anchor_pos    = None,   # centered by _center_on_screen()
                edit_mode     = True,
                parent        = self,
            )
            self._day_dialog.edit_requested.connect(
                lambda exam: self._on_edit_exam_clicked(exam, anchor)
            )
            self._day_dialog.finished.connect(lambda: setattr(self, "_day_dialog", None))
            self._day_dialog.show()
            return

        # Normal view mode: show the read-only DayDetailDialog
        if self._day_dialog is not None:
            self._day_dialog.close()
            self._day_dialog = None

        program_names = self._get_program_names()
        exam_date     = exams[0].get("exam_date")
        self._day_dialog = DayDetailDialog(
            exams         = exams,
            exam_date     = exam_date,
            program_names = program_names,
            anchor_pos    = None,   # always centered
            parent        = self,
        )
        self._day_dialog.finished.connect(lambda: setattr(self, "_day_dialog", None))
        self._day_dialog.show()

    def _on_exam_clicked(self, exam_data: dict) -> None:
        """Backward-compat shim."""
        self._on_exam_day_clicked([exam_data], anchor=None)

    def _get_program_names(self) -> dict:
        try:
            return {p["id"]: p["name"] for p in self.service.get_available_programs()}
        except Exception:
            return {}

    # ג”€ג”€ EngineListener integration ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    _PERIOD_PREFIX_TO_TAB: dict[str, str] = {
        "FALL": "FALL",
        "SPRI": "SPRING",
        "SUMM": "SUMMER",
    }

    def connect_listener(self, listener) -> None:
        listener.period_ready.connect(self._on_period_ready)
        listener.finished.connect(self._on_generation_finished)
        listener.error.connect(self._on_generation_error)

    def _on_period_ready(self, period_id: str) -> None:
        """Called once per exam period when the engine finishes generating it.

        Disk mode:   data is immediately readable via get_period_schedule().
        Legacy mode: _results_by_period[period_id] is populated at this point,
                     so get_period_schedule() can serve it right away.
        """
        # If the calendar is still empty, jump to whatever period just got data.
        if not self._calendar_displaying_data:
            self._jump_to_period(period_id)

        prefix = period_id.split("_")[0].upper()
        tab    = self._PERIOD_PREFIX_TO_TAB.get(prefix, "FALL")
        if tab != self._current_semester:
            return

        # Check whether this period matches the active tab
        if period_id != self._active_period_id():
            return

        if self._edit_schedule_mode:
            self._pending_refresh_while_editing = True
            return

        if self._calendar_displaying_data:
            state = self._active_window_state()
            state.mark_pending()
            if self.service.get_sort_order():
                self._check_better_solution(period_id)
            return

        # Data just arrived for the currently-visible period ג€” update count and render.
        try:
            count = self.service.get_schedule_count(period_id=period_id)
            if isinstance(count, int) and count > 0:
                self._sync_active_counter_state()
                self._refresh_screen_display()
        except Exception:
            pass

    def _on_generation_finished(self, total: int) -> None:
        """Called when generation is fully complete ג€” all period data available.

        Re-enables tabs, updates the total, resets indices to 0, and renders
        the first schedule for the currently visible period.
        """
        if self._edit_schedule_mode:
            self._pending_refresh_while_editing = True
            return
        self.semester_tabs.set_enabled_all(True)
        # Reset all WindowState objects and render schedule 0 for the active period.
        
        for state in self._window_states.values():
            state.clear()
        self._hide_sorting_update_banner()
        self._active_window_state().clear()
        self._sync_active_counter_state()
        self._refresh_screen_display()

    def _on_generation_error(self, message: str) -> None:
        self._generation_error_banner.show_error(message)
        if self._edit_schedule_mode:
            self._pending_refresh_while_editing = True
            return
        self.semester_tabs.set_enabled_all(True)

    # ג”€ג”€ Helpers ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

    @staticmethod
    def _to_date(value) -> "_date":
        if isinstance(value, _date):
            return value
        return _date.fromisoformat(str(value))



    def on_sort_changed(self, sort_cols: list = None) -> None:
        """Reset all period navigation states to 0 when the sort order changes."""
        if self._edit_schedule_mode:
            self._pending_refresh_while_editing = True
            return
        selected = list(sort_cols or [])
        try:
            self.service.set_sort_order(selected)
            self.service.refresh_ranked_view()
        except Exception:
            pass
        for state in self._window_states.values():
            state.clear()
        self._sync_active_counter_state()
        self._hide_sorting_update_banner()
        self._ranked_baseline = 0   # the new sort defines a fresh baseline
        self._best_seen.clear()
        self._schedule_post_refresh()
        self._refresh_screen_display()

    def _on_back_clicked(self) -> None:
        if self._day_dialog is not None:
            self._day_dialog.close()
            self._day_dialog = None

        if self._edit_schedule_mode:
            QMessageBox.warning(
                self,
                "Edit Mode Active",
                "Please save or cancel editing before leaving the output screen.",
            )
            return

        self.switch_to_input.emit()

    def _on_download_clicked(self) -> None:
        """Export the currently displayed per-period schedules into one combined file.

        Uses export_by_period_indices() which reads each period at its local
        index ג€” exactly what is shown on screen ג€” and merges them into a single
        human-readable report.
        """
        # Check that at least one period has data.
        has_data = any(
            self.service.get_schedule_count(period_id=pid) > 0
            for pid in self._window_states
        )
        if not has_data:
            QMessageBox.warning(self, "No Schedule", "No schedule is currently loaded.")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Schedule", "",
            "Text Files (*.txt);;PDF Files (*.pdf);;CSV Files (*.csv);;All Files (*)",
            options=options,
        )
        if not file_path:
            return

        try:
            self.service.export_by_period_indices(self._current_export_indices(), file_path)
            self._show_success_banner("Schedule exported successfully.")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed", f"Could not export schedule:\n{exc}"
            )



