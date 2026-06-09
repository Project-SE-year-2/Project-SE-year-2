"""
Inline error banner component.
Provides a standardized way to display dismissible error alerts.
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal
from src.styles.error_banner_style import (
    BANNER_MESSAGE_STYLE,
    BANNER_DISMISS_BTN_STYLE,
    BANNER_CONTAINER_STYLE,
    banner_error_text,
)
import src.styles.theme as th


class ErrorBanner(QWidget):
    """
    A dismissible error banner.

    Signals:
        dismissed: Emitted when the user closes the banner via the 'X' button.
    """

    # Signal used for decoupled communication: allows parent components to react
    # to user actions (like closing the error) without direct dependency.
    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            th.BANNER_PADDING_X,
            th.BANNER_PADDING_Y,
            th.BANNER_PADDING_RIGHT,
            th.BANNER_PADDING_Y
        )
        layout.setSpacing(th.BANNER_SPACING)

        self.message_label = QLabel()
        self.message_label.setStyleSheet(BANNER_MESSAGE_STYLE)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)

        dismiss_btn = QPushButton("✕")
        dismiss_btn.setFixedSize(th.BANNER_BTN_SIZE, th.BANNER_BTN_SIZE)
        dismiss_btn.setStyleSheet(BANNER_DISMISS_BTN_STYLE)
        dismiss_btn.clicked.connect(self._on_dismiss)
        layout.addWidget(dismiss_btn)

        self.setStyleSheet(BANNER_CONTAINER_STYLE)

    def show_error(self, message: str) -> None:
        """Updates the error message and displays the banner."""
        self.message_label.setText(banner_error_text(message))
        self.show()

    def hide_error(self) -> None:
        """Clears the message and hides the banner."""
        self.message_label.setText("")
        self.hide()

    def _on_dismiss(self) -> None:
        """Handles internal close event and notifies external listeners."""
        self.hide_error()
        self.dismissed.emit()
