from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

# Import the existing GenerateWorker per task requirements
from src.presenter.generate_worker import GenerateWorker
from src.styles.input_screen_style import INPUT_SCREEN_STYLE
from src.views.shared_components.error_banner import ErrorBanner
from src.views.shared_components.loading_spinner import LoadingSpinner

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
        layout.addWidget(self.generate_btn)
        # שים לב: מחקתי כאן את הקריאה ל-self._setup_error_banner(layout)

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
        self.spinner.stop()
        self.generate_btn.setEnabled(True)
        self.error_banner.show_error(message)