"""
ranking_config_widget.py
-------------------------
Placeholder container for ranking priority controls.

Full implementation (drag-and-drop metric ordering list) is delivered
in EP-112.  This stub lets SettingsScreen instantiate and lay out
the panel without depending on EP-112 being merged first.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class RankingConfigWidget(QWidget):
    """Right panel of SettingsScreen — metric ranking priority controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("Ranking Priority")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Placeholder label — replaced by EP-112 drag-and-drop list.
        placeholder = QLabel("Ranking controls will appear here.")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #94A3B8;")
        layout.addWidget(placeholder, stretch=1)
