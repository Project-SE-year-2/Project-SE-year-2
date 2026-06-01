from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

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
        # TODO EP-46: replace with GenerateWorker(self._service).start() 
        self.switch_to_output.emit()