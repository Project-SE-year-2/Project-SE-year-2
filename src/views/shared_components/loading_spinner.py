"""
Animated loading spinner widget shown during schedule generation.
Used by InputScreen during generate() processing.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QPainter, QColor, QPen
import src.styles.theme as th

class LoadingSpinner(QWidget):
    """
    Rotating circular spinner animation.
    
    Emits no signals. Call start() to begin animation, stop() to halt it.
    """

    def __init__(self, parent=None, size: int = None):
        """
        Args:
            parent: parent widget
            size: diameter in pixels (default 40)
        """
        super().__init__(parent)
        # Use provided size or default from theme
        self._spinner_size = size if size is not None else th.SPINNER_SIZE
        self.angle = 0
        self.is_running = False

        self.setFixedSize(self._spinner_size, self._spinner_size)
        
        # Enforce transparent background and ignore global stylesheet cascades
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setStyleSheet("background: transparent; border: none;")

        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._rotate)
        self.timer.setInterval(th.SPINNER_TIMER_INTERVAL)

    def start(self) -> None:
        """Begin the spinner animation."""
        self.is_running = True
        self.timer.start()

    def stop(self) -> None:
        """Stop the spinner animation."""
        self.is_running = False
        self.timer.stop()
        self.angle = 0
        self.update()

    def _rotate(self) -> None:
        """Increment angle for next frame."""
        self.angle = (self.angle + 6) % 360
        self.update()

    def paintEvent(self, event) -> None:
        """Draw the rotating arc spinner."""
        if not self.is_running:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Center and radius based on the spinner size
        cx, cy = self._spinner_size / 2, self._spinner_size / 2
        radius = self._spinner_size / 2 - th.SPINNER_PADDING

        # Draw outer circle (background ring)
        pen = QPen(QColor(th.BORDER_LIGHT), th.SPINNER_LINE_WIDTH)
        painter.setPen(pen)
        painter.drawEllipse(
            int(cx - radius), int(cy - radius),
            int(2 * radius), int(2 * radius)
        )

        # Draw rotating arc (foreground)
        pen = QPen(QColor(th.SPINNER_COLOR), th.SPINNER_LINE_WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Qt uses 1/16 degree units for arc calculations
        painter.drawArc(
            int(cx - radius),
            int(cy - radius),
            int(2 * radius),
            int(2 * radius),
            int(self.angle * 16),
            int(th.SPINNER_ARC_ANGLE * 16)
        )

        painter.end()

    def sizeHint(self) -> QSize:
        """Return preferred size."""
        return QSize(self._spinner_size, self._spinner_size)