"""
Tests for CalendarTableWidget (EP-36 / EP-47).
Covers both INPUT mode (period selector) and OUTPUT mode (schedule viewer).
"""

import sys
import unittest
from datetime import date as py_date

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QApplication, QLabel

app = QApplication.instance() or QApplication(sys.argv)

from src.models.enums import CalendarMode
from src.views.shared_components.calendar_table_widget import CalendarTableWidget
from src.views.shared_components.calendar_widgets import InputDayCell, OutputDayCell


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SENTINEL = object()   # used so exam_date=None can be passed explicitly


def _make_exam(course_number="CS201", course_name="Data Structures",
               exam_type="Obligatory", exam_date=_SENTINEL):
    return {
        "course_number": course_number,
        "course_name":   course_name,
        "type":          exam_type,
        "programs":      ["83101"],
        # Use default date only when caller didn't supply exam_date at all
        "exam_date":     py_date(2026, 9, 2) if exam_date is _SENTINEL else exam_date,
        "semester":      "FALL",
        "moed":          "A",
    }


# ===========================================================================
# INPUT mode — widget level
# ===========================================================================

class TestInputConstruction(unittest.TestCase):

    def setUp(self):
        self.w = CalendarTableWidget(CalendarMode.INPUT)

    def test_mode_is_input(self):
        self.assertEqual(self.w._mode, CalendarMode.INPUT)

    def test_has_start_date_edit(self):
        self.assertTrue(hasattr(self.w, "_start_edit"))

    def test_has_end_date_edit(self):
        self.assertTrue(hasattr(self.w, "_end_edit"))

    def test_has_two_month_grids(self):
        self.assertEqual(len(self.w._month_grids), 2)

    def test_initial_unavailable_empty(self):
        self.assertEqual(len(self.w.get_unavailable_days()), 0)

    def test_has_save_button(self):
        self.assertTrue(hasattr(self.w, "save_btn"))

    def test_output_mode_has_no_save_button(self):
        w_out = CalendarTableWidget(CalendarMode.OUTPUT)
        self.assertFalse(hasattr(w_out, "save_btn"))


class TestSaveButton(unittest.TestCase):

    def setUp(self):
        self.w = CalendarTableWidget(CalendarMode.INPUT)
        self.w.set_date_range(QDate(2026, 6, 1), QDate(2026, 7, 31))
        self.w.set_unavailable_days([QDate(2026, 6, 10)])

    def test_save_emits_start_date(self):
        received = []
        self.w.save_requested.connect(lambda s, e, u: received.append(s))
        self.w.save_btn.click()
        self.assertEqual(received[0], QDate(2026, 6, 1))

    def test_save_emits_end_date(self):
        received = []
        self.w.save_requested.connect(lambda s, e, u: received.append(e))
        self.w.save_btn.click()
        self.assertEqual(received[0], QDate(2026, 7, 31))

    def test_save_emits_unavailable_set(self):
        received = []
        self.w.save_requested.connect(lambda s, e, u: received.append(u))
        self.w.save_btn.click()
        self.assertIn(QDate(2026, 6, 10), received[0])

    def test_save_not_emitted_when_no_range(self):
        w = CalendarTableWidget(CalendarMode.INPUT)   # no range set
        received = []
        w.save_requested.connect(lambda s, e, u: received.append(True))
        w.save_btn.click()
        self.assertEqual(received, [])

    def test_save_emitted_copy_of_unavailable(self):
        """The emitted set must be a copy — mutating it should not affect internal state."""
        received = []
        self.w.save_requested.connect(lambda s, e, u: received.append(u))
        self.w.save_btn.click()
        received[0].add(QDate(2026, 6, 20))   # mutate the copy
        self.assertEqual(len(self.w.get_unavailable_days()), 1)  # internal unchanged


class TestInputDateRange(unittest.TestCase):

    def setUp(self):
        self.w     = CalendarTableWidget(CalendarMode.INPUT)
        self.start = QDate(2026, 6, 1)
        self.end   = QDate(2026, 7, 31)
        self.w.set_date_range(self.start, self.end)

    def test_start_date_stored(self):
        self.assertEqual(self.w._start_date, self.start)

    def test_end_date_stored(self):
        self.assertEqual(self.w._end_date, self.end)

    def test_page_snaps_to_start_month(self):
        self.assertEqual(self.w._page_month, 6)
        self.assertEqual(self.w._page_year,  2026)

    def test_start_edit_reflects_date(self):
        self.assertEqual(self.w._start_edit.date(), self.start)

    def test_end_edit_reflects_date(self):
        self.assertEqual(self.w._end_edit.date(), self.end)


class TestInputToggle(unittest.TestCase):

    def setUp(self):
        self.w     = CalendarTableWidget(CalendarMode.INPUT)
        self.start = QDate(2026, 6, 1)
        self.end   = QDate(2026, 7, 31)
        self.w.set_date_range(self.start, self.end)

    def test_toggle_in_range_day_marks_unavailable(self):
        day = QDate(2026, 6, 15)
        self.w._on_day_toggled(day)
        self.assertIn(day, self.w._unavailable)

    def test_toggle_twice_removes(self):
        day = QDate(2026, 6, 15)
        self.w._on_day_toggled(day)
        self.w._on_day_toggled(day)
        self.assertNotIn(day, self.w._unavailable)

    def test_anchor_start_not_togglable(self):
        self.w._on_day_toggled(self.start)
        self.assertNotIn(self.start, self.w._unavailable)

    def test_anchor_end_not_togglable(self):
        self.w._on_day_toggled(self.end)
        self.assertNotIn(self.end, self.w._unavailable)

    def test_day_clicked_signal_emitted(self):
        received = []
        self.w.day_clicked.connect(received.append)
        day = QDate(2026, 6, 20)
        self.w._on_day_toggled(day)
        self.assertEqual(received, [day])

    def test_unavailable_changed_signal_emitted(self):
        received = []
        self.w.unavailable_changed.connect(received.append)
        day = QDate(2026, 6, 20)
        self.w._on_day_toggled(day)
        self.assertEqual(len(received), 1)
        self.assertIn(day, received[0])


class TestInputSetUnavailableDays(unittest.TestCase):

    def setUp(self):
        self.w = CalendarTableWidget(CalendarMode.INPUT)
        self.w.set_date_range(QDate(2026, 6, 1), QDate(2026, 7, 31))

    def test_set_with_qdate_list(self):
        self.w.set_unavailable_days([QDate(2026, 6, 10), QDate(2026, 6, 25)])
        self.assertEqual(len(self.w.get_unavailable_days()), 2)

    def test_set_with_pydate_list(self):
        self.w.set_unavailable_days([py_date(2026, 6, 10), py_date(2026, 7, 4)])
        self.assertEqual(len(self.w.get_unavailable_days()), 2)

    def test_set_clears_previous(self):
        self.w.set_unavailable_days([QDate(2026, 6, 5)])
        self.w.set_unavailable_days([QDate(2026, 6, 10), QDate(2026, 6, 11)])
        self.assertEqual(len(self.w.get_unavailable_days()), 2)


# ===========================================================================
# INPUT mode — InputDayCell unit tests
# ===========================================================================

class TestInputDayCellStates(unittest.TestCase):

    def _cell(self, state):
        c = InputDayCell(QDate(2026, 6, 15))
        c.set_state(state)
        return c

    def test_in_range_is_interactive(self):
        self.assertTrue(self._cell(InputDayCell.STATE_IN_RANGE).is_interactive)

    def test_unavailable_is_interactive(self):
        self.assertTrue(self._cell(InputDayCell.STATE_UNAVAIL).is_interactive)

    def test_anchor_is_interactive(self):
        self.assertTrue(self._cell(InputDayCell.STATE_ANCHOR).is_interactive)

    def test_other_month_not_interactive(self):
        self.assertFalse(self._cell(InputDayCell.STATE_OTHER).is_interactive)

    def test_normal_not_interactive(self):
        self.assertFalse(self._cell(InputDayCell.STATE_NORMAL).is_interactive)

    def test_day_number_label_text(self):
        c = InputDayCell(QDate(2026, 6, 15))
        self.assertEqual(c._num_lbl.text(), "15")


# ===========================================================================
# OUTPUT mode — widget level
# ===========================================================================

class TestOutputConstruction(unittest.TestCase):

    def setUp(self):
        self.w = CalendarTableWidget(CalendarMode.OUTPUT)

    def test_mode_is_output(self):
        self.assertEqual(self.w._mode, CalendarMode.OUTPUT)

    def test_has_one_month_grid(self):
        self.assertEqual(len(self.w._month_grids), 1)

    def test_no_date_edits(self):
        self.assertFalse(hasattr(self.w, "_start_edit"))


class TestOutputSetSchedule(unittest.TestCase):

    def setUp(self):
        self.w = CalendarTableWidget(CalendarMode.OUTPUT)

    def test_exams_by_date_populated(self):
        exams = [
            _make_exam(exam_date=py_date(2026, 9, 2)),
            _make_exam("IS201", "Web Tech", "Elective", py_date(2026, 9, 5)),
        ]
        self.w.set_month_schedule(2026, 9, exams)
        self.assertEqual(len(self.w._exams_by_date), 2)

    def test_page_set_to_given_month(self):
        self.w.set_month_schedule(2026, 9, [])
        self.assertEqual(self.w._page_year,  2026)
        self.assertEqual(self.w._page_month, 9)

    def test_unavailable_dates_stored(self):
        self.w.set_month_schedule(2026, 9, [],
                                  unavailable_dates=[py_date(2026, 9, 18)])
        self.assertEqual(len(self.w._unavail_out), 1)

    def test_qdate_exam_date_accepted(self):
        self.w.set_month_schedule(2026, 9, [_make_exam(exam_date=QDate(2026, 9, 2))])
        self.assertIn(QDate(2026, 9, 2), self.w._exams_by_date)

    def test_invalid_exam_date_skipped(self):
        self.w.set_month_schedule(2026, 9, [_make_exam(exam_date=None)])
        self.assertEqual(len(self.w._exams_by_date), 0)

    def test_multiple_exams_same_day_grouped(self):
        exams = [
            _make_exam("CS201", exam_date=py_date(2026, 9, 2)),
            _make_exam("CS202", exam_date=py_date(2026, 9, 2)),
        ]
        self.w.set_month_schedule(2026, 9, exams)
        self.assertEqual(len(self.w._exams_by_date[QDate(2026, 9, 2)]), 2)


class TestOutputDayClickedSignal(unittest.TestCase):

    def setUp(self):
        self.w = CalendarTableWidget(CalendarMode.OUTPUT)

    def test_on_exam_clicked_emits_exams_day_clicked(self):
        from PyQt5.QtCore import QPoint
        exam = _make_exam(exam_date=py_date(2026, 9, 2))
        self.w.set_month_schedule(2026, 9, [exam])
        received = []
        self.w.exams_day_clicked.connect(lambda exams, anchor: received.append(exams))
        self.w._on_exam_clicked([exam], QPoint(0, 0))
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0]["course_number"], "CS201")


# ===========================================================================
# OUTPUT mode — OutputDayCell unit tests
# ===========================================================================

class TestOutputDayCell(unittest.TestCase):
    """
    NOTE: OutputDayCell widgets are created without a parent, so they must be
    stored as instance attributes to prevent Qt from garbage-collecting the
    underlying C++ object between the cell creation and the assertion.
    We use isHidden() (checks WA_Hidden flag) rather than isVisible() (requires
    the widget to be mapped on screen) for reliable headless testing.
    """

    def setUp(self):
        self.cell = OutputDayCell(QDate(2026, 9, 2))

    def _first_pill_text(self) -> str:
        """Return the text of the first badge pill.

        Pill is a QFrame containing a QLabel child.  Walk the children to find
        the first QLabel and return its text (may be truncated for long names).
        """
        pill = self.cell._pill_widgets[0]
        # pill is a QFrame — find the QLabel child that holds the badge text
        for child in pill.children():
            if hasattr(child, "text") and callable(child.text):
                return child.text()
        # Fallback: if pill is somehow a QLabel subclass
        return getattr(pill, "_full_text", pill.text() if hasattr(pill, "text") else "")

    # ── default state ─────────────────────────────────────────────────────────

    def test_badges_area_hidden_by_default(self):
        self.assertTrue(self.cell._badges_area.isHidden())

    def test_no_pills_by_default(self):
        self.assertEqual(len(self.cell._pill_widgets), 0)

    # ── set_exam (single) ─────────────────────────────────────────────────────

    def test_set_exam_shows_badges_area(self):
        self.cell.set_exam(_make_exam())
        self.assertFalse(self.cell._badges_area.isHidden())

    def test_set_exam_stores_data(self):
        exam = _make_exam()
        self.cell.set_exam(exam)
        self.assertEqual(self.cell._exam_data, exam)

    def test_set_exam_creates_one_pill(self):
        self.cell.set_exam(_make_exam())
        self.assertEqual(len(self.cell._pill_widgets), 1)

    def test_badge_label_contains_course_number(self):
        self.cell.set_exam(_make_exam(course_number="SE201"))
        self.assertIn("SE201", self._first_pill_text())

    def test_long_name_truncated_in_pill(self):
        # Names longer than 12 chars are truncated with an ellipsis in the pill.
        # "Very Long Course Name Here" (25 chars) → "Very Long Co…" (12 chars)
        self.cell.set_exam(_make_exam(course_name="Very Long Course Name Here"))
        text = self._first_pill_text()
        # The truncated prefix must appear and end with the ellipsis character
        self.assertIn("Very Long C", text)
        self.assertIn("…", text)

    # ── set_exams (multiple) ──────────────────────────────────────────────────

    def test_set_exams_two_shows_two_pills_no_more(self):
        exams = [_make_exam("CS201"), _make_exam("IS202", "Web Tech", "Elective")]
        self.cell.set_exams(exams)
        self.assertEqual(len(self.cell._pill_widgets), 2)
        self.assertIsNone(self.cell._more_lbl)

    def test_set_exams_three_shows_plus_one(self):
        exams = [_make_exam(f"C{i}") for i in range(3)]
        self.cell.set_exams(exams)
        self.assertEqual(len(self.cell._pill_widgets), 2)
        self.assertIsNotNone(self.cell._more_lbl)
        self.assertEqual(self.cell._more_lbl.text(), "+1")

    def test_set_exams_four_shows_plus_two(self):
        exams = [_make_exam(f"C{i}") for i in range(4)]
        self.cell.set_exams(exams)
        self.assertEqual(self.cell._more_lbl.text(), "+2")

    def test_set_exams_primary_exam_is_first(self):
        exams = [_make_exam("CS201"), _make_exam("IS202")]
        self.cell.set_exams(exams)
        self.assertEqual(self.cell._exam_data["course_number"], "CS201")

    # ── set_unavailable ───────────────────────────────────────────────────────

    def test_set_unavailable_shows_badges_area(self):
        # Per design: unavailable days show a rose "Unavailable" pill — badges area IS shown
        self.cell.set_unavailable()
        self.assertFalse(self.cell._badges_area.isHidden())

    def test_set_unavailable_sets_red_day_number(self):
        # The day number label should switch to the unavailable (red) colour (#DC2626)
        self.cell.set_unavailable()
        style = self.cell._day_num.styleSheet()
        self.assertIn("#DC2626", style)

    def test_set_unavailable_clears_exam_data(self):
        self.cell.set_unavailable()
        self.assertIsNone(self.cell._exam_data)

    def test_set_unavailable_flag(self):
        self.cell.set_unavailable()
        self.assertTrue(self.cell._unavailable)

    # ── clear ─────────────────────────────────────────────────────────────────

    def test_clear_hides_badges_area(self):
        self.cell.set_exam(_make_exam())
        self.cell.clear()
        self.assertTrue(self.cell._badges_area.isHidden())

    def test_clear_removes_pills(self):
        exams = [_make_exam(f"C{i}") for i in range(3)]
        self.cell.set_exams(exams)
        self.cell.clear()
        self.assertEqual(len(self.cell._pill_widgets), 0)

    def test_clear_resets_exam_data(self):
        self.cell.set_exam(_make_exam())
        self.cell.clear()
        self.assertIsNone(self.cell._exam_data)

    # ── misc ──────────────────────────────────────────────────────────────────

    def test_exam_clicked_signal_carries_list_and_point(self):
        from PyQt5.QtCore import QPoint
        exam = _make_exam()
        self.cell.set_exam(exam)
        received_exams = []
        received_anchors = []
        self.cell.exam_clicked.connect(
            lambda exams, anchor: (received_exams.append(exams), received_anchors.append(anchor))
        )
        self.cell.exam_clicked.emit([self.cell._exam_data], QPoint(0, 0))
        self.assertEqual(len(received_exams), 1)
        self.assertEqual(received_exams[0][0]["course_number"], "CS201")

    def test_other_month_cell_constructed(self):
        c = OutputDayCell(QDate(2026, 8, 31), is_other_month=True)
        self.assertEqual(c._day_num.text(), "31")


if __name__ == "__main__":
    unittest.main()
