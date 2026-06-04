"""
Inline error banner component.
Provides a standardized way to display dismissible error alerts.
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
# Import the theme as 'th' to create a clean, organized namespace for design tokens
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
        """Initialize UI layout and component styling."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            th.BANNER_PADDING_X, 
            th.BANNER_PADDING_Y, 
            th.BANNER_PADDING_RIGHT, 
            th.BANNER_PADDING_Y
        )
        layout.setSpacing(th.BANNER_SPACING)

        # Message display
        self.message_label = QLabel()
        self.message_label.setStyleSheet(
            f"color: {th.ERROR_TEXT}; "
            f"font-size: {th.FONT_SIZE_MD}px; "
            f"font-weight: {th.BANNER_FONT_WEIGHT};"
        )
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)

        # Dismiss button
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setFixedSize(th.BANNER_BTN_SIZE, th.BANNER_BTN_SIZE)
        dismiss_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: transparent; 
                color: {th.ERROR_TEXT}; 
                border: none; 
                font-size: {th.BANNER_BTN_FONT_SIZE}px; 
                font-weight: {th.BANNER_BTN_FONT_WEIGHT}; 
            }}
            QPushButton:hover {{ 
                background-color: {th.ERROR_BG}; 
                border-radius: {th.BANNER_BUTTON_RADIUS}px; 
            }}
        """)
        dismiss_btn.clicked.connect(self._on_dismiss)
        layout.addWidget(dismiss_btn)

        # Container styling
        self.setStyleSheet(f"""
            ErrorBanner {{
                background-color: {th.ERROR_BG};
                border: {th.BANNER_BORDER_WIDTH}px solid {th.ERROR_BORDER};
                border-radius: {th.BANNER_BORDER_RADIUS}px;
            }}
        """)

    def show_error(self, message: str) -> None:
        """Updates the error message and displays the banner."""
        formatted_text = f'<span style="color: {th.ICON_ERROR}; font-size: {th.ERROR_ICON_SIZE}px;">●</span>  {message}'
        self.message_label.setText(formatted_text)
        self.show()

    def hide_error(self) -> None:
        """Clears the message and hides the banner."""
        self.message_label.setText("")
        self.hide()

    def _on_dismiss(self) -> None:
        """Handles internal close event and notifies external listeners."""
        self.hide_error()
        self.dismissed.emit()