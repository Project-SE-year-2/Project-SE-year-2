"""
ScheduleNavigatorWidget — compact « N of M » navigation bar.

Signals
-------
navigate_to(int)    — emitted after a Prev/Next click; carries the new 0-based index.
prefetch_needed(int)— emitted when the user approaches the end of the loaded buffer;
                      carries the current `loaded` count so the caller knows where to
                      start fetching the next batch.

Public API
----------
set_state(current, total, loaded)
    current : 0-based index of the currently displayed schedule.
    total   : total number of schedules that exist (may be ≥ loaded).
    loaded  : how many schedules are in the in-memory buffer.

current_index : int  (read-only property)
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class ScheduleNavigatorWidget(QWidget):
    """Compact Previous / Counter / Next widget for schedule browsing."""

    navigate_to     = pyqtSignal(int)   # new 0-based index
    prefetch_needed = pyqtSignal(int)   # current loaded count

    # Emit prefetch_needed when remaining buffer ≤ this many items.
    PREFETCH_THRESHOLD = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0
        self._total   = 0
        self._loaded  = 0
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._prev_btn = QPushButton("‹")
        self._prev_btn.setObjectName("navArrowBtn")
        self._prev_btn.setFixedSize(30, 30)
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.clicked.connect(self._on_prev)

        self._counter_lbl = QLabel("— of —")
        self._counter_lbl.setObjectName("navCounter")
        self._counter_lbl.setAlignment(Qt.AlignCenter)
        self._counter_lbl.setMinimumWidth(60)

        self._next_btn = QPushButton("›")
        self._next_btn.setObjectName("navArrowBtn")
        self._next_btn.setFixedSize(30, 30)
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(self._on_next)

        layout.addWidget(self._prev_btn)
        layout.addWidget(self._counter_lbl)
        layout.addWidget(self._next_btn)

        self._refresh_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current_index(self) -> int:
        return self._current

    def set_state(self, current: int, total: int, loaded: int) -> None:
        """Update the navigator state and refresh the display."""
        self._total   = max(0, total)
        self._loaded  = max(0, loaded)
        if self._total == 0:
            self._current = 0
        else:
            self._current = max(0, min(current, self._loaded - 1))
        self._refresh_ui()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh_ui(self) -> None:
        if self._total == 0:
            self._counter_lbl.setText("— of —")
        else:
            self._counter_lbl.setText(f"{self._current + 1} of {self._total}")

        self._prev_btn.setEnabled(self._current > 0)
        # Next is only available while within the loaded buffer
        self._next_btn.setEnabled(
            self._loaded > 0 and self._current < self._loaded - 1
        )

    def _on_prev(self) -> None:
        if self._current > 0:
            self._current -= 1
            self._refresh_ui()
            self.navigate_to.emit(self._current)

    def _on_next(self) -> None:
        if self._loaded > 0 and self._current < self._loaded - 1:
            self._current += 1
            self._refresh_ui()
            self.navigate_to.emit(self._current)
            # Proactive prefetch when approaching end of buffer
            remaining = self._loaded - self._current
            if remaining <= self.PREFETCH_THRESHOLD and self._loaded < self._total:
                self.prefetch_needed.emit(self._loaded)
