from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

class input_screen(QWidget):
    # 1. Define the signal exactly as the MainWindow expects it
    switch_to_output = pyqtSignal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        
        # 2. Call the function that actually draws the buttons!
        self._setup_ui()

    def _setup_ui(self):
        """
        Initializes the user interface components and layouts.
        """
        layout = QVBoxLayout(self)

        # Title Label
        self.title_label = QLabel("Select Programs and Generate Schedule")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; margin-bottom: 20px; color: white;")
        layout.addWidget(self.title_label)

        # Push the button to the bottom
        layout.addStretch()

        # The Generate Button
        self.generate_btn = QPushButton("📅 GENERATE CALENDAR")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                padding: 10px; 
                background-color: #3a3a3a; 
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        layout.addWidget(self.generate_btn)

    def _on_generate_clicked(self):
        """
        Callback executed when the user clicks the generate button.
        Emits the correct signal name to trigger the MainWindow transition.
        """
        self.switch_to_output.emit()

