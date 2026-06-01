import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer

# Import the shared calendar widget from EP-47
from src.views.output_screen.calendar_table_widget import ScheduleCalendarWidget
from src.styles.output_screen_style import OUTPUT_SCREEN_STYLE
class OutputScreen(QWidget):
    """
    The main output screen layout (EP-59 & EP-62).
    Contains a top toolbar, a central schedule grid, and a bottom navigation bar.
    Actively fetches data and polls the backend for new schedules.
    """
    switch_to_input = pyqtSignal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        
        # State variables to hold the fetched data
        self.current_schedules = []
        self.current_index = 0
        self.total_schedules = 0
        
        self._setup_ui()
        self._setup_polling()

    def _load_stylesheet(self):
        """
        Dynamically loads the CSS stylesheet from the src/style/ directory.
        """
        # Calculate the absolute path to the src/ directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(os.path.dirname(current_dir))
        
        # Construct the path to the CSS file
        style_path = os.path.join(src_dir, "styles", "output_screen_style.py")
        
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(OUTPUT_SCREEN_STYLE)
        except FileNotFoundError:
            print(f"DEBUG: Could not find stylesheet at {style_path}")

    def _setup_ui(self):
        """Builds the 3-part layout: Top Toolbar, Central Calendar, Bottom Toolbar."""
        
        # Load the external CSS and set the main container ID
        self._load_stylesheet()
        self.setObjectName("mainContainer")
        self._load_stylesheet()

        main_layout = QVBoxLayout(self)
        
        # --- 1. Top Toolbar ---
        top_toolbar = QHBoxLayout()
        
        self.back_btn = QPushButton("⬅ Back to Input")
        self.back_btn.setObjectName("backBtn")
        self.back_btn.clicked.connect(self._on_back_clicked)
        
        self.download_btn = QPushButton("💾 Download Schedule")
        self.download_btn.setObjectName("primaryBtn")
        self.download_btn.clicked.connect(self._on_download_clicked)
        
        top_toolbar.addWidget(self.back_btn)
        top_toolbar.addStretch() 
        top_toolbar.addWidget(self.download_btn)
        
        main_layout.addLayout(top_toolbar)
        
        # --- 2. Central Area (Calendar wrapped in a Card Frame) ---
        self.card_container = QFrame()
        self.card_container.setObjectName("cardContainer")
        card_layout = QVBoxLayout(self.card_container)
        
        self.calendar = ScheduleCalendarWidget()
        card_layout.addWidget(self.calendar)
        
        main_layout.addWidget(self.card_container, stretch=1)
        
        # --- 3. Bottom Navigation Bar (EP-62) ---
        bottom_toolbar = QHBoxLayout()
        
        # Previous Arrow Button
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setObjectName("iconBtn")
        self.prev_btn.clicked.connect(self._prev_schedule)
        
        # Pagination Label
        self.sched_label = QLabel("1 of 1")
        self.sched_label.setObjectName("paginationText")
        self.sched_label.setAlignment(Qt.AlignCenter)
        
        # Next Arrow Button
        self.next_btn = QPushButton("▶")
        self.next_btn.setObjectName("iconBtn")
        self.next_btn.clicked.connect(self._next_schedule)
        
        bottom_toolbar.addStretch()
        bottom_toolbar.addWidget(self.prev_btn)
        bottom_toolbar.addWidget(self.sched_label)
        bottom_toolbar.addWidget(self.next_btn)
        bottom_toolbar.addStretch()
        
        main_layout.addLayout(bottom_toolbar)

    def _setup_polling(self):
        """Initializes the background timer for polling schedule counts."""
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_schedule_count)

    def showEvent(self, event):
        """
        Triggered automatically by PyQt when the screen becomes visible.
        Fetches the initial batch and starts the polling timer.
        """
        super().showEvent(event)
        self.current_index = 0
        self._update_schedule_nav_label()
        self._load_schedule(self.current_index)
            
        # Start polling the service every 1000 milliseconds
        self.poll_timer.start(1000)

    def hideEvent(self, event):
        """Stops the polling timer when leaving the screen to save resources."""
        super().hideEvent(event)
        self.poll_timer.stop()

    # --- EP-62 Navigation Logic ---
    
    def _load_schedule(self, index):
        """Fetches a specific schedule by index and renders it in the calendar."""
        try:
            # Fetch exactly 1 schedule at the given index
            schedules = self.service.get_schedule_batch(index, 1)
            if schedules and len(schedules) > 0:
                self.calendar.render_schedule_mode(schedules[0])
        except Exception as e:
            print(f"DEBUG: Could not load schedule {index}: {e}")

    def _prev_schedule(self):
        """Navigates to the previous schedule if available."""
        if self.current_index > 0:
            self.current_index -= 1
            self._update_schedule_nav_label()
            self._load_schedule(self.current_index)

    def _next_schedule(self):
        """Navigates to the next schedule if available."""
        total = max(1, self.service.get_schedule_count())
        if self.current_index < total - 1:
            self.current_index += 1
            self._update_schedule_nav_label()
            self._load_schedule(self.current_index)

    def _update_schedule_nav_label(self):
        """Updates the pagination text to reflect the current state."""
        total = max(1, self.service.get_schedule_count())
        self.sched_label.setText(f"Schedule {self.current_index + 1} of {total}")

    def _poll_schedule_count(self):
        """Polls the service to see if the backtracking algorithm found more schedules."""
        try:
            # Just update the label so the "total" updates dynamically as algorithm runs
            self._update_schedule_nav_label()
        except Exception:
            pass

    # --- Toolbar Actions ---

    def _on_back_clicked(self):
        """Emits the signal to tell MainWindow to swap back to index 0."""
        self.switch_to_input.emit()

    def _on_download_clicked(self):
        """Opens a file dialog to save the currently viewed schedule."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Schedule", 
            "", 
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)", 
            options=options
        )
        
        if file_path:
            try:
                self.service.export_schedule(file_path, self.current_index)
                QMessageBox.information(self, "Success", "Schedule exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Could not export schedule:\n{str(e)}")