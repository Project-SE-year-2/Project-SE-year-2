from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QScrollArea
from PyQt5.QtCore import pyqtSignal, Qt

# Import the existing GenerateWorker per task requirements
from src.presenter.generate_worker import GenerateWorker
from src.styles.input_screen_style import INPUT_SCREEN_STYLE
from src.views.shared_components.error_banner import ErrorBanner
from src.views.shared_components.loading_spinner import LoadingSpinner
from src.views.widgets.file_loader_widget import FileLoaderWidget
from src.views.widgets.program_list_widget import ProgramListWidget
from src.views.widgets.period_list_widget import PeriodListWidget
from src.views.widgets.period_editor_widget import PeriodEditorWidget
from src.views.widgets.selected_programs_panel import SelectedProgramsPanel
from src.views.input_screen.generate_button_state import GenerateButtonState


class InputScreen(QWidget):
    """
    The main input screen where users select programs and trigger schedule generation.
    Handles UI state transitions for background processing.
    """
    switch_to_output = pyqtSignal()

    # Initializes the screen, stores the service dependency, and builds the UI.
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._generate_state = GenerateButtonState()
        # Apply the Dark Mode stylesheet to the entire screen
        self.setStyleSheet(INPUT_SCREEN_STYLE)
        self._setup_ui()
        self._sync_generate_button_state()

    # Builds all input-screen widgets and connects their signals.
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        self.title_label = QLabel("Select Programs and Generate Schedule")
        self.title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.title_label)

        self.file_loader = FileLoaderWidget(self.service)
        content_layout.addWidget(self.file_loader)

        self.program_list = ProgramListWidget(self.service)
        self.program_list.setVisible(False)
        content_layout.addWidget(self.program_list)

        self.selected_panel = SelectedProgramsPanel(self.service)
        self.selected_panel.setVisible(False)
        content_layout.addWidget(self.selected_panel)

        self.period_list = PeriodListWidget(self.service)
        self.period_list.setVisible(False)
        content_layout.addWidget(self.period_list)

        self.period_editor = PeriodEditorWidget(self.service)
        self.period_editor.setVisible(False)
        content_layout.addWidget(self.period_editor)

        self.spinner = LoadingSpinner()
        content_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)

        self.error_banner = ErrorBanner()
        content_layout.addWidget(self.error_banner)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, stretch=1)

        self.generate_btn = QPushButton("GENERATE CALENDAR")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.generate_btn.setVisible(False)
        main_layout.addWidget(self.generate_btn)

        self.file_loader.files_loaded.connect(self._on_files_loaded)
        self.program_list.programs_selected.connect(self._on_programs_selected)
        self.period_list.period_selected.connect(self._on_period_selected)

    # Syncs the Generate button's visibility and enabled state based on the current GenerateButtonState.
    def _sync_generate_button_state(self) -> None:
        self.generate_btn.setVisible(self._generate_state.should_show_button())
        self.generate_btn.setEnabled(self._generate_state.should_enable_button())

    # Handles successful file loading by clearing old UI state and showing the program list.
    def _on_files_loaded(self):
        self._generate_state.reset_after_file_load()
        # Clear any state from previous file loads
        self.selected_panel.clear_cache()
        self.selected_panel.clear()
        self.selected_panel.setVisible(False)

        self.period_list.clear_selection()
        self.period_list.setVisible(False)

        self.period_editor.clear()
        self.period_editor.setVisible(False)

        # Refresh programs from the newly loaded files
        self.program_list.refresh()
        self.program_list.setVisible(True)

        self._sync_generate_button_state()

    # Handles program selection changes and shows dependent widgets only when needed.
    def _on_programs_selected(self, selected_programs):
        has_selection = len(selected_programs) > 0
        self._generate_state.set_program_selection(has_selection)
        self.selected_panel.setVisible(has_selection)
        self.period_list.setVisible(has_selection)

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

        self._worker = GenerateWorker(self.service)
        self._worker.period_ready.connect(self._on_period_ready)
        self._worker.finished.connect(self._on_generation_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # Handles successful generation completion and switches to the output screen.
    def _on_generation_finished(self, count):
        self.spinner.stop()
        self._generate_state.finish_generation()
        self._sync_generate_button_state()
        self.switch_to_output.emit()

    # Receives period-ready events from the worker while streaming generation runs.
    def _on_period_ready(self, period_id):
        pass

    # Handles errors emitted from the background worker, updating the UI accordingly.
    def _on_error(self, message):
        self.spinner.stop()
        self._generate_state.finish_generation()
        self._sync_generate_button_state()
        self.error_banner.show_error(message)
