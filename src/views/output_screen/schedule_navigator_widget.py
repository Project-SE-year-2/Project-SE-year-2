from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class ScheduleNavigatorWidget(QWidget):
    """Bottom navigation bar for browsing generated schedules."""

    index_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        """Initialize the navigator with default index and count, and set up the UI"""
        super().__init__(parent)
        self._current_index = 0
        self._total_count = 0
        self._init_ui()

    def _init_ui(self):
        """Set up the horizontal layout with Previous/Next buttons and a counter label"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.addStretch()

        self.prev_btn = QPushButton("Previous")
        self.prev_btn.setObjectName("navTextBtn")
        self.prev_btn.clicked.connect(self._on_prev)
        layout.addWidget(self.prev_btn)

        self.counter_label = QLabel("Schedule 0 of 0")
        self.counter_label.setObjectName("paginationText")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setMinimumWidth(150)
        layout.addWidget(self.counter_label)

        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("navTextBtn")
        self.next_btn.clicked.connect(self._on_next)
        layout.addWidget(self.next_btn)

        layout.addStretch()
        self._update_buttons()

    def set_data(self, current_index: int, total_count: int):
        """Update the current index, total count, label, and button states."""
        self._total_count = max(0, total_count)
        if self._total_count == 0:
            self._current_index = 0
        else:
            self._current_index = min(max(0, current_index), self._total_count - 1)

        display_index = self._current_index + 1 if self._total_count else 0
        self.counter_label.setText(f"Schedule {display_index} of {self._total_count}")
        self._update_buttons()

    def _update_buttons(self):
        """Enable/disable Previous and Next buttons based on the current index and total count"""
        self.prev_btn.setEnabled(self._current_index > 0)
        self.next_btn.setEnabled(
            self._total_count > 0 and self._current_index < self._total_count - 1
        )

    def _on_prev(self):
        """Navigate to the previous schedule if possible and emit the index_changed signal"""
        if self._current_index > 0:
            self.set_data(self._current_index - 1, self._total_count)
            self.index_changed.emit(self._current_index)

    def _on_next(self):
        """Navigate to the next schedule if possible and emit the index_changed signal"""
        if self._current_index < self._total_count - 1:
            self.set_data(self._current_index + 1, self._total_count)
            self.index_changed.emit(self._current_index)
