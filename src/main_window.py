from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QMessageBox

# Import the Singleton service and screen modules
from src.presenter.app_service import AppService
from src.views.input_screen.input_screen import InputScreen
from src.views.output_screen.output_screen import OutputScreen
from src.views.settings_screen.settings_dialog import SettingsDialog

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
        # InputScreen=0, OutputScreen=1
        self.stacked_widget.addWidget(self.input_screen)    # Index 0
        self.stacked_widget.addWidget(self.output_screen)   # Index 1

        # Wire navigation signals
        self.input_screen.switch_to_output.connect(self._show_output_screen)
        self.input_screen.switch_to_settings.connect(self._show_settings_dialog)
        self.output_screen.switch_to_input.connect(self._show_input_screen)
        # Route output-screen sort changes to AppService and reset output position.
        self.output_screen.ranking_panel.sort_order_changed.connect(self.service.set_sort_order)
        self.output_screen.ranking_panel.sort_order_changed.connect(self.output_screen.on_sort_changed)

    def _show_output_screen(self):
        """Switches the stacked widget to the Output Screen (Index 1)."""
        self.stacked_widget.setCurrentIndex(1)

    def _show_settings_dialog(self):
        """Instantiates and shows the SettingsDialog."""
        dialog = SettingsDialog(self.service, parent=self)
        
        # We need a local reference to the dialog inside the connection
        def on_confirmed():
            try:
                settings = dialog.get_constraint_settings()
            except ValueError as exc:
                QMessageBox.warning(
                    self,
                    "Invalid Constraint Settings",
                    str(exc),
                )
                return
            
            self.service.set_constraint_settings(settings)
            if hasattr(self.input_screen, "check_existing_results"):
                self.input_screen.check_existing_results()

        dialog.settings_confirmed.connect(on_confirmed)
        
        # Load the current settings into the dialog
        dialog.set_constraint_settings(self.service.get_constraint_settings())
        dialog.exec_()

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

    # Settings confirmed handling is now local to the dialog lambda.
