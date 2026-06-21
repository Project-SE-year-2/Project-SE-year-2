"""
constraint_config_widget.py
----------------------------
Placeholder container for constraint configuration controls.

Full implementation (checkboxes + spinboxes per constraint type) is
delivered in EP-109.  This stub lets SettingsScreen instantiate and
lay out the panel without depending on EP-109 being merged first.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class ConstraintConfigWidget(QWidget):
    """Left panel of SettingsScreen — constraint enable/value controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
    # No public methods yet — EP-109 will add getters/setters for each constraint.
    def _build_ui(self):
        # Build a simple placeholder UI until EP-109 delivers the real controls.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        title = QLabel("Constraint Settings")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Placeholder label — replaced by EP-109 checkboxes + spinboxes.
        placeholder = QLabel("Constraint controls will appear here.")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #94A3B8;")
        layout.addWidget(placeholder, stretch=1)
