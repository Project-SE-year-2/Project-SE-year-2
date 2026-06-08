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
from src.views.widgets.selected_programs_panel import SelectedProgramsPanel

class InputScreen(QWidget):
    """
    The main input screen where users select programs and trigger schedule generation.
    Handles UI state transitions for background processing.
    """
    switch_to_output = pyqtSignal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        # Apply the Dark Mode stylesheet to the entire screen
        self.setStyleSheet(INPUT_SCREEN_STYLE)
        self._setup_ui()

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

    def _on_files_loaded(self):
        # Clear any state from previous file loads
        self.selected_panel.clear_cache()
        self.selected_panel.clear()
        self.selected_panel.setVisible(False)

        self.period_list.clear_selection()
        self.period_list.setVisible(False)

        self.generate_btn.setVisible(False)

        # Refresh programs from the newly loaded files
        self.program_list.refresh()
        self.program_list.setVisible(True)

    def _on_programs_selected(self, selected_programs):
        # Show the period list only if there are selected programs
        has_selection = len(selected_programs) > 0
        self.selected_panel.setVisible(has_selection)
        self.period_list.setVisible(has_selection)

        if has_selection:
            self.selected_panel.refresh(selected_programs)
            self.period_list.refresh()
        else:
            self.selected_panel.clear()
            self.period_list.clear_selection()
            self.generate_btn.setVisible(False)

    # When a period is selected, show the generate button
    def _on_period_selected(self, period_id):
        self.generate_btn.setVisible(True)

    def _on_generate_clicked(self):
        """
        Instantiates the background thread worker, links streaming signals, and starts execution.
        """
        # Reset UI state for new generation attempt
        self.error_banner.hide_error()
        self.spinner.start()
        
        self.generate_btn.setEnabled(False)

        self._worker = GenerateWorker(self.service)
        self._worker.period_ready.connect(self._on_period_ready)
        self._worker.finished.connect(self._on_generation_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_generation_finished(self, count):
        self.spinner.stop()
        self.generate_btn.setEnabled(True)
        self.switch_to_output.emit()

    def _on_period_ready(self, period_id):
        pass

    def _on_error(self, message):
        """Handles errors emitted from the background worker, updating the UI accordingly."""
        self.spinner.stop()
        self.generate_btn.setEnabled(True)
        self.error_banner.show_error(message)