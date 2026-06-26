"""
SemesterTabsWidget
==================
Row of three large selectable semester cards: FALL · SPRING · SUMMER.

Each card shows a coloured icon + bold semester name.
Clicking a card emits semester_changed(str) with the semester id.

Signals
-------
semester_changed(str)  — "FALL" | "SPRING" | "SUMMER"

Public API
----------
set_selected(semester: str)   — highlight a card without emitting a signal
current_semester() -> str     — return the currently selected semester id
set_enabled_all(enabled: bool)— disable/enable all tabs (during loading)
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.styles.icons import load_pixmap, ICON_FALL, ICON_SPRING, ICON_SUMMER


# ── Semester definitions ──────────────────────────────────────────────────────

_SEMESTERS = [
    {"id": "FALL",   "icon": ICON_FALL,   "color": "#2563EB", "bg_sel": "#EFF6FF"},
    {"id": "SPRING", "icon": ICON_SPRING, "color": "#16A34A", "bg_sel": "#F0FDF4"},
    {"id": "SUMMER", "icon": ICON_SUMMER, "color": "#F59E0B", "bg_sel": "#FFF7ED"},
]

# ── Individual tab card ───────────────────────────────────────────────────────

_CARD_NORMAL = (
    "QFrame#semTab {{"
    "  background: #FFFFFF;"
    "  border: 1.5px solid #E5E7EB;"
    "  border-radius: 14px;"
    "}}"
    "QFrame#semTab:hover {{"
    "  border-color: #93C5FD;"
    "  background: #FAFBFF;"
    "}}"
)

_CARD_SELECTED = (
    "QFrame#semTab {{"
    "  background: {bg};"
    "  border: 2px solid {color};"
    "  border-radius: 14px;"
    "}}"
)

_CARD_DISABLED = (
    "QFrame#semTab {{"
    "  background: #F9FAFB;"
    "  border: 1.5px solid #E5E7EB;"
    "  border-radius: 14px;"
    "}}"
)


class _SemesterTabCard(QFrame):
    """Single clickable semester card."""

    clicked = pyqtSignal(str)   # semester id

    def __init__(self, meta: dict, parent=None):
        super().__init__(parent)
        self._id      = meta["id"]
        self._color   = meta["color"]
        self._bg_sel  = meta["bg_sel"]
        self._selected = False
        self._enabled  = True

        self.setObjectName("semTab")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(68)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        # Icon label — PNG image from the icon registry
        self._icon_lbl = QLabel()
        self._icon_lbl.setStyleSheet("background: transparent;")
        self._icon_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        pix = load_pixmap(meta["icon"], size=22)
        if not pix.isNull():
            self._icon_lbl.setPixmap(pix)
        # layout.addWidget(self._icon_lbl)

        # Semester name — uses accent colour
        self._name_lbl = QLabel(meta["id"])
        self._name_lbl.setStyleSheet(
            f"font-size: 24px; font-weight: 800; color: {meta['color']};"
            f" letter-spacing: 1px; background: transparent;"
        )
        self._name_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(self._name_lbl)

        self._apply_style()

    # ------------------------------------------------------------------

    def _apply_style(self) -> None:
        if not self._enabled:
            self.setStyleSheet(_CARD_DISABLED)
        elif self._selected:
            self.setStyleSheet(
                _CARD_SELECTED.format(color=self._color, bg=self._bg_sel)
            )
        else:
            self.setStyleSheet(_CARD_NORMAL)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    def set_card_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        self._apply_style()

    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._enabled:
            self.clicked.emit(self._id)
        super().mousePressEvent(event)


# ── SemesterTabsWidget ────────────────────────────────────────────────────────

class SemesterTabsWidget(QWidget):
    """Horizontal row of FALL / SPRING / SUMMER selector cards."""

    semester_changed = pyqtSignal(str)   # "FALL" | "SPRING" | "SUMMER"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current: str = "FALL"
        self._cards: dict[str, _SemesterTabCard] = {}
        self._setup_ui()

    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)

        for meta in _SEMESTERS:
            card = _SemesterTabCard(meta)
            card.clicked.connect(self._on_card_clicked)
            self._cards[meta["id"]] = card
            row.addWidget(card)

        # Mark default selection without emitting
        self._cards["FALL"].set_selected(True)

    def _on_card_clicked(self, semester: str) -> None:
        if semester == self._current:
            return
        self.set_selected(semester)
        self.semester_changed.emit(semester)

    # ------------------------------------------------------------------
    # Public API

    def set_selected(self, semester: str) -> None:
        """Visually select a tab without emitting semester_changed."""
        for sid, card in self._cards.items():
            card.set_selected(sid == semester)
        self._current = semester

    def current_semester(self) -> str:
        return self._current

    def set_enabled_all(self, enabled: bool) -> None:
        """Enable or disable all tab cards (use during loading)."""
        for card in self._cards.values():
            card.set_card_enabled(enabled)
