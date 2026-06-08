"""
Tests for CalendarTableWidget (EP-36 / EP-47).
Covers both INPUT mode (period selector) and OUTPUT mode (schedule viewer).
"""

import sys
import unittest
import datetime
from datetime import date as py_date

from PyQt5.QtCore import QDate, QEvent, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication, QLabel

# Ensure QApplication exists before testing QWidgets
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


# ===========================================================================
# OUTPUT mode — OutputDayCell unit tests
# ===========================================================================

class TestOutputDayCell(unittest.TestCase):

    def setUp(self):
        self.cell = OutputDayCell(QDate(2026, 9, 2))

    def _first_pill_text(self) -> str:
        """Return the text of the QLabel inside the first badge pill."""
        pill = self.cell._pill_widgets[0]
        lbl = pill.findChild(QLabel)
        return lbl.text() if lbl else ""

    def test_badges_area_hidden_by_default(self):
        self.assertTrue(self.cell._badges_area.isHidden())

    def test_set_exam_shows_badges_area(self):
        self.cell.set_exam(_make_exam())
        self.assertFalse(self.cell._badges_area.isHidden())

    def test_badge_label_contains_course_number(self):
        self.cell.set_exam(_make_exam(course_number="SE201"))
        self.assertIn("SE201", self._first_pill_text())

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

    def test_set_unavailable_clears_exam_data(self):
        self.cell.set_unavailable()
        self.assertIsNone(self.cell._exam_data)

    def test_clear_removes_pills(self):
        exams = [_make_exam(f"C{i}") for i in range(3)]
        self.cell.set_exams(exams)
        self.cell.clear()
        self.assertEqual(len(self.cell._pill_widgets), 0)


if __name__ == "__main__":
    unittest.main()