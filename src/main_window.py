from PyQt5.QtWidgets import QMainWindow, QStackedWidget

# Import the Singleton service and screen modules
from src.presenter.app_service import AppService
from src.views.input_screen.input_screen import InputScreen
from src.views.output_screen.output_screen import OutputScreen
from src.views.settings_screen.settings_screen import SettingsScreen

class MainWindow(QMainWindow):
    """
    The main application window acting as the root scaffold.
    Manages the central stacked widget for navigating between screens.
    """
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Schedule Generator System")
        self.resize(1024, 768)
        
        self.setStyleSheet("""
            QMainWindow    { background-color: #F8FAFC; }
            QStackedWidget { background-color: #F8FAFC; }
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
        # Inject the SAME service instance into all screens
        self.input_screen = InputScreen(self.service)
        self.output_screen = OutputScreen(self.service)
        self.settings_screen = SettingsScreen(self.service)

        # InputScreen=0, OutputScreen=1, SettingsScreen=2
        self.stacked_widget.addWidget(self.input_screen)    # Index 0
        self.stacked_widget.addWidget(self.output_screen)   # Index 1
        self.stacked_widget.addWidget(self.settings_screen) # Index 2

        # Wire navigation signals
        self.input_screen.switch_to_output.connect(self._show_output_screen)
        self.input_screen.switch_to_settings.connect(self._show_settings_screen)
        self.output_screen.switch_to_input.connect(self._show_input_screen)
        # Settings back-navigation must NOT wipe results — user is just browsing settings.
        self.settings_screen.switch_to_input.connect(self._return_to_input_without_wipe)

    def _show_output_screen(self):
        """Switches the stacked widget to the Output Screen (Index 1)."""
        self.stacked_widget.setCurrentIndex(1)

    def _show_settings_screen(self):
        """Switches the stacked widget to the Settings Screen (Index 2)."""
        self.stacked_widget.setCurrentIndex(2)

    def _return_to_input_without_wipe(self):
        """Return to the Input Screen from Settings without wiping generated results."""
        self.stacked_widget.setCurrentIndex(0)

    def _wipe_results(self):
        """Cleanly stop the background engine and aggressively wipe the disk."""
        if self.service._engine_process is not None:
            self.service._engine_process.stop()
            
        import shutil
        from pathlib import Path
        results_dir = Path("data") / "results"
        if results_dir.exists():
            shutil.rmtree(results_dir, ignore_errors=True)

    def _show_input_screen(self):
        """Switches the stacked widget to the Input Screen (Index 0)."""
        self.stacked_widget.setCurrentIndex(0)
        if hasattr(self.input_screen, 'check_existing_results'):
            self.input_screen.check_existing_results()

    def closeEvent(self, event):
        """Hook into the application shutdown to wipe all generated results."""
        self._wipe_results()
        super().closeEvent(event)