from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy,
)

import src.styles.theme as th
from src.styles.study_programs_style import STUDY_PROGRAMS_STYLE

# Maps raw type strings to badge object name
_TYPE_BADGE = {
    "obligatory": "typeBadgeObligatory",
    "elective":   "typeBadgeElective",
}


class CourseDetailWidget(QWidget):
    """
    Right column of the Study Programs tab.
    Displays full details of the currently selected course row.

    Fields shown (from service dict):
        number   → Course Code
        name     → Course Name
        type     → Course Type  (colored badge)
        year     → part of Semester field
        semester → part of Semester field
        evaluation → Evaluation
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("courseDetailPanel")
        self.setStyleSheet(STUDY_PROGRAMS_STYLE)
        self._build_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def show_course(self, course: dict) -> None:
        """Populate the panel with data from one course dict."""
        self._empty_lbl.setVisible(False)
        self._detail_frame.setVisible(True)

        name     = str(course.get("name",       ""))
        code     = str(course.get("number",     "—"))
        type_str = str(course.get("type",       "—"))
        year     = course.get("year",      "")
        semester = course.get("semester",  "")
        evaluation = str(course.get("evaluation", "—"))

        sem_display = (
            f"Year {year} - Semester {semester}"
            if year or semester else "—"
        )

        self._course_title.setText(name)

        # Type badge
        badge_key = type_str.lower()
        self._type_badge.setObjectName(
            _TYPE_BADGE.get(badge_key, "typeBadgeElective")
        )
        self._type_badge.setText(type_str)
        # Force stylesheet re-application after object-name change
        self._type_badge.style().unpolish(self._type_badge)
        self._type_badge.style().polish(self._type_badge)

        self._val_code.setText(code)
        self._val_name.setText(name)
        self._val_type.setText(type_str)
        self._val_semester.setText(sem_display)
        self._val_evaluation.setText(evaluation)

    def clear(self) -> None:
        self._detail_frame.setVisible(False)
        self._empty_lbl.setVisible(True)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(th.SPACING_LARGE, th.SPACING_LARGE,
                                 th.SPACING_LARGE, th.SPACING_LARGE)
        outer.setSpacing(th.SPACING_MEDIUM)

        # Panel title
        title = QLabel("Course Details")
        title.setObjectName("detailTitle")
        outer.addWidget(title)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {th.BORDER_LIGHT};")
        outer.addWidget(line)

        # ── Detail frame (hidden when empty) ───────────────────────────────
        self._detail_frame = QWidget()
        self._detail_frame.setStyleSheet("QWidget { background: transparent; }")
        detail_l = QVBoxLayout(self._detail_frame)
        detail_l.setContentsMargins(0, 0, 0, 0)
        detail_l.setSpacing(th.SPACING_MEDIUM)

        # Course name heading
        self._course_title = QLabel("")
        self._course_title.setObjectName("detailCourseTitle")
        self._course_title.setWordWrap(True)
        detail_l.addWidget(self._course_title)

        # Type badge
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        self._type_badge = QLabel("")
        self._type_badge.setObjectName("typeBadgeObligatory")
        self._type_badge.setFixedHeight(24)
        self._type_badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        badge_row.addWidget(self._type_badge)
        badge_row.addStretch()
        detail_l.addLayout(badge_row)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet(f"color: {th.BORDER_LIGHT};")
        detail_l.addWidget(div2)

        # Field rows
        self._val_code       = self._add_field(detail_l, "Course Code")
        self._val_name       = self._add_field(detail_l, "Course Name")
        self._val_type       = self._add_field(detail_l, "Course Type")
        self._val_semester   = self._add_field(detail_l, "Semester")
        self._val_evaluation = self._add_field(detail_l, "Evaluation")

        detail_l.addStretch()
        self._detail_frame.setVisible(False)
        outer.addWidget(self._detail_frame, stretch=1)

        # ── Empty state ────────────────────────────────────────────────────
        self._empty_lbl = QLabel("Select a course to view its details")
        self._empty_lbl.setObjectName("detailEmpty")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        outer.addWidget(self._empty_lbl, stretch=1)

    def _add_field(self, layout: QVBoxLayout, label_text: str) -> QLabel:
        """Add a label+value pair and return the value QLabel."""
        block = QWidget()
        block.setStyleSheet("QWidget { background: transparent; }")
        bl = QVBoxLayout(block)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(2)

        lbl = QLabel(label_text)
        lbl.setObjectName("detailFieldLabel")

        val = QLabel("—")
        val.setObjectName("detailFieldValue")
        val.setWordWrap(True)

        bl.addWidget(lbl)
        bl.addWidget(val)
        layout.addWidget(block)
        return val
