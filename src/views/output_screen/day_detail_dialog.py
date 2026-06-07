"""
DayDetailDialog — popup shown when the user clicks an exam badge.

Each exam is a collapsible card row:
  ┌────────────────────────────────────────────────────┐
  │ [CODE]  Course Name                    [Type badge] │
  │ Programs Affected (N)                           ▲/▼ │
  │   • Full Program Name (AB)                       AB  │
  │   • …                                                │
  └────────────────────────────────────────────────────┘

Left border colour: indigo for Required, green for Elective.
Programs section is expanded by default; the arrow toggles it.
"""

from __future__ import annotations

from datetime import date as date_type

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.styles.day_detail_dialog_style import (
    CARD_STYLE,
    CLOSE_BTN_STYLE,
    COURSE_CODE_ELECTIVE_STYLE,
    COURSE_CODE_REQUIRED_STYLE,
    COURSE_NAME_INLINE_STYLE,
    EXAM_ROW_ELECTIVE_BORDER,
    EXAM_ROW_REQUIRED_BORDER,
    FOOTER_STYLE,
    MINI_BADGE_ELECTIVE_STYLE,
    MINI_BADGE_REQUIRED_STYLE,
    PROGRAM_ABBR_RIGHT_STYLE,
    PROGRAM_BULLET_STYLE,
    PROGRAMS_COUNT_STYLE,
    TITLE_STYLE,
    exam_row_style,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_date(value) -> str:
    """Format an exam date as DD/MM/YYYY; passes strings through unchanged."""
    if isinstance(value, date_type):
        return value.strftime("%d/%m/%Y")
    return str(value) if value else "—"


def _abbrev(name: str) -> str:
    """
    Build a short abbreviation from a program name.
    Multi-word names → initials ('Computer Science' → 'CS').
    Single-word / numeric IDs → first 2 chars ('83101' → '83').
    """
    words = name.split()
    if len(words) >= 2:
        return "".join(w[0].upper() for w in words if w)
    return name[:2].upper() if name else "?"


def _is_elective(exam: dict) -> bool:
    t = str(exam.get("type", "Obligatory")).strip().lower()
    return "elective" in t or "elect" in t


# ---------------------------------------------------------------------------
# _ExamRow — one collapsible card per exam
# ---------------------------------------------------------------------------

class _ExamRow(QFrame):
    """
    Card row for a single exam.

    Layout:
      top row : [CODE]  Name                    [Type badge]
      prog row: Programs Affected (N)
      list    : • Full Name (AB)                          AB
                  …
    """

    def __init__(self, exam: dict, program_names: dict[str, str], parent=None):
        super().__init__(parent)
        elective   = _is_elective(exam)
        border_clr = EXAM_ROW_ELECTIVE_BORDER if elective else EXAM_ROW_REQUIRED_BORDER
        self.setStyleSheet(exam_row_style(border_clr))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(6)

        # ── Top row: code  name  |  badge ────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(6)
        top.setContentsMargins(0, 0, 0, 0)

        code_lbl = QLabel(str(exam.get("course_number", "—")))
        code_lbl.setStyleSheet(
            COURSE_CODE_ELECTIVE_STYLE if elective else COURSE_CODE_REQUIRED_STYLE
        )

        name_lbl = QLabel(str(exam.get("course_name", "—")))
        name_lbl.setStyleSheet(COURSE_NAME_INLINE_STYLE)

        badge_lbl = QLabel("Elective" if elective else "Required")
        badge_lbl.setAlignment(Qt.AlignCenter)
        badge_lbl.setStyleSheet(
            MINI_BADGE_ELECTIVE_STYLE if elective else MINI_BADGE_REQUIRED_STYLE
        )

        top.addWidget(code_lbl)
        top.addSpacing(4)
        top.addWidget(name_lbl)
        top.addStretch()
        top.addWidget(badge_lbl)
        outer.addLayout(top)

        # ── "Programs Affected (N)" label ────────────────────────────
        programs = list(exam.get("programs") or [])
        n = len(programs)

        count_lbl = QLabel(f"Programs Affected ({n})")
        count_lbl.setStyleSheet(PROGRAMS_COUNT_STYLE)
        outer.addWidget(count_lbl)

        # ── Program bullet list (always visible) ──────────────────────
        for pid in programs:
            display_full = program_names.get(str(pid), str(pid))
            abbr         = _abbrev(display_full)

            item_row = QHBoxLayout()
            item_row.setContentsMargins(0, 0, 0, 0)
            item_row.setSpacing(4)

            bullet = QLabel(f"• {display_full} ({abbr})")
            bullet.setStyleSheet(PROGRAM_BULLET_STYLE)

            right = QLabel(abbr)
            right.setStyleSheet(PROGRAM_ABBR_RIGHT_STYLE)
            right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            item_row.addWidget(bullet)
            item_row.addStretch()
            item_row.addWidget(right)
            outer.addLayout(item_row)


# ---------------------------------------------------------------------------
# DayDetailDialog
# ---------------------------------------------------------------------------

class DayDetailDialog(QDialog):
    """
    Frameless modal dialog listing all exams for a given day.

    Args:
        exams:         list of exam dicts for the clicked day.
        exam_date:     the date shown in the title.
        program_names: optional {program_id: display_name} mapping.
        anchor_pos:    global QPoint to position the dialog (bottom of clicked cell).
        parent:        optional parent widget.
    """

    def __init__(
        self,
        exams: list[dict],
        exam_date=None,
        program_names: dict[str, str] | None = None,
        anchor_pos: QPoint | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._exams         = exams or []
        self._exam_date     = exam_date
        self._program_names = program_names or {}
        self._build_ui()

        if anchor_pos is not None:
            self.move(anchor_pos)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(340)
        self.setMaximumWidth(440)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Card ──────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("dialogCard")
        card.setStyleSheet(CARD_STYLE)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)

        # ── Header: "Exams on DD/MM/YYYY"  [✕] ───────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(f"Exams on {_format_date(self._exam_date)}")
        title_lbl.setStyleSheet(TITLE_STYLE)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        close_btn.clicked.connect(self.close)

        header.addWidget(title_lbl)
        header.addStretch()
        header.addWidget(close_btn)
        card_layout.addLayout(header)

        # ── Scrollable exam rows ──────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")
        scroll.setMaximumHeight(420)

        rows_widget = QWidget()
        rows_widget.setStyleSheet("background: transparent;")
        rows_layout = QVBoxLayout(rows_widget)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(8)

        for exam in self._exams:
            rows_layout.addWidget(_ExamRow(exam, self._program_names))

        rows_layout.addStretch()
        scroll.setWidget(rows_widget)
        card_layout.addWidget(scroll)

        # ── Footer: "🔗  N exams on this day" ────────────────────────
        n     = len(self._exams)
        noun  = "exam" if n == 1 else "exams"
        footer = QLabel(f"🔗  {n} {noun} on this day")
        footer.setStyleSheet(FOOTER_STYLE)
        card_layout.addWidget(footer)

        outer.addWidget(card)

    # ------------------------------------------------------------------
    # Helpers (static so tests can call DayDetailDialog._format_date)
    # ------------------------------------------------------------------

    @staticmethod
    def _format_date(value) -> str:
        """Format an exam date as DD/MM/YYYY; passes strings through unchanged."""
        return _format_date(value)
