"""
settings_screen.py
------------------
Root container for the Settings view (QStackedWidget index 2).

Layout
------
  ┌─────────────────────────────────────────────┐
  │  ← Back          Settings                   │  header
  ├──────────────────┬──────────────────────────┤
  │ ConstraintConfig │   RankingConfig           │  panels
  │    Widget        │     Widget                │
  └──────────────────┴──────────────────────────┘

Signals
-------
  switch_to_input — emitted when the user clicks the Back button.
                    MainWindow connects this to _show_input_screen().
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame,
)
from PyQt5.QtCore import pyqtSignal, Qt

from src.views.settings_screen.constraint_config_widget import ConstraintConfigWidget
from src.views.settings_screen.ranking_config_widget import RankingConfigWidget
from src.models.constraint_settings import ConstraintSettings


class SettingsScreen(QWidget):
    """
    Structural canvas that hosts ConstraintConfigWidget and RankingConfigWidget
    side-by-side, with a header bar providing back-navigation.
    """

    switch_to_input = pyqtSignal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        # Keep a reference so sub-widgets added in EP-109/EP-112 can use it.
        self.service = service
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_divider())
        root.addLayout(self._make_panels(), stretch=1)

    def _make_header(self) -> QWidget:
        """Top bar with a back button on the left and a centred title."""
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet("background-color: #FFFFFF;")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedWidth(80)
        self.back_btn.setStyleSheet(
            "QPushButton { border: none; color: #3B82F6; font-size: 14px; }"
            "QPushButton:hover { color: #1D4ED8; }"
        )
        self.back_btn.clicked.connect(self.switch_to_input.emit)

        title = QLabel("Settings")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B;")

        # Invisible spacer on the right keeps the title visually centred.
        spacer = QWidget()
        spacer.setFixedWidth(80)

        layout.addWidget(self.back_btn)
        layout.addWidget(title, stretch=1)
        layout.addWidget(spacer)

        return header

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        return line

    def _make_panels(self) -> QHBoxLayout:
        """Two sub-panels placed side-by-side without overlap."""
        panels = QHBoxLayout()
        panels.setContentsMargins(16, 16, 16, 16)
        panels.setSpacing(16)

        self.constraint_panel = ConstraintConfigWidget()
        self.ranking_panel = RankingConfigWidget()

        panels.addWidget(self.constraint_panel, stretch=1)

        # Vertical separator between the two panels.
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #E2E8F0;")
        panels.addWidget(sep)

        panels.addWidget(self.ranking_panel, stretch=1)

        return panels


    def get_constraint_settings(self) -> ConstraintSettings:
        """Return typed constraint settings collected from the constraint panel."""
        return self.constraint_panel.get_settings()

    def set_constraint_settings(self, settings: ConstraintSettings) -> None:
        """Load typed constraint settings into the constraint panel."""
        self.constraint_panel.set_settings(settings)