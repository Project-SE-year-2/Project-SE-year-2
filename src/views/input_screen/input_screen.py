from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
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
from src.views.input_screen.generate_button_state import GenerateButtonState

_SECTION_BADGE_SIZE = 28       # diameter of the numbered circle badge
_GENERATE_BAR_HEIGHT = 68      # fixed height of the bottom generate bar
_PERIOD_LIST_MAX_HEIGHT = 220  # cap so the list doesn't crowd the calendar editor
_SELECTED_PANEL_MIN_HEIGHT = 120  # minimum height for the selected-programs chips area


class InputScreen(QWidget):
    """
    The main input screen where users select programs and trigger schedule generation.
    Handles UI state transitions for background processing.
    """
    switch_to_output = pyqtSignal()

    # Initializes the screen, stores the service dependency, and builds the UI.
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("inputScreen")
        self.service = service
        self._generate_state = GenerateButtonState()
        self.setStyleSheet(INPUT_SCREEN_STYLE)
        self._setup_ui()
        self._sync_generate_button_state()

    # Builds the 3-column layout and connects widget signals.
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(
            th.SPACING_LARGE, th.SPACING_LARGE, th.SPACING_LARGE, 0
        )
        root.setSpacing(0)

        # ── three-column area ──────────────────────────────────────────────
        columns = QHBoxLayout()
        columns.setSpacing(th.SPACING_MEDIUM)

        self.file_loader = FileLoaderWidget(self.service)
        self.program_list = ProgramListWidget(self.service)
        self.selected_panel = SelectedProgramsPanel(self.service)
        self.selected_panel.setMinimumHeight(_SELECTED_PANEL_MIN_HEIGHT)
        self.period_list = PeriodListWidget(self.service)
        self.period_list.setMaximumHeight(_PERIOD_LIST_MAX_HEIGHT)  # prevent list from crowding the calendar
        self.period_editor = PeriodEditorWidget(self.service)

        col1 = self._make_section(
            number=1,
            title="Data Input",
            widgets=[self.file_loader],
        )

        # Programs column: available list on top, selected panel below
        programs_body = QWidget()
        programs_body_layout = QVBoxLayout(programs_body)
        programs_body_layout.setContentsMargins(0, 0, 0, 0)
        programs_body_layout.setSpacing(th.SPACING_SMALL)
        programs_body_layout.addWidget(self.program_list, stretch=2)
        programs_body_layout.addWidget(self.selected_panel, stretch=1)
        self.selected_panel.setVisible(False)

        col2 = self._make_section(
            number=2,
            title="Study Programs",
            subtitle="Select up to 5",
            widgets=[programs_body],
        )
        self.program_list.setVisible(False)

        # Period column: period list on top, calendar editor below
        period_body = QWidget()
        period_body_layout = QVBoxLayout(period_body)
        period_body_layout.setContentsMargins(0, 0, 0, 0)
        period_body_layout.setSpacing(th.SPACING_SMALL)
        period_body_layout.addWidget(self.period_list)
        period_body_layout.addWidget(self.period_editor, stretch=1)
        self.period_list.setVisible(False)
        self.period_editor.setVisible(False)

        col3 = self._make_section(
            number=3,
            title="Exam Period",
            widgets=[period_body],
        )

        columns.addWidget(col1, stretch=1)
        columns.addWidget(col2, stretch=1)
        columns.addWidget(col3, stretch=2)

        root.addLayout(columns, stretch=1)

        # ── bottom generate bar ────────────────────────────────────────────
        bar = QWidget()
        bar.setObjectName("generateBar")
        bar.setFixedHeight(_GENERATE_BAR_HEIGHT)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(
            th.SPACING_XL, 0, th.SPACING_XL, 0
        )

        self.generate_btn = QPushButton("  Generate Schedule")
        _gen_pix = load_pixmap(ICON_CALENDAR_PLUS, size=20)
        if not _gen_pix.isNull():
            self.generate_btn.setIcon(QIcon(_gen_pix))

        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.setVisible(False)
        self.generate_btn.clicked.connect(self._on_generate_clicked)

        self.spinner = LoadingSpinner()
        self.error_banner = ErrorBanner()

        bar_layout.addStretch()
        bar_layout.addWidget(self.spinner)
        bar_layout.addWidget(self.generate_btn)
        bar_layout.addStretch()

        root.addWidget(self.error_banner)
        root.addWidget(bar)

        # ── signal connections ─────────────────────────────────────────────
        self.file_loader.files_loaded.connect(self._on_files_loaded)
        self.program_list.programs_selected.connect(self._on_programs_selected)
        self.period_list.period_selected.connect(self._on_period_selected)
        self.selected_panel.program_removed.connect(self.program_list.remove_selection)

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
        # No objectName — badge is styled inline only to avoid cascade conflicts.
        # Qt5 requires a QSS selector (not bare properties) for border-radius to clip correctly.
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

        # Subtle elevation shadow so cards lift off the background
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 18))
        card.setGraphicsEffect(shadow)

        return card

    # Syncs the Generate button's visibility and enabled state based on the current GenerateButtonState.
    def _sync_generate_button_state(self) -> None:
        self.generate_btn.setVisible(self._generate_state.should_show_button())
        self.generate_btn.setEnabled(self._generate_state.should_enable_button())

    # Handles successful file loading by clearing old UI state and showing the program list.
    def _on_files_loaded(self):
        self._generate_state.reset_after_file_load()

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

        # Refresh programs from the newly loaded files
        self.program_list.refresh()
        self.program_list.setVisible(True)

        self.file_loader.update_validation(programs=False, period=False)
        self.file_loader.update_validation(programs=False, period=False)
        self._sync_generate_button_state()

    # Handles program selection changes and shows dependent widgets only when needed.
    def _on_programs_selected(self, selected_programs):
        has_selection = len(selected_programs) > 0
        self._generate_state.set_program_selection(has_selection)
        self.selected_panel.setVisible(has_selection)
        self.period_list.setVisible(has_selection)
        self.file_loader.update_validation(programs=has_selection, period=self._generate_state.has_viewed_period)

        if has_selection:
            self.selected_panel.refresh(selected_programs)
            self.period_list.refresh()
        else:
            self.selected_panel.clear()
            self.period_list.clear_selection()
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
        self.switch_to_output.emit()

    # Receives period-ready events from the worker while streaming generation runs.
    def _on_period_ready(self, period_id):
        if getattr(self, "_switched_to_output", False):
            return
        self._switched_to_output = True
        self.spinner.stop()
        self._generate_state.finish_generation()
        self._sync_generate_button_state()
        self.switch_to_output.emit()

    # Handles errors emitted from the background worker, updating the UI accordingly.
    def _on_error(self, message):
        self.spinner.stop()
        self._generate_state.finish_generation()
        self._sync_generate_button_state()
        self.error_banner.show_error(message)
