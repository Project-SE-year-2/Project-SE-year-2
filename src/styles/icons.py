"""
Icon registry for the application.

All icon file paths are defined here so no other module contains
hard-coded path strings.  Use ``load_pixmap(name, size)`` to get
a scaled QPixmap ready to drop into a QLabel.

Icon names
----------
ICON_FILE          – document / courses file
ICON_CALENDAR      – calendar / dates file
ICON_CALENDAR_PLUS – calendar with plus / Generate Schedule button
ICON_DOWNLOAD      – download arrow / Download Schedule button
ICON_FALL          – autumn / FALL semester
ICON_SPRING        – spring / SPRING semester
ICON_SUMMER        – sun / SUMMER semester
ICON_SEARCH        – magnifying glass
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

# ── Icon name constants ────────────────────────────────────────────────────────

ICON_FILE          = "file"
ICON_CALENDAR      = "calendar"
ICON_CALENDAR_PLUS = "calendar_plus"
ICON_DOWNLOAD      = "download"
ICON_FALL          = "fall"
ICON_SPRING        = "spring"
ICON_SUMMER        = "summer"
ICON_SEARCH        = "search1"

# ── Internal: map name → filename ─────────────────────────────────────────────

_ICON_DIR = Path(__file__).parent.parent.parent / "icon"

_ICON_FILES: dict[str, str] = {
    ICON_FILE:          "file.png",
    ICON_CALENDAR:      "calendar.png",
    ICON_CALENDAR_PLUS: "calendar_plus.png",
    ICON_DOWNLOAD:      "download.png",
    ICON_FALL:          "fall.png",
    ICON_SPRING:        "spring.png",
    ICON_SUMMER:        "summer.png",
    ICON_SEARCH:        "search1.png",
}

# ── Semester → icon name mapping (useful in output widgets) ───────────────────

SEMESTER_ICON: dict[str, str] = {
    "FALL":   ICON_FALL,
    "SPRING": ICON_SPRING,
    "SUMMER": ICON_SUMMER,
}


# ── Public helper ──────────────────────────────────────────────────────────────

def load_pixmap(name: str, size: int = 32) -> QPixmap:
    """
    Return a QPixmap for *name* scaled to *size* × *size* pixels.

    If the file is missing or unreadable a null QPixmap is returned
    (the caller's QLabel will simply stay blank).
    """
    filename = _ICON_FILES.get(name)
    if not filename:
        return QPixmap()

    path = str(_ICON_DIR / filename)
    pix  = QPixmap(path)
    if pix.isNull() or size <= 0:
        return pix

    return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
