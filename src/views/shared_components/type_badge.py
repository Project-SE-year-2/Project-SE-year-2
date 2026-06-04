"""
Badge widget for displaying course type (obligatory/elective).
Used by OutputScreen in DayDetailDialog and ScheduleTableWidget.
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
# Import the theme as 'th' to create a clean, organized namespace for design tokens
import src.styles.theme as th

class TypeBadge(QLabel):
    """
    A small badge label displaying course requirement type.
    """

    def __init__(self, type_str: str, parent=None):
        super().__init__(type_str, parent)
        self.setAlignment(Qt.AlignCenter)
        self._apply_style(type_str.lower())

    def _apply_style(self, type_key: str) -> None:
        """Apply styling based on type using theme tokens."""
        # Selection logic (Mapping)
        styles = {
            "obligatory": (th.OBLIGATORY_BG, th.OBLIGATORY_TEXT, th.OBLIGATORY_BORDER),
            "elective": (th.ELECTIVE_BG, th.ELECTIVE_TEXT, th.ELECTIVE_BORDER)
        }
        
        # Get styles, default to neutral if type not found
        bg_color, text_color, border_color = styles.get(
            type_key, (th.NEUTRAL_BG, th.NEUTRAL_TEXT, th.NEUTRAL_BORDER)
        )

        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border: {th.BADGE_BORDER_WIDTH}px solid {border_color};
                border-radius: {th.BADGE_RADIUS}px;
                padding: {th.BADGE_PADDING_Y}px {th.BADGE_PADDING_X}px;
                font-weight: {th.BADGE_FONT_WEIGHT};
                font-size: {th.BADGE_FONT_SIZE}px;
            }}
        """)

    def set_type(self, type_str: str) -> None:
        """Update badge text and style dynamically."""
        self.setText(type_str)
        self._apply_style(type_str.lower())