from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal, Qt

# Import the Singleton service and screen modules
from src.presenter.app_service import AppService
from src.views.input_screen.input_screen import input_screen
from src.views.output_screen.calendar_table_widget import CalendarTableWidget

class PlaceholderOutputScreen(QWidget):
    """
    A temporary placeholder for the output screen (EP-59).
    Includes the required switch_to_input signal to navigate back.
    """
    switch_to_input = pyqtSignal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Output Screen (Calendar)")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #4CAF50; font-size: 24px; font-weight: bold;")
        layout.addWidget(label)
        
        # Button to trigger the switch_to_input signal
        back_btn = QPushButton("⬅ Back to Input Screen")
        back_btn.setStyleSheet("padding: 10px; background-color: #3a3a3a; border-radius: 5px;")
        back_btn.clicked.connect(self.switch_to_input.emit)
        layout.addWidget(back_btn)

class MainWindow(QMainWindow):
    """
    The main application window acting as the root scaffold.
    Manages the central stacked widget for navigating between screens.
    """
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Schedule Generator System")
        self.resize(1024, 768)
        
        # Apply dark mode styling for a consistent application theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
        """)

        # 1. Instantiate AppService.getInstance() exactly once
        self.service = AppService.getInstance()

        # 2. Build MainWindow as a QMainWindow containing a QStackedWidget
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self._init_screens()

    def _init_screens(self):
        """
        Initializes screens, injects dependencies, and wires navigation signals.
        """
        # Inject the SAME service instance into both screens
        self.input_screen = input_screen(self.service)
        self.output_screen = PlaceholderOutputScreen(self.service)

        # 3. InputScreen on page 0, OutputScreen on page 1
        self.stacked_widget.addWidget(self.input_screen)  # Index 0
        self.stacked_widget.addWidget(self.output_screen) # Index 1

        # 4. Wire the signals to the matching page switches
        self.input_screen.switch_to_output.connect(self._show_output_screen)
        self.output_screen.switch_to_input.connect(self._show_input_screen)

    def _show_output_screen(self):
        """Switches the stacked widget to the Output Screen (Index 1)."""
        self.stacked_widget.setCurrentIndex(1)

    def _show_input_screen(self):
        """Switches the stacked widget to the Input Screen (Index 0)."""
        self.stacked_widget.setCurrentIndex(0)