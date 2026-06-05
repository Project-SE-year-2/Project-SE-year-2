from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

# Import the existing GenerateWorker per task requirements
from src.presenter.generate_worker import GenerateWorker
from src.styles.input_screen_style import INPUT_SCREEN_STYLE
from src.views.shared_components.error_banner import ErrorBanner
from src.views.shared_components.loading_spinner import LoadingSpinner
from src.views.widgets.file_loader_widget import FileLoaderWidget
from src.views.widgets.program_list_widget import ProgramListWidget
from src.views.widgets.period_list_widget import PeriodListWidget

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
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel("Select Programs and Generate Schedule")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # The users will select input files and load them into the service
        self.file_loader = FileLoaderWidget(self.service)
        layout.addWidget(self.file_loader)

        # After loading, the program list will be populated and shown for selection.
        self.program_list = ProgramListWidget(self.service)
        self.program_list.setVisible(False)
        layout.addWidget(self.program_list)

        # After selecting a program, the period list will be shown for selection.
        self.period_list = PeriodListWidget(self.service)
        self.period_list.setVisible(False)
        layout.addWidget(self.period_list)

        # Loading spinner shown during generation processing
        self.spinner = LoadingSpinner()
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)

        # Error banner for displaying generation errors
        # Uses the shared ErrorBanner component
        self.error_banner = ErrorBanner()
        layout.addWidget(self.error_banner)

        layout.addStretch()
        
        self.generate_btn = QPushButton("GENERATE CALENDAR")
        self.generate_btn.clicked.connect(self._on_generate_clicked)

        # Hidden until a period is selected
        self.generate_btn.setVisible(False)

        layout.addWidget(self.generate_btn)

        # Connect signals from child widgets to handle UI state transitions
        self.file_loader.files_loaded.connect(self._on_files_loaded)
        self.program_list.programs_selected.connect(
            self._on_programs_selected
        )
        self.period_list.periods_selected.connect(
            self._on_periods_selected
        )

    def _on_files_loaded(self):
        # After files are loaded, show the program list for selection
        self.program_list.refresh()
        self.program_list.setVisible(True)

    def _on_programs_selected(self, selected_programs):
        # Show the period list only if there are selected programs
        has_selection = len(selected_programs) > 0
        self.period_list.setVisible(has_selection)

        if has_selection:
            self.period_list.refresh()
        else:
            self.period_list.clear_selection()

    # When a period is selected, show the generate button
    def _on_periods_selected(self, period_ids):
        self.generate_btn.setVisible(len(period_ids) > 0)

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