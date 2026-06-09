"""
OutputDayCell — single day cell for CalendarMode.OUTPUT.

Day-number colour
-----------------
• Other month  → grey
• Weekend      → red  (col 0 = Sun, col 6 = Sat, decided by caller)
• Unavailable  → red
• Weekday      → black

Badge pills
-----------
Up to MAX_VISIBLE_BADGES exam pills are shown; if more exams exist a
"+N" indicator is appended below them.

• Required exam   → indigo pill
• Elective exam   → green  pill
• Unavailable day → rose   pill  ("Unavailable")
• No exam         → no badge / pill
"""

from __future__ import annotations

from PyQt5.QtCore import QDate, QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from src.styles.calendar_table_style import (
    BADGE_ELECTIVE_STYLE,
    BADGE_REQUIRED_STYLE,
    BADGE_UNAVAILABLE_STYLE,
    CELL_BG,
    ELECT_TEXT,
    REQ_TEXT,
    UNAVAIL_CIRCLE_TEXT,
    UNAVAIL_OUT_TEXT,
)
from src.views.shared_components.calendar_widgets._constants import (
    DAY_COLOR_OTHER,
    DAY_COLOR_WEEKDAY,
    DAY_COLOR_WEEKEND,
)

# Maximum number of exam badges shown before the "+N" indicator
MAX_VISIBLE_BADGES = 2


class OutputDayCell(QFrame):
    """Single day cell for OUTPUT mode."""

    # Emits (list[dict], QPoint) — the full exam list for the day + the
    # global bottom-left corner of the cell so the caller can anchor the popup.
    exam_clicked = pyqtSignal(object, object)

    def __init__(self, qdate: QDate, is_other_month: bool = False,
                 is_weekend: bool = False, parent=None):
        super().__init__(parent)
        self._qdate       = qdate
        self._is_other    = is_other_month
        self._is_weekend  = is_weekend
        self._all_exams: list[dict] = []
        self._exam_data: dict | None = None   # primary exam (first in list)
        self._unavailable = False
        self._setup_ui()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _default_day_color(self) -> str:
        """Determine the default day number colour based on the cell's date."""
        if self._is_other:
            return DAY_COLOR_OTHER
        if self._is_weekend:
            return DAY_COLOR_WEEKEND
        return DAY_COLOR_WEEKDAY

    def _day_num_style(self, color: str) -> str:
        """Generate the stylesheet for the day number label with the given text colour."""
        return f"font-size: 13px; font-weight: 700; color: {color}; background: transparent;"

    def _badge_lbl_style(self, color: str) -> str:
        """Generate the stylesheet for the badge label with the given text colour."""
        return f"font-size: 9px; font-weight: 600; color: {color}; background: transparent;"

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(70, 75)
        self.setStyleSheet(f"QFrame {{ background: {CELL_BG}; }}")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(3)

        # Day number (top-left)
        self._day_num = QLabel(str(self._qdate.day()))
        self._day_num.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._day_num.setStyleSheet(self._day_num_style(self._default_day_color()))
        self._layout.addWidget(self._day_num)

        # Badges container — holds 0‥MAX_VISIBLE_BADGES pills + optional "+N"
        self._badges_area = QFrame()
        self._badges_area.setObjectName("badgesArea")
        self._badges_area.setVisible(False)
        self._badges_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._badges_layout = QVBoxLayout(self._badges_area)
        self._badges_layout.setContentsMargins(0, 0, 0, 0)
        self._badges_layout.setSpacing(2)

        self._layout.addWidget(self._badges_area)
        self._layout.addStretch()

        # Keep references so Qt doesn't GC them
        self._pill_widgets: list[QFrame] = []
        self._more_lbl: QLabel | None = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _clear_badges(self) -> None:
        """Remove all pill widgets and the '+N' label from the badges area."""
        for pill in self._pill_widgets:
            self._badges_layout.removeWidget(pill)
            pill.deleteLater()
        self._pill_widgets.clear()

        if self._more_lbl is not None:
            self._badges_layout.removeWidget(self._more_lbl)
            self._more_lbl.deleteLater()
            self._more_lbl = None

    def _make_pill(self, exam: dict) -> QFrame:
        """Build a single badge pill QFrame for one exam."""
        exam_type = str(exam.get("type", "Obligatory")).strip().lower()
        is_elective = "elective" in exam_type or "elect" in exam_type

        course_num  = str(exam.get("course_number", ""))
        course_name = str(exam.get("course_name", ""))
        if len(course_name) > 12:
            course_name = course_name[:11] + "…"

        badge_text = f"{course_num} {course_name}".strip()

        pill = QFrame()
        pill.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        pill.setStyleSheet(BADGE_ELECTIVE_STYLE if is_elective else BADGE_REQUIRED_STYLE)

        pill_layout = QVBoxLayout(pill)
        pill_layout.setContentsMargins(4, 3, 4, 3)
        pill_layout.setSpacing(0)

        text_color = ELECT_TEXT if is_elective else REQ_TEXT
        lbl = QLabel(badge_text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(self._badge_lbl_style(text_color))
        pill_layout.addWidget(lbl)

        return pill

    def _add_more_label(self, count: int, exam_type: str) -> None:
        """Add a '+N' indicator below the visible pills."""
        exam_type_lower = exam_type.strip().lower()
        is_elective = "elective" in exam_type_lower or "elect" in exam_type_lower
        color = ELECT_TEXT if is_elective else REQ_TEXT
        
        self._more_lbl = QLabel(f"+{count}")
        self._more_lbl.setAlignment(Qt.AlignCenter)
        self._more_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {color}; background: transparent;"
        )
        self._badges_layout.addWidget(self._more_lbl)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_exams(self, exams: list[dict]) -> None:
        """
        Display up to MAX_VISIBLE_BADGES exam pills.
        If len(exams) > MAX_VISIBLE_BADGES, a '+N' label is appended.
        Clicking the cell emits the first exam's data.
        """
        if not exams:
            return

        self._all_exams   = list(exams)
        self._exam_data   = exams[0]
        self._unavailable = False

        self._day_num.setStyleSheet(self._day_num_style(self._default_day_color()))
        self._clear_badges()

        visible = exams[:MAX_VISIBLE_BADGES]
        hidden_count = len(exams) - len(visible)

        for exam in visible:
            pill = self._make_pill(exam)
            self._badges_layout.addWidget(pill)
            self._pill_widgets.append(pill)

        if hidden_count > 0:
            # Use the type of the first hidden exam for colour consistency
            first_hidden_type = str(exams[MAX_VISIBLE_BADGES].get("type", "Obligatory"))
            self._add_more_label(hidden_count, first_hidden_type)

        self._badges_area.setVisible(True)
        self.setCursor(Qt.PointingHandCursor)

    def set_exam(self, exam_data: dict) -> None:
        """Convenience wrapper — single exam (backward compatible)."""
        self.set_exams([exam_data])

    def set_unavailable(self) -> None:
        """Red day number + rose badge pill with 'Unavailable' text."""
        self._unavailable = True
        self._exam_data   = None

        self._day_num.setStyleSheet(self._day_num_style(UNAVAIL_CIRCLE_TEXT))
        self._clear_badges()

        # Single rose pill
        pill = QFrame()
        pill.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        pill.setStyleSheet(BADGE_UNAVAILABLE_STYLE)

        pill_layout = QVBoxLayout(pill)
        pill_layout.setContentsMargins(4, 3, 4, 3)
        pill_layout.setSpacing(0)

        lbl = QLabel("Unavailable")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(self._badge_lbl_style(UNAVAIL_OUT_TEXT))
        pill_layout.addWidget(lbl)

        # Keep public reference expected by tests
        self._badge_lbl = lbl
        self._pill_widgets.append(pill)
        self._badges_layout.addWidget(pill)
        self._badges_area.setVisible(True)
        self.setCursor(Qt.ArrowCursor)

    def set_out_of_range(self) -> None:
        """Gray out a day that is within the displayed month but outside the period range."""
        self._exam_data   = None
        self._unavailable = False
        self._all_exams   = []
        self._day_num.setStyleSheet(self._day_num_style(DAY_COLOR_OTHER))
        self._clear_badges()
        self._badges_area.setVisible(False)
        self.setCursor(Qt.ArrowCursor)

    def clear(self) -> None:
        """Reset to default state: no exams, not unavailable, default day number colour."""
        self._exam_data   = None
        self._unavailable = False
        self._day_num.setStyleSheet(self._day_num_style(self._default_day_color()))
        self._clear_badges()
        self._badges_area.setVisible(False)
        self.setCursor(Qt.ArrowCursor)

    # ── Events ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        """Emit exam_clicked with (all_exams, anchor_point) if left-clicked and has exams."""
        if event.button() == Qt.LeftButton and self._all_exams:
            anchor = self.mapToGlobal(QPoint(0, self.height()))
            self.exam_clicked.emit(self._all_exams, anchor)
        super().mousePressEvent(event)
