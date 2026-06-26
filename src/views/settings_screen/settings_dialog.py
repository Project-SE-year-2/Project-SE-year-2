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
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame,
)
from PyQt5.QtCore import pyqtSignal, Qt

from src.views.settings_screen.constraint_config_widget import ConstraintConfigWidget
from src.models.constraint_settings import ConstraintSettings


class SettingsDialog(QDialog):
    """
    Dialog canvas that hosts ConstraintConfigWidget with a header bar.
    """

    settings_confirmed = pyqtSignal()

    def __init__(self, service, parent=None):
        # Qt.Tool makes it a floating tool window without standard OS window controls,
        # or we can use Qt.FramelessWindowHint | Qt.Dialog to remove the OS title bar entirely.
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; }")
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
        """Top bar with a centred title and cancel/apply buttons."""
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet("background-color: #FFFFFF;")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedWidth(80)
        self.cancel_btn.setStyleSheet(
            "QPushButton { border: none; color: #64748B; font-size: 14px; }"
            "QPushButton:hover { color: #475569; }"
        )
        self.cancel_btn.clicked.connect(self.reject)

        title = QLabel("Settings")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B;")

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setFixedWidth(100)
        self.apply_btn.setStyleSheet(
            "QPushButton { background-color: #3B82F6; color: white; border-radius: 6px; font-size: 16px; font-weight: bold; padding: 6px; }"
            "QPushButton:hover { background-color: #2563EB; }"
        )
        self.apply_btn.clicked.connect(self._on_apply)

        layout.addWidget(self.cancel_btn)
        layout.addWidget(title, stretch=1)
        layout.addWidget(self.apply_btn)

        return header

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        return line

    def _make_panels(self) -> QHBoxLayout:
        """Constraint settings panel."""
        panels = QHBoxLayout()
        panels.setContentsMargins(16, 16, 16, 16)
        panels.setSpacing(16)

        self.constraint_panel = ConstraintConfigWidget()

        panels.addWidget(self.constraint_panel, stretch=1)

        return panels


    def _on_apply(self) -> None:
        """Private click handler for the Apply button.

        Emits settings_confirmed and accepts the dialog so MainWindow can read constraint settings.
        """
        self.settings_confirmed.emit()
        self.accept()

    def get_constraint_settings(self) -> ConstraintSettings:
        """Return typed constraint settings collected from the constraint panel."""
        return self.constraint_panel.get_settings()

    def set_constraint_settings(self, settings: ConstraintSettings) -> None:
        """Load typed constraint settings into the constraint panel."""
        self.constraint_panel.set_settings(settings)
