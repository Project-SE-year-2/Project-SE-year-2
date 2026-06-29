from __future__ import annotations

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
from src.views.output_screen.moed_calendar_output_widget import MoedCalendarOutputWidget
from src.views.output_screen.semester_tabs_widget import SemesterTabsWidget
from src.views.settings_screen.ranking_config_widget import RankingConfigDialog
from src.views.shared_components.calendar_table_widget import CalendarTableWidget
from src.styles.output_screen_style import OUTPUT_SCREEN_STYLE
from src.views.output_screen.window_state import WindowState


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
    POLL_INTERVAL_MS = 150

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service

        # ── Shared global counter (for legacy compat properties) ──────────────
        self._global_index: int = 0
        self._global_total: int = 0

        # ── Per-period window states ─────────────────────────────────────────────
        self._window_states: dict[str, WindowState] = {
            f"{sem.value}_{moed.value}": WindowState()
            for sem in Semester
            for moed in Moed
        }

        # ── Active view ───────────────────────────────────────────────────────
        self._current_semester: str = "FALL"
        self._current_moed:     str = "Aleph"
        self._check_conflicts_next: bool = False
        self._day_dialog: DayDetailDialog | None = None
        self._calendar_displaying_data: bool = False

        # EP-149 / EP-150 Baseline state
        self._ranked_baseline: int = 0
        self._best_seen: dict[str, float] = {}

        # Delayed timers
        self._empty_timer = QTimer(self)
        self._empty_timer.setSingleShot(True)
        self._empty_timer.setInterval(2000)
        self._empty_semester: str = ""

        self._loading_timer = QTimer(self)
        self._loading_timer.setSingleShot(True)
        self._loading_timer.setInterval(2000)
        self._loading_semester: str = ""

        self._setup_ui()
        self._setup_polling()
        self._empty_timer.timeout.connect(self._on_empty_timeout)
        self._loading_timer.timeout.connect(self._on_loading_timeout)

    # ── Active period ID ──────────────────────────────────────────────────────

    def _active_period_id(self) -> str:
        sem_code = _SEMESTER_TO_ID.get(self._current_semester, self._current_semester)
        return f"{sem_code}_{self._current_moed}"

    def _active_period_count(self) -> int:
        try:
            c = self.service.get_schedule_count(period_id=self._active_period_id())
            return c if isinstance(c, int) and c > 0 else 0
        except Exception:
            return 0

    def _select_first_available_period(self) -> None:
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

    def _active_window_state(self) -> WindowState:
        pid = self._active_period_id()
        return self._window_states.setdefault(pid, WindowState())

    def _period_index(self, period_id: str) -> int:
        return self._window_states.setdefault(period_id, WindowState()).current()

    def _current_export_indices(self) -> dict[str, int]:
        return {
            pid: state.current()
            for pid, state in self._window_states.items()
        }

    # ── Backward-compat properties ────────────────────────────────────────────

    @property
    def current_index(self) -> int:
        return self._global_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        self._global_index = value

    @property
    def current_schedules(self) -> list:
        return []

    @current_schedules.setter
    def current_schedules(self, value: list) -> None:
        pass

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

        # Toolbar layout
        toolbar = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
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

        # --- Edit Mode Buttons (EP-160 Requirements) ---
        self.edit_btn = QPushButton("EDIT")
        self.edit_btn.setObjectName("editBtn")
        self.edit_btn.clicked.connect(self._on_edit_clicked)

        self.save_btn = QPushButton("SAVE")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self._on_save_clicked)

        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)

        # Hide Save/Cancel by default
        self.save_btn.setVisible(False)
        self.cancel_btn.setVisible(False)

        toolbar.addWidget(self.back_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.save_btn)
        toolbar.addWidget(self.cancel_btn)
        toolbar.addWidget(self.sort_settings_btn)
        toolbar.addWidget(self.download_btn)
        main_layout.addLayout(toolbar)

        # Semester tabs
        self.semester_tabs = SemesterTabsWidget()
        self.semester_tabs.semester_changed.connect(self._on_semester_changed)
        main_layout.addWidget(self.semester_tabs)

        # Custom Visual Indicator / Edit Mode Status Banner
        self._edit_mode_banner = self._build_edit_mode_banner()
        self._edit_mode_banner.setVisible(False)
        main_layout.addWidget(self._edit_mode_banner)

        # Conflict banner
        self._conflict_banner = self._build_conflict_banner()
        self._conflict_banner.setVisible(False)
        main_layout.addWidget(self._conflict_banner)

        # Success/Update banners
        self._success_banner = self._build_success_banner()
        self._success_banner.setVisible(False)
        main_layout.addWidget(self._success_banner)
        
        self._sorting_update_banner = self._build_sorting_update_banner()
        self._sorting_update_banner.setVisible(False)
        main_layout.addWidget(self._sorting_update_banner)
        
        self._success_timer = QTimer(self)
        self._success_timer.setSingleShot(True)
        self._success_timer.timeout.connect(lambda: self._success_banner.setVisible(False))

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(16)

        # MoedCalendarOutputWidget
        self.four_month = MoedCalendarOutputWidget()
        self.four_month.exam_day_clicked.connect(self._on_exam_day_clicked)
        self.four_month.moed_changed.connect(self._on_moed_changed)

        self._sort_dialog = RankingConfigDialog(self)
        self.ranking_panel = self._sort_dialog.ranking_widget

        body_layout.addWidget(self.four_month, stretch=1)
        main_layout.addLayout(body_layout, stretch=1)

        self.navigator   = self.four_month.navigator
        self.navigator.navigate_to.connect(self._on_navigator_index_changed)
        self.navigator.prefetch_needed.connect(self._on_prefetch_needed)
        self.sched_label = self.navigator._counter_lbl

        self._scroll.setWidget(content)
        root.addWidget(self._scroll)

        self.calendar = CalendarTableWidget()
        self.calendar.exams_day_clicked.connect(self._on_exam_day_clicked)

    def _show_sort_settings(self):
        self._sort_dialog.exec_()

    # ── Edit Mode Actions & Synchronisation ────────────────────────────────────

    def _build_edit_mode_banner(self) -> QFrame:
        """Builds a clear, styled visual notification that edit mode is active."""
        banner = QFrame()
        banner.setObjectName("editModeBanner")
        banner.setStyleSheet("""
            QFrame#editModeBanner {
                background: #FFFBEB;
                border: 1.5px solid #FDE68A;
                border-radius: 10px;
            }
        """)
        row = QHBoxLayout(banner)
        row.setContentsMargins(16, 12, 16, 12)
        
        lbl = QLabel("⚠️ MANUAL EDIT MODE ACTIVE — Click SAVE to commit or CANCEL to revert changes.")
        lbl.setStyleSheet("color: #B45309; font-size: 13px; font-weight: 700;")
        row.addWidget(lbl, stretch=1)
        return banner

    def _on_edit_clicked(self) -> None:
        if hasattr(self.service, "set_edit_mode"):
            self.service.set_edit_mode(True)
        self._sync_edit_mode_ui()

    def _on_save_clicked(self) -> None:
        if hasattr(self.service, "set_edit_mode"):
            self.service.set_edit_mode(False)
        self._sync_edit_mode_ui()
        self._show_success_banner("Schedule changes saved successfully.")

    def _on_cancel_clicked(self) -> None:
        if hasattr(self.service, "set_edit_mode"):
            self.service.set_edit_mode(False)
        self._sync_edit_mode_ui()
        self._refresh_screen_display()

    def _sync_edit_mode_ui(self) -> None:
        """Dynamically adjusts button states, tabs, and banners based on edit mode state."""
        # Defend against partial/legacy mocks missing the contract method
        if not hasattr(self.service, "is_edit_mode"):
            return

        try:
            is_editing = bool(self.service.is_edit_mode())
        except Exception:
            is_editing = False

        # Main Action Button Visibility
        self.edit_btn.setVisible(not is_editing)
        self.save_btn.setVisible(is_editing)
        self.cancel_btn.setVisible(is_editing)

        # Disable navigation elements and preference controls during manual alignment
        self.sort_settings_btn.setEnabled(not is_editing)
        self.download_btn.setEnabled(not is_editing)
        self.back_btn.setEnabled(not is_editing)
        self.semester_tabs.setEnabled(not is_editing)
        self.four_month.moed_tabs.setEnabled(not is_editing)

        # Visual Banner Toggle
        self._edit_mode_banner.setVisible(is_editing)
        
        # Hide any background optimization popups when starting to edit
        if is_editing:
            self._hide_sorting_update_banner()

        # Update Navigator Layout Visibility state
        self._update_navigator()

    # ── Specialized Layout Builders ──────────────────────────────────────────

    def _build_conflict_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("conflictBanner")
        banner.setStyleSheet("QFrame#conflictBanner { background: #FEF2F2; border: 1.5px solid #FECACA; border-radius: 10px; }")
        row = QHBoxLayout(banner)
        row.setContentsMargins(16, 12, 16, 12)
        icon = QLabel("")
        row.addWidget(icon)
        self._conflict_text = QLabel("")
        self._conflict_text.setWordWrap(True)
        self._conflict_text.setStyleSheet("color: #DC2626; font-size: 13px; font-weight: 700;")
        row.addWidget(self._conflict_text, stretch=1)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #DC2626; font-size: 15px; font-weight: 700; }")
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
        banner.setStyleSheet("QFrame#successBanner { background: #F0FDF4; border: 1.5px solid #BBF7D0; border-radius: 10px; }")
        row = QHBoxLayout(banner)
        row.setContentsMargins(16, 12, 16, 12)
        icon = QLabel("✓")
        icon.setStyleSheet("color: #16A34A; font-size: 18px; font-weight: 700;")
        row.addWidget(icon)
        self._success_text = QLabel("")
        self._success_text.setStyleSheet("color: #16A34A; font-size: 13px; font-weight: 700;")
        row.addWidget(self._success_text, stretch=1)
        return banner
    
    def _build_sorting_update_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("sortingUpdateBanner")
        banner.setStyleSheet("QFrame#sortingUpdateBanner { background: #EFF6FF; border: 1.5px solid #BFDBFE; border-radius: 10px; }")
        row = QHBoxLayout(banner)
        row.setContentsMargins(16, 12, 16, 12)
        self._sorting_update_label = QLabel("New optimized schedules are available.")
        self._sorting_update_label.setStyleSheet("color: #1D4ED8; font-size: 13px; font-weight: 700;")
        row.addWidget(self._sorting_update_label, stretch=1)
        refresh_btn = QPushButton("Refresh View")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("QPushButton { background: #2563EB; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: 700; }")
        refresh_btn.clicked.connect(self._on_refresh_pending_clicked)
        row.addWidget(refresh_btn)
        return banner

    def _show_success_banner(self, message: str) -> None:
        self._success_text.setText(message)
        self._success_banner.setVisible(True)
        self._success_timer.start(5000)

    def _show_sorting_update_banner(self, message: str | None = None) -> None:
        # Prevent presentation updates if the user is in manual editing state
        try:
            if hasattr(self.service, "is_edit_mode") and self.service.is_edit_mode():
                return
        except Exception:
            pass
        if message is not None:
            self._sorting_update_label.setText(message)
        self._sorting_update_banner.setVisible(True)

    def _hide_sorting_update_banner(self) -> None:
        self._sorting_update_banner.setVisible(False)

    def _setup_polling(self) -> None:
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_schedule_count)
        self.destroyed.connect(self.poll_timer.stop)

    # ── Qt events ─────────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._current_semester = "FALL"
        self._current_moed     = "Aleph"
        self.semester_tabs.set_selected("FALL")
        self.four_month.set_active_moed("Aleph")
        self._select_first_available_period()
        self._hide_conflict_banner()
        self._hide_sorting_update_banner()
        
        # Sync view to ensure edit mode state resets on initial layout entrance
        self._sync_edit_mode_ui()
        self._ranked_baseline = 0
        self._best_seen.clear()

        if self._global_total > 0:
            self._calendar_displaying_data = False
            self._refresh_screen_display()
            self.poll_timer.start(self.POLL_INTERVAL_MS)
            return

        self._global_index = 0
        for state in self._window_states.values():
            state.clear()
        self._calendar_displaying_data = False
        self.semester_tabs.set_enabled_all(False)
        self._loading_semester = self._current_semester
        if not self._loading_timer.isActive():
            self._loading_timer.start()

        pid = self._active_period_id()
        try:
            count = self.service.get_schedule_count(period_id=pid)
            if isinstance(count, int) and count > 0:
                self._global_total = count
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

    # ── Semester / moed switching ─────────────────────────────────────────────

    def _on_semester_changed(self, semester: str) -> None:
        self._current_semester = semester
        self._global_index = self._active_window_state().current()
        self._hide_conflict_banner()
        self._hide_sorting_update_banner()
        self._check_conflicts_next = True
        self._calendar_displaying_data = False
        self._ranked_baseline = 0
        self._best_seen.clear()
        self._refresh_screen_display()

    def _on_moed_changed(self, moed: str) -> None:
        self._current_moed = moed
        self._hide_conflict_banner()
        self._hide_sorting_update_banner()
        self._calendar_displaying_data = False

        if moed == "All":
            self._refresh_all_sessions_display()
            return

        self._global_index = self._active_window_state().current()
        self._check_conflicts_next = True
        self._ranked_baseline = 0
        self._best_seen.clear()
        self._refresh_screen_display()

    # ── Central display refresh ───────────────────────────────────────────────

    def _refresh_all_sessions_display(self) -> None:
        sem      = self._current_semester
        sem_code = _SEMESTER_TO_ID.get(sem, sem)
        sections: list[dict] = []

        for moed in ["Aleph", "Bet", "Gimel"]:
            pid  = f"{sem_code}_{moed}"
            idx = self._period_index(pid)
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

    def _refresh_screen_display(self) -> None:
        if self._current_moed == "All":
            self._refresh_all_sessions_display()
            return

        sem  = self._current_semester
        moed = self._current_moed
        pid  = self._active_period_id()
        idx = self._active_window_state().current()

        try:
            exams = self.service.get_period_schedule(pid, idx)
        except Exception as exc:
            print(f"OutputScreen: get_period_schedule({pid}, {idx}) failed: {exc}")
            exams = []

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
            period_found = True

        if not period_found:
            self.four_month.show_no_period(sem, moed)
            self._update_navigator()
            return

        if exams:
            self._empty_timer.stop()
            self._loading_timer.stop()
            self._global_total = max(self._global_total, 1)
            self._calendar_displaying_data = True
            if self._ranked_baseline == 0:
                self._ranked_baseline = self._active_period_count()
            self.four_month.update_schedule(
                exams,
                semester=sem,
                start_date=start_date,
                end_date=end_date,
            )
            if self._check_conflicts_next:
                self._check_conflicts_next = False
                self._check_cross_moed_conflicts(sem, moed, exams)
        else:
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
                self._empty_semester = sem
                if not self._empty_timer.isActive():
                    self._empty_timer.start()

        self._update_navigator()

    def _on_loading_timeout(self) -> None:
        if not self._calendar_displaying_data:
            self.four_month.show_loading(self._loading_semester)

    def _on_empty_timeout(self) -> None:
        if not self._calendar_displaying_data:
            self.four_month.show_empty(self._empty_semester)

    # ── Cross-moed conflict detection ─────────────────────────────────────────

    _MOED_LABEL: dict[str, str] = {"Aleph": "A", "Bet": "B", "Gimel": "C"}
    _ALL_MOEDS = ["Aleph", "Bet", "Gimel"]

    def _check_cross_moed_conflicts(
        self, semester: str, current_moed: str, current_exams: list[dict]
    ) -> None:
        sem_code = _SEMESTER_TO_ID.get(semester, semester)
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

    # ── Per-period navigator ──────────────────────────────────────────────────

    def _on_navigator_index_changed(self, index: int) -> None:
        try:
            if hasattr(self.service, "is_edit_mode") and self.service.is_edit_mode():
                return
        except Exception:
            pass
        pid = self._active_period_id()
        state = self._active_window_state()
        state.move_to(index)

        self._global_index = state.current()
        self._hide_conflict_banner()
        self._check_conflicts_next = True
        self._refresh_screen_display()

    def _on_refresh_pending_clicked(self) -> None:
        state = self._active_window_state()
        state.accept_pending()
        self._hide_sorting_update_banner()
        self._ranked_baseline = self._active_period_count()
        self._best_seen.pop(self._active_period_id(), None)
        if hasattr(self.service, "refresh_ranked_view"):
            self.service.refresh_ranked_view()
        self._refresh_screen_display()

    def _on_prefetch_needed(self, _loaded_so_far: int) -> None:
        pass

    def _check_better_solution(self, period_id: str) -> None:
        try:
            if hasattr(self.service, "is_edit_mode") and self.service.is_edit_mode():
                return
        except Exception:
            pass
        if not hasattr(self.service, "get_best_score"):
            return
        best = self.service.get_best_score(period_id)
        if best is None:
            return
        previous = self._best_seen.get(period_id)
        self._best_seen[period_id] = best
        if previous is not None and best != previous:
            self._show_sorting_update_banner("A better schedule was found.")

    def _update_navigator(self) -> None:
        if self._current_moed == "All":
            return

        pid         = self._active_period_id()
        current_idx = self._period_index(pid)

        try:
            total = self.service.get_schedule_count(period_id=pid)
            if not isinstance(total, int) or total < 0:
                total = 0
        except Exception:
            total = 0

        if total > 0:
            self._global_total = max(self._global_total, total)

        try:
            is_editing = bool(hasattr(self.service, "is_edit_mode") and self.service.is_edit_mode())
        except Exception:
            is_editing = False

        # Hide navigator counter completely if editing or no schedules exist
        self.navigator.setVisible(total > 0 and not is_editing)
        self.navigator.set_state(current=current_idx, total=total, loaded=total)

    # ── Polling ───────────────────────────────────────────────────────────────

    def _poll_schedule_count(self) -> None:
        if self._current_moed == "All":
            return

        try:
            if hasattr(self.service, "is_edit_mode") and self.service.is_edit_mode():
                return
        except Exception:
            pass

        pid = self._active_period_id()
        try:
            count = self.service.get_schedule_count(period_id=pid)
            if isinstance(count, int) and count > 0:
                self._global_total = max(self._global_total, count)
                if not self._calendar_displaying_data:
                    self.semester_tabs.set_enabled_all(True)
                    self._refresh_screen_display()
                    return
                if hasattr(self.service, "get_sort_order") and self.service.get_sort_order():
                    self._check_better_solution(pid)
                elif self._ranked_baseline > 0 and count > self._ranked_baseline:
                    self._show_sorting_update_banner()
        except Exception:
            pass

        self._update_navigator()

    # ── Exam cell click → DayDetailDialog ────────────────────────────────────

    def _on_exam_day_clicked(self, exams: list, anchor) -> None:
        if self._day_dialog is not None:
            self._day_dialog.close()
            self._day_dialog = None

        program_names = self._get_program_names()
        exam_date     = exams[0].get("exam_date") if exams else None
        self._day_dialog = DayDetailDialog(
            exams         = exams,
            exam_date     = exam_date,
            program_names = program_names,
            anchor_pos    = anchor,
            parent        = self,
        )
        self._day_dialog.finished.connect(lambda: setattr(self, "_day_dialog", None))
        self._day_dialog.show()

    def _on_exam_clicked(self, exam_data: dict) -> None:
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
        "SUMM": "SUMMER",
    }

    def connect_listener(self, listener) -> None:
        listener.period_ready.connect(self._on_period_ready)
        listener.finished.connect(self._on_generation_finished)
        listener.error.connect(self._on_generation_error)

    def _on_period_ready(self, period_id: str) -> None:
        try:
            if hasattr(self.service, "is_edit_mode") and self.service.is_edit_mode():
                return
        except Exception:
            pass

        prefix = period_id.split("_")[0].upper()
        tab    = self._PERIOD_PREFIX_TO_TAB.get(prefix, "FALL")
        if tab != self._current_semester:
            return

        if period_id != self._active_period_id():
            return

        if self._calendar_displaying_data:
            state = self._active_window_state()
            state.mark_pending()
            
            if hasattr(self.service, "get_sort_order") and self.service.get_sort_order():
                self._check_better_solution(period_id)
            else:
                self._show_sorting_update_banner()
            return

        try:
            count = self.service.get_schedule_count(period_id=period_id)
            if isinstance(count, int) and count > 0:
                self._global_total = max(self._global_total, count)
                self._refresh_screen_display()
        except Exception:
            pass

    def _on_generation_finished(self, total: int) -> None:
        try:
            if hasattr(self.service, "is_edit_mode") and self.service.is_edit_mode():
                return
        except Exception:
            pass

        self.semester_tabs.set_enabled_all(True)
        pid = self._active_period_id()
        real_total = total if isinstance(total, int) and total > 0 else 0
        try:
            count = self.service.get_schedule_count(period_id=pid)
            if isinstance(count, int) and count > 0:
                real_total = count
        except Exception:
            pass
        self._global_total = real_total

        for state in self._window_states.values():
            state.clear()
        self._hide_sorting_update_banner()
        self._global_index = 0
        self._refresh_screen_display()

    def _on_generation_error(self, message: str) -> None:
        self.four_month.show_error(message)
        self.semester_tabs.set_enabled_all(True)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def on_sort_changed(self, _sort_cols: list = None) -> None:
        for state in self._window_states.values():
            state.clear()
        self._global_index = 0
        self._hide_sorting_update_banner()
        self._ranked_baseline = 0
        self._best_seen.clear()
        self._refresh_screen_display()

    def _on_back_clicked(self) -> None:
        if self._day_dialog is not None:
            self._day_dialog.close()
            self._day_dialog = None
        self.switch_to_input.emit()

    def _on_download_clicked(self) -> None:
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
            if hasattr(self.service, "export_by_period_indices"):
                self.service.export_by_period_indices(self._current_export_indices(), file_path)
            self._show_success_banner("Schedule exported successfully.")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed", f"Could not export schedule:\n{exc}"
            )