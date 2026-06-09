"""
Styled button variants: Primary, Secondary, Danger.
Used across both InputScreen and OutputScreen for consistent styling.
"""

from PyQt5.QtWidgets import QPushButton
from src.styles.buttons_style import PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, DANGER_BUTTON_STYLE


class PrimaryButton(QPushButton):
    """Primary action button (solid indigo surface with bold text)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(PRIMARY_BUTTON_STYLE)


class SecondaryButton(QPushButton):
    """Secondary action button (outlined border with transparent background)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(SECONDARY_BUTTON_STYLE)


class DangerButton(QPushButton):
    """Destructive action button (solid red surface for risky actions)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(DANGER_BUTTON_STYLE)
