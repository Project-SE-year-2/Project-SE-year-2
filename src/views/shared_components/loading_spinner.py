"""
Animated loading spinner widget shown during schedule generation.
Used by InputScreen during generate() processing.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QPainter, QColor, QPen
import src.styles.theme as th
from src.styles.loading_spinner_style import SPINNER_BASE_STYLE


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
        self._spinner_size = size if size is not None else th.SPINNER_SIZE
        self.angle = 0
        self.is_running = False

        self.setFixedSize(self._spinner_size, self._spinner_size)

        # Enforce transparent background and ignore global stylesheet cascades
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setStyleSheet(SPINNER_BASE_STYLE)

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

        cx, cy = self._spinner_size / 2, self._spinner_size / 2
        radius = self._spinner_size / 2 - th.SPINNER_PADDING

        pen = QPen(QColor(th.BORDER_LIGHT), th.SPINNER_LINE_WIDTH)
        painter.setPen(pen)
        painter.drawEllipse(
            int(cx - radius), int(cy - radius),
            int(2 * radius), int(2 * radius)
        )

        pen = QPen(QColor(th.SPINNER_COLOR), th.SPINNER_LINE_WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        painter.drawArc(
            int(cx - radius),
            int(cy - radius),
            int(2 * radius),
            int(2 * radius),
            int(self.angle * th.QT_ANGLE_UNIT),
            int(th.SPINNER_ARC_ANGLE * th.QT_ANGLE_UNIT)
        )

        painter.end()

    def sizeHint(self) -> QSize:
        """Return preferred size."""
        return QSize(self._spinner_size, self._spinner_size)
