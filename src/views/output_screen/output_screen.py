from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.views.output_screen.calendar_table_widget import ScheduleCalendarWidget
from src.views.output_screen.day_detail_dialog import DayDetailDialog
from src.views.output_screen.schedule_navigator_widget import ScheduleNavigatorWidget
from src.styles.output_screen_style import OUTPUT_SCREEN_STYLE


class OutputScreen(QWidget):
    """Screen that displays generated schedules and export/navigation controls."""

    switch_to_input = pyqtSignal()

    BATCH_SIZE = 10
    POLL_INTERVAL_MS = 1000

    def __init__(self, service, parent=None):
        """Initialize the output screen with references to the service, default schedule data, 
                and set up the UI and polling mechanism."""
        super().__init__(parent)
        self.service = service

        self.current_schedules = []
        self.current_index = 0
        self.total_schedules = 0

        self._setup_ui()
        self._setup_polling()

    def _load_stylesheet(self):
        """Load and apply the stylesheet for the output screen."""
        self.setStyleSheet(OUTPUT_SCREEN_STYLE)

    def _setup_ui(self):
        """Set up the user interface components, including buttons, labels, calendar widget, and navigator."""
        self._load_stylesheet()
        self.setObjectName("mainContainer")

        # Create the main vertical layout for the screen
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(18)

        # Create a horizontal toolbar layout for the back button, title, and download button
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        # Initialize the back button, title label, and download button with appropriate styles and connect signals
        self.back_btn = QPushButton("Back to Input")
        self.back_btn.setObjectName("backBtn")
        self.back_btn.clicked.connect(self._on_back_clicked)

        # Set the title label with a specific object name for styling
        self.title_label = QLabel("Exam Calendar")
        self.title_label.setObjectName("mainTitle")

        # Initialize the download button
        self.download_btn = QPushButton("Download Schedule")
        # Set the object name for styling and connect the click signal to the download handler
        self.download_btn.setObjectName("primaryBtn")
        # Connect the download button's clicked signal to the handler method
        self.download_btn.clicked.connect(self._on_download_clicked)

        # Add widgets to the toolbar with spacing and alignment
        toolbar.addWidget(self.back_btn)
        toolbar.addWidget(self.title_label)
        toolbar.addStretch()
        toolbar.addWidget(self.download_btn)
        main_layout.addLayout(toolbar)

        # Card container to hold the calendar widget with a styled frame
        self.card_container = QFrame()
        self.card_container.setObjectName("cardContainer")
        card_layout = QVBoxLayout(self.card_container)
        card_layout.setContentsMargins(0, 0, 0, 0)

        #  Initialize the calendar widget and add it to the card layout
        self.calendar = ScheduleCalendarWidget()
        self.calendar.exam_clicked.connect(self._on_exam_clicked)
        card_layout.addWidget(self.calendar)
        main_layout.addWidget(self.card_container, stretch=1)

        # Initialize the schedule navigator widget, connect its signals, and add it to the main layout
        self.navigator = ScheduleNavigatorWidget()
        self.navigator.index_changed.connect(self._on_navigator_index_changed)
        self.sched_label = self.navigator.counter_label
        self.prev_btn = self.navigator.prev_btn
        self.next_btn = self.navigator.next_btn
        main_layout.addWidget(self.navigator)

        # Update the navigator label and button states based on the initial schedule count
        self._update_schedule_nav_label()

    def _setup_polling(self):
        """Set up a QTimer to poll the service for schedule count updates at regular intervals."""
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_schedule_count)
        self.destroyed.connect(self.poll_timer.stop)

    def showEvent(self, event):
        """Override the showEvent to load the initial batch of schedules and start polling when the screen is shown."""
        super().showEvent(event)
        self.current_index = 0
        # Load the initial batch of schedules to display immediately when the screen is shown, then start polling for updates.
        self._load_initial_batch()
        self._poll_schedule_count()
        self.poll_timer.start(self.POLL_INTERVAL_MS)

    def hideEvent(self, event):
        """Override the hideEvent to stop polling when the screen is hidden."""
        super().hideEvent(event)
        self.poll_timer.stop()

    def _load_initial_batch(self):
        """Load the initial batch of schedules to display when the screen is first shown."""
        try:
            self.current_schedules = self.service.get_schedule_batch(0, self.BATCH_SIZE)
        except Exception as exc:
            self.current_schedules = []
            print(f"DEBUG: Could not load initial batch: {exc}")
            return

        if self.current_schedules:
            # Load the first schedule into the calendar widget.
            self.calendar.update_schedule(self.current_schedules[0])

    def _load_schedule(self, index):
        """Load a specific schedule by index and update the calendar widget accordingly."""
        try:
            schedules = self.service.get_schedule_batch(index, 1)
        except Exception as exc:
            print(f"DEBUG: Could not load schedule {index}: {exc}")
            return

        if schedules:
            self.calendar.update_schedule(schedules[0])

    def _on_navigator_index_changed(self, index):
        """Handle index changes from the navigator, update the current index, load the corresponding schedule,
                 and refresh the navigator label."""
        self.current_index = index
        self._load_schedule(index)
        self._update_schedule_nav_label()

    def _prev_schedule(self):
        """Navigate to the previous schedule if possible and update the calendar widget."""
        if self.current_index > 0:
            self._on_navigator_index_changed(self.current_index - 1)

    def _next_schedule(self):
        """Navigate to the next schedule if possible and update the calendar widget."""
        try:
            self.total_schedules = self.service.get_schedule_count()
        except Exception:
            pass
        if self.current_index < self.total_schedules - 1:
            self._on_navigator_index_changed(self.current_index + 1)

    def _update_schedule_nav_label(self):
        """Update the navigator's counter label and button states based on the current index and total 
                schedule count."""
        self.navigator.set_data(self.current_index, self.total_schedules)

    def _poll_schedule_count(self):
        """Poll the service for the total schedule count, update the navigator label, 
                and adjust the current index if necessary."""
        try:
            self.total_schedules = self.service.get_schedule_count()
        except Exception:
            self.total_schedules = 0

        if self.current_index >= self.total_schedules and self.total_schedules > 0:
            self.current_index = self.total_schedules - 1

        self._update_schedule_nav_label()

    def _on_exam_clicked(self, exam_data: dict) -> None:
        """Open a DayDetailDialog for the clicked exam badge."""
        program_names = self._get_program_names()
        dialog = DayDetailDialog(exam_data, program_names=program_names, parent=self)
        dialog.exec_()

    def _get_program_names(self) -> dict:
        """Build an id → display-name mapping from the service."""
        try:
            return {p["id"]: p["name"] for p in self.service.get_available_programs()}
        except Exception:
            return {}

    def _on_back_clicked(self):
        """Handle the back button click by emitting the signal to switch back to the input screen."""
        self.switch_to_input.emit()

    def _on_download_clicked(self):
        """Handle the download button click by prompting the user to select a save location and 
                exporting the current schedule."""
        if self.total_schedules <= 0 and not self.current_schedules:
            QMessageBox.warning(self, "No Schedule", "No schedule is currently loaded.")
            return

        options = QFileDialog.Options()
        # Ensure the dialog does not use native file dialogs 
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Schedule",
            "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)",
            options=options,
        )
        if not file_path:
            return

        try:
            self.service.export_schedule(self.current_index, file_path)
            QMessageBox.information(self, "Success", "Schedule exported successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export schedule:\n{exc}")
