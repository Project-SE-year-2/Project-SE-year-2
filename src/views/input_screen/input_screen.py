from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

# Import the existing GenerateWorker per task requirements
from src.presenter.generate_worker import GenerateWorker

class InputScreen(QWidget):
    """
    The main input screen where users select programs and trigger schedule generation.
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
        layout.addStretch()
        self.generate_btn = QPushButton("GENERATE CALENDAR")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        layout.addWidget(self.generate_btn)

    def _on_generate_clicked(self):
        """
        Instantiates the background thread worker, links streaming signals, and starts execution.
        """
        self._worker = GenerateWorker(self.service)
        self._worker.period_ready.connect(self._on_period_ready)
        self._worker.finished.connect(self._on_generation_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_generation_finished(self, count):
        """
        Callback executed when the worker completes streaming all periods.
        Triggers the navigation transition to the output screen.
        """
        self.switch_to_output.emit()

    def _on_period_ready(self, period_id):
        """
        Callback executed when a distinct scheduling period finishes processing.
        """
        pass  # Output screen handles this in EP-59

    def _on_error(self, message):
        """
        Callback executed if the background processing encounters an exception.
        """
        pass  # EP-48 will add ErrorBanner here