from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QStackedWidget,
)

import src.styles.theme as th
from src.presenter.generate_worker import GenerateWorker
from src.styles.icons import load_pixmap, ICON_CALENDAR_PLUS
from src.styles.input_screen_style import INPUT_SCREEN_STYLE
from src.views.shared_components.error_banner import ErrorBanner
from src.views.shared_components.loading_spinner import LoadingSpinner
from src.views.widgets.file_loader_widget import FileLoaderWidget
from src.views.widgets.program_list_widget import ProgramListWidget
from src.views.widgets.period_list_widget import PeriodListWidget
from src.views.widgets.period_editor_widget import PeriodEditorWidget
from src.views.widgets.selected_programs_panel import SelectedProgramsPanel
from src.views.widgets.course_table_widget import CourseTableWidget
from src.views.input_screen.generate_button_state import GenerateButtonState

_SECTION_BADGE_SIZE      = 28    # diameter of the numbered circle badge
_GENERATE_BAR_HEIGHT     = 68    # fixed height of the bottom generate bar
_SELECTED_PANEL_MIN_HEIGHT = 120 # minimum height for the selected-programs chips area


class InputScreen(QWidget):
    """
    The main input screen where users select programs and trigger schedule generation.
    Handles UI state transitions for background processing.
    """
    switch_to_output = pyqtSignal()
    switch_to_settings = pyqtSignal()

    # Initializes the screen, stores the service dependency, and builds the UI.
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("inputScreen")
        self.service = service
        self._generate_state = GenerateButtonState()
        self.setStyleSheet(INPUT_SCREEN_STYLE)
        self._setup_ui()
        self._sync_generate_button_state()

    # Builds the two-column layout (Data Input | tabbed panel) and connects signals.
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(
            th.SPACING_LARGE, th.SPACING_LARGE, th.SPACING_LARGE, 0
        )
        root.setSpacing(0)

        # ── Create all child widgets ───────────────────────────────────────
        self.file_loader    = FileLoaderWidget(self.service)
        self.program_list   = ProgramListWidget(self.service)
        self.selected_panel = SelectedProgramsPanel(self.service)
        self.selected_panel.setFixedHeight(280)  # divider + title + up to three rows of chips
        self.course_table   = CourseTableWidget(self.service)
        self.period_list    = PeriodListWidget(self.service)
        self.period_editor  = PeriodEditorWidget(self.service)

        # ── Column 1: Data Input ───────────────────────────────────────────
        col1 = self._make_section(
            number=1,
            title="Data Input",
            widgets=[self.file_loader],
        )

        # ── Tab page 0: Study Programs ─────────────────────────────────────
        # Left stack: program list + selected-chips panel
        # Right:      course table
        programs_body = QWidget()
        programs_body_layout = QHBoxLayout(programs_body)
        programs_body_layout.setContentsMargins(0, 0, 0, 0)
        programs_body_layout.setSpacing(th.SPACING_LARGE)

        left_stack = QWidget()
        left_stack.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(left_stack)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(th.SPACING_SMALL)
        left_layout.addWidget(self.program_list, stretch=1)
        left_layout.addWidget(self.selected_panel)

        programs_body_layout.addWidget(left_stack,        stretch=2)
        programs_body_layout.addWidget(self.course_table, stretch=3)

        self.selected_panel.setVisible(False)
        self.program_list.setVisible(False)

        # ── Tab page 1: Exam Periods ───────────────────────────────────────
        # period_list on the LEFT, period_editor on the RIGHT (horizontal split)
        period_body = QWidget()
        period_body_layout = QHBoxLayout(period_body)
        period_body_layout.setContentsMargins(0, 0, 0, 0)
        period_body_layout.setSpacing(th.SPACING_MEDIUM)
        period_body_layout.addWidget(self.period_list, stretch=2)
        period_body_layout.addWidget(self.period_editor, stretch=3)
        self.period_list.setVisible(False)
        self.period_editor.setVisible(False)

        # ── Right panel: tab card ──────────────────────────────────────────
        right_panel = self._build_tab_panel(programs_body, period_body)

        # ── Assemble columns ───────────────────────────────────────────────
        columns = QHBoxLayout()
        columns.setSpacing(th.SPACING_MEDIUM)
        columns.addWidget(col1,        stretch=1)
        columns.addWidget(right_panel, stretch=3)
        root.addLayout(columns, stretch=1)

        # ── Bottom generate bar ────────────────────────────────────────────
        bar = QWidget()
        bar.setObjectName("generateBar")
        bar.setFixedHeight(_GENERATE_BAR_HEIGHT)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(th.SPACING_XL, 0, th.SPACING_XL, 0)

        self.generate_btn = QPushButton("  Generate Schedule")
        _gen_pix = load_pixmap(ICON_CALENDAR_PLUS, size=20)
        if not _gen_pix.isNull():
            self.generate_btn.setIcon(QIcon(_gen_pix))

        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.setVisible(False)
        self.generate_btn.clicked.connect(self._on_generate_clicked)

        self.view_calendar_btn = QPushButton("  View Calendar")
        if not _gen_pix.isNull():
            self.view_calendar_btn.setIcon(QIcon(_gen_pix))
        self.view_calendar_btn.setObjectName("viewCalendarBtn")
        self.view_calendar_btn.setVisible(False)
        self.view_calendar_btn.clicked.connect(self.switch_to_output.emit)

        self.spinner      = LoadingSpinner()
        self.error_banner = ErrorBanner()

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.clicked.connect(self.switch_to_settings.emit)

        bar_layout.addWidget(self.settings_btn)
        bar_layout.addStretch()
        bar_layout.addWidget(self.view_calendar_btn)
        bar_layout.addWidget(self.spinner)
        bar_layout.addWidget(self.generate_btn)
        bar_layout.addStretch()

        root.addWidget(self.error_banner)
        root.addWidget(bar)

        # ── Signal connections ─────────────────────────────────────────────
        self.file_loader.files_loaded.connect(self._on_files_loaded)
        self.program_list.programs_selected.connect(self._on_programs_selected)
        self.program_list.program_view_requested.connect(self.course_table.load_program)
        self.period_list.period_selected.connect(self._on_period_selected)
        self.selected_panel.program_removed.connect(self.program_list.remove_selection)

    # ── Tab panel ─────────────────────────────────────────────────────────────

    def _build_tab_panel(
        self, programs_body: QWidget, period_body: QWidget
    ) -> QFrame:
        """White card with a Study Programs / Exam Periods tab bar at the top."""
        card = QFrame()
        card.setObjectName("tabCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Tab bar ────────────────────────────────────────────────────────
        tab_bar_w = QWidget()
        tab_bar_w.setObjectName("tabBar")
        tab_bar_l = QHBoxLayout(tab_bar_w)
        tab_bar_l.setContentsMargins(th.SPACING_LARGE, 0, th.SPACING_LARGE, 0)
        tab_bar_l.setSpacing(0)

        self._tab_programs_btn = QPushButton("🎓  Study Programs")
        self._tab_programs_btn.setObjectName("tabBtnActive")
        self._tab_programs_btn.setCursor(Qt.PointingHandCursor)
        self._tab_programs_btn.clicked.connect(lambda: self._switch_tab(0))

        self._tab_periods_btn = QPushButton("📅  Exam Periods")
        self._tab_periods_btn.setObjectName("tabBtn")
        self._tab_periods_btn.setCursor(Qt.PointingHandCursor)
        self._tab_periods_btn.clicked.connect(lambda: self._switch_tab(1))

        tab_bar_l.addWidget(self._tab_programs_btn)
        tab_bar_l.addWidget(self._tab_periods_btn)
        tab_bar_l.addStretch()

        # ── Content stack ──────────────────────────────────────────────────
        self._tab_stack = QStackedWidget()
        self._tab_stack.addWidget(self._tab_page(programs_body))  # index 0
        self._tab_stack.addWidget(self._tab_page(period_body))    # index 1

        layout.addWidget(tab_bar_w)
        layout.addWidget(self._tab_stack, stretch=1)

        # Subtle elevation shadow
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 18))
        card.setGraphicsEffect(shadow)

        return card

    def _tab_page(self, content: QWidget) -> QWidget:
        """Wrap tab content in a padded container."""
        page = QWidget()
        page.setObjectName("tabPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            th.SPACING_LARGE, th.SPACING_LARGE,
            th.SPACING_LARGE, th.SPACING_LARGE,
        )
        layout.setSpacing(0)
        layout.addWidget(content, stretch=1)
        return page

    def _switch_tab(self, index: int) -> None:
        """Switch the visible tab page and update button styles."""
        self._tab_stack.setCurrentIndex(index)
        self._tab_programs_btn.setObjectName(
            "tabBtnActive" if index == 0 else "tabBtn"
        )
        self._tab_periods_btn.setObjectName(
            "tabBtnActive" if index == 1 else "tabBtn"
        )
        for btn in (self._tab_programs_btn, self._tab_periods_btn):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    # ── Section card (col 1) ──────────────────────────────────────────────────

    # Builds a numbered section card with a title and optional subtitle.
    def _make_section(self, number: int, title: str, widgets: list,
                      subtitle: str = "") -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            th.SPACING_LARGE, th.SPACING_LARGE,
            th.SPACING_LARGE, th.SPACING_LARGE,
        )
        layout.setSpacing(th.SPACING_MEDIUM)

        # Header row: number badge + title + optional subtitle
        header = QHBoxLayout()
        header.setSpacing(th.SPACING_SMALL)

        num = QLabel(str(number))
        num.setFixedSize(_SECTION_BADGE_SIZE, _SECTION_BADGE_SIZE)
        num.setAlignment(Qt.AlignCenter)
        num.setStyleSheet(
            f"QLabel {{"
            f" background-color: {th.PRIMARY_COLOR}; color: white;"
            f" border-radius: {_SECTION_BADGE_SIZE // 2}px;"
            f" font-size: {th.FONT_SIZE_SM}px; font-weight: {th.FONT_WEIGHT_BOLD};"
            f"}}"
        )

        title_lbl = QLabel(title)
        title_lbl.setObjectName("sectionTitle")

        header.addWidget(num)
        header.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(f"({subtitle})")
            sub_lbl.setObjectName("sectionSubtitle")
            header.addWidget(sub_lbl)

        header.addStretch()
        layout.addLayout(header)

        # Thin divider below the header
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {th.BORDER_LIGHT};")
        layout.addWidget(line)

        for w in widgets:
            layout.addWidget(w, stretch=1)

        # Subtle elevation shadow
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 18))
        card.setGraphicsEffect(shadow)

        return card

    # ── Button state ──────────────────────────────────────────────────────────

    # Syncs the Generate button's visibility and enabled state based on the current GenerateButtonState.
    def _sync_generate_button_state(self) -> None:
        self.generate_btn.setVisible(self._generate_state.should_show_button())
        self.generate_btn.setEnabled(self._generate_state.should_enable_button())

    # ── Event handlers (logic unchanged) ─────────────────────────────────────

    def check_existing_results(self):
        has_results = self.service.get_schedule_count() > 0
        if hasattr(self, 'view_calendar_btn'):
            self.view_calendar_btn.setVisible(has_results)

    # Handles successful file loading by clearing old UI state and showing the program list.
    def _on_files_loaded(self):
        self._generate_state.reset_after_file_load()
        if hasattr(self, 'view_calendar_btn'):
            self.view_calendar_btn.setVisible(False)

        # Clear selected programs in the service
        self.service.select_programs([])

        # Clear selected programs UI
        self.selected_panel.clear_cache()
        self.selected_panel.clear()
        self.selected_panel.setVisible(False)

        # Clear program list selection state
        if hasattr(self.program_list, "clear_selection"):
            self.program_list.clear_selection()

        # Clear period selection/editor
        self.period_list.clear_selection()
        self.period_list.setVisible(False)

        self.period_editor.clear()
        self.period_editor.setVisible(False)

        # Clear course table (new files = new data)
        self.course_table.clear()

        # Refresh programs from the newly loaded files
        self.program_list.refresh()
        self.program_list.setVisible(True)

        # In the tabbed layout the Exam Periods tab is always accessible, so
        # refresh and show the period list immediately after file load — the
        # user should see all available periods without having to select a
        # program first.
        self.period_list.refresh()
        self.period_list.setVisible(True)

        self.file_loader.update_validation(programs=False, period=False)
        self._sync_generate_button_state()

    # Handles program selection changes and shows dependent widgets only when needed.
    def _on_programs_selected(self, selected_programs):
        has_selection = len(selected_programs) > 0
        self._generate_state.set_program_selection(has_selection)
        self.selected_panel.setVisible(has_selection)
        # period_list stays visible at all times in the Exam Periods tab
        self.file_loader.update_validation(
            programs=has_selection,
            period=self._generate_state.has_viewed_period,
        )

        if has_selection:
            self.selected_panel.refresh(selected_programs)
            self.period_list.refresh()
        else:
            self.selected_panel.clear()
            self.period_list.clear_selection()
            # Keep period_list visible — it lives in its own tab and should
            # always show available periods regardless of program selection.
            self.period_editor.clear()
            self.period_editor.setVisible(False)

        self._sync_generate_button_state()

    # Loads the selected period into the period editor and enables generation.
    def _on_period_selected(self, period_id):
        self.period_editor.load_period(period_id)
        self.period_editor.setVisible(True)
        self._generate_state.set_period_viewed(bool(period_id))
        self._sync_generate_button_state()

    # Starts schedule generation in the background worker.
    def _on_generate_clicked(self):
        """
        Instantiates the background thread worker, links streaming signals, and starts execution.
        """
        if getattr(self.service, '_engine_process', None) is not None:
            self.service._engine_process.stop()
            
        import shutil
        from pathlib import Path
        results_dir = Path("data") / "results"
        if results_dir.exists():
            shutil.rmtree(results_dir, ignore_errors=True)

        if hasattr(self, 'view_calendar_btn'):
            self.view_calendar_btn.setVisible(False)

        # Reset UI state for new generation attempt
        self.error_banner.hide_error()
        self.spinner.start()

        self._generate_state.start_generation()
        self._sync_generate_button_state()
        self._switched_to_output = False

        self._worker = GenerateWorker(self.service)
        self._worker.period_ready.connect(self._on_period_ready)
        self._worker.finished.connect(self._on_generation_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # Handles successful generation completion and switches to the output screen.
    def _on_generation_finished(self, count):
        if getattr(self, "_switched_to_output", False):
            return
        self._switched_to_output = True
        self.spinner.stop()
        self._generate_state.finish_generation()
        self._sync_generate_button_state()
        QTimer.singleShot(500, lambda: self.switch_to_output.emit())

    # Receives period-ready events from the worker while streaming generation runs.
    def _on_period_ready(self, period_id):
        if getattr(self, "_switched_to_output", False):
            return
        self._switched_to_output = True
        self.spinner.stop()
        self._generate_state.finish_generation()
        self._sync_generate_button_state()
        QTimer.singleShot(500, lambda: self.switch_to_output.emit())

    # Handles errors emitted from the background worker, updating the UI accordingly.
    def _on_error(self, message):
        self.spinner.stop()
        self._generate_state.finish_generation()
        self._sync_generate_button_state()
        self.error_banner.show_error(message)
