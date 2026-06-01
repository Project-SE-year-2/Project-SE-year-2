from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

# Import the existing GenerateWorker per task requirements
from src.presenter.generate_worker import GenerateWorker
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
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel("Select Programs and Generate Schedule")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # Loading spinner shown during generation processing
        # Initially hidden until generation starts
        self.spinner = LoadingSpinner()
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)

        # Error banner for displaying generation errors
        # Initially hidden until an error occurs
        self.error_banner = ErrorBanner()
        layout.addWidget(self.error_banner)

        layout.addStretch()
        
        self.generate_btn = QPushButton("GENERATE CALENDAR")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        layout.addWidget(self.generate_btn)

    def _on_generate_clicked(self):
        """
        Instantiates the background thread worker, links streaming signals, and starts execution.
        Updates UI state to prevent concurrent generation attempts.
        """
        # Reset UI state for new generation attempt
        self.error_banner.hide_error()
        self.spinner.start()
        
        # Disable the generate button to prevent multiple concurrent generation attempts
        self.generate_btn.setEnabled(False)

        self._worker = GenerateWorker(self.service)
        self._worker.period_ready.connect(self._on_period_ready)
        self._worker.finished.connect(self._on_generation_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_generation_finished(self, count):
        """
        Callback executed when the worker completes streaming all periods.
        Resets UI state and triggers the navigation transition to the output screen.
        """
        self.spinner.stop()
        self.generate_btn.setEnabled(True)
        self.switch_to_output.emit()

    def _on_period_ready(self, period_id):
        """
        Callback executed when a distinct scheduling period finishes processing.
        """
        pass  # Output screen handles this in EP-59

    def _on_error(self, message):
        """
        Callback executed if the background processing encounters an exception.
        Stops the spinner, re-enables the button, and displays the error banner.
        """
        self.spinner.stop()
        self.generate_btn.setEnabled(True)
        self.error_banner.show_error(message)