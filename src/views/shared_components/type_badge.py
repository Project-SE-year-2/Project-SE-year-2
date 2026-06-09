"""
Badge widget for displaying course type (obligatory/elective).
Used by OutputScreen in DayDetailDialog and ScheduleTableWidget.
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
import src.styles.theme as th
from src.styles.type_badge_style import type_badge_style


class TypeBadge(QLabel):
    """
    A small badge label displaying course requirement type.
    """

    def __init__(self, type_str: str, parent=None):
        super().__init__(type_str, parent)
        self.setAlignment(Qt.AlignCenter)
        self._apply_style(type_str.lower())

    def _apply_style(self, type_key: str) -> None:
        styles = {
            "obligatory": (th.OBLIGATORY_BG, th.OBLIGATORY_TEXT, th.OBLIGATORY_BORDER),
            "elective": (th.ELECTIVE_BG, th.ELECTIVE_TEXT, th.ELECTIVE_BORDER)
        }

        bg_color, text_color, border_color = styles.get(
            type_key, (th.NEUTRAL_BG, th.NEUTRAL_TEXT, th.NEUTRAL_BORDER)
        )

        self.setStyleSheet(type_badge_style(bg_color, text_color, border_color))

    def set_type(self, type_str: str) -> None:
        """Update badge text and style dynamically."""
        self.setText(type_str)
        self._apply_style(type_str.lower())
