from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal, Qt

# Import the Singleton service and screen modules
from src.presenter.app_service import AppService
from src.views.input_screen.input_screen import InputScreen
from src.views.output_screen.output_screen import OutputScreen

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

        # Instantiate AppService.getInstance() exactly once
        self.service = AppService.getInstance()

        # Build MainWindow as a QMainWindow containing a QStackedWidget
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self._init_screens()

    def _init_screens(self):
        """
        Initializes screens, injects dependencies, and wires navigation signals.
        """
        # Inject the SAME service instance into both REAL screens
        self.input_screen = InputScreen(self.service)
        self.output_screen = OutputScreen(self.service)

        # InputScreen on page 0, OutputScreen on page 1
        self.stacked_widget.addWidget(self.input_screen)  # Index 0
        self.stacked_widget.addWidget(self.output_screen) # Index 1

        # Wire the signals to the matching page switches
        self.input_screen.switch_to_output.connect(self._show_output_screen)
        self.output_screen.switch_to_input.connect(self._show_input_screen)

    def _show_output_screen(self):
        """Switches the stacked widget to the Output Screen (Index 1)."""
        self.stacked_widget.setCurrentIndex(1)

    def _show_input_screen(self):
        """Switches the stacked widget to the Input Screen (Index 0)."""
        self.stacked_widget.setCurrentIndex(0)