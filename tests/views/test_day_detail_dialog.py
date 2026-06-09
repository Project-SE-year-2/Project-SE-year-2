"""
Tests for DayDetailDialog (multi-exam day popup).

The dialog now accepts a *list* of exam dicts and renders each one as
a card row with a coloured left border, course code, course name,
mini type-badge chip, and abbreviated program names.
"""

import sys
import unittest
from datetime import date

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QPushButton

app = QApplication.instance() or QApplication(sys.argv)

from src.views.output_screen.day_detail_dialog import DayDetailDialog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_exam(overrides: dict = None) -> dict:
    """Return a minimal valid exam dict, with optional field overrides."""
    base = {
        "course_number": "83111",
        "course_name":   "Data Structures",
        "type":          "Obligatory",
        "programs":      ["83101", "83104"],
        "exam_date":     date(2026, 6, 10),
        "semester":      "FALL",
        "moed":          "Aleph",
    }
    if overrides:
        base.update(overrides)
    return base


def _make_dialog(exams=None, program_names=None, anchor_pos=None) -> DayDetailDialog:
    """Construct a DayDetailDialog (without showing it)."""
    exam_list  = exams if exams is not None else [_make_exam()]
    first_date = exam_list[0].get("exam_date") if exam_list else None
    return DayDetailDialog(
        exams         = exam_list,
        exam_date     = first_date,
        program_names = program_names,
        anchor_pos    = anchor_pos,
    )


def _all_label_texts(dlg: DayDetailDialog) -> list[str]:
    """Collect every non-empty QLabel text inside the dialog."""
    return [lbl.text() for lbl in dlg.findChildren(QLabel) if lbl.text()]


# ===========================================================================
# Construction
# ===========================================================================

class TestDayDetailDialogCreation(unittest.TestCase):
    """Verify that the dialog builds without errors under various inputs."""

    def test_dialog_creates_without_crash(self):
        """Dialog must instantiate successfully with a fully populated exam dict."""
        try:
            _make_dialog()
            created = True
        except Exception as exc:
            created = False
            self.fail(f"DayDetailDialog raised an exception on creation: {exc}")
        self.assertTrue(created)

    def test_dialog_creates_with_missing_optional_fields(self):
        """Dialog must not crash when optional fields are absent."""
        exam = {"course_number": "111", "course_name": "Math", "type": "Elective",
                "programs": [], "exam_date": date(2026, 1, 1)}
        try:
            _make_dialog(exams=[exam])
            created = True
        except Exception as exc:
            created = False
            self.fail(f"DayDetailDialog crashed with missing fields: {exc}")
        self.assertTrue(created)

    def test_dialog_creates_with_no_program_names(self):
        """Dialog must work when program_names is None (falls back to abbreviated IDs)."""
        dlg = _make_dialog(program_names=None)
        self.assertIsNotNone(dlg)

    def test_dialog_creates_with_empty_programs_list(self):
        """Dialog must not crash when the programs list is empty."""
        exam = _make_exam({"programs": []})
        try:
            _make_dialog(exams=[exam])
            created = True
        except Exception as exc:
            created = False
            self.fail(f"Dialog crashed with empty programs list: {exc}")
        self.assertTrue(created)

    def test_dialog_creates_with_multiple_exams(self):
        """Dialog must render all exams without crashing."""
        exams = [
            _make_exam({"course_number": "CS201"}),
            _make_exam({"course_number": "IS202"}),
            _make_exam({"course_number": "MA101"}),
        ]
        try:
            _make_dialog(exams=exams)
            created = True
        except Exception as exc:
            created = False
            self.fail(f"Dialog crashed with multiple exams: {exc}")
        self.assertTrue(created)

    def test_dialog_creates_with_anchor_pos(self):
        """Dialog must accept an anchor QPoint without crashing."""
        try:
            _make_dialog(anchor_pos=QPoint(100, 200))
            created = True
        except Exception as exc:
            created = False
            self.fail(f"Dialog crashed with anchor_pos: {exc}")
        self.assertTrue(created)


# ===========================================================================
# Field values
# ===========================================================================

class TestDayDetailDialogFieldValues(unittest.TestCase):
    """Verify that the correct text is rendered for each field."""

    def test_course_number_is_displayed(self):
        """The dialog must show the course number string somewhere in its labels."""
        dlg = _make_dialog()
        self.assertIn("83111", _all_label_texts(dlg))

    def test_course_name_is_displayed(self):
        """The dialog must show the course name string somewhere in its labels."""
        dlg = _make_dialog()
        self.assertIn("Data Structures", _all_label_texts(dlg))

    def test_exam_date_appears_in_title(self):
        """The formatted date (DD/MM/YYYY) must appear in the title label."""
        dlg   = _make_dialog()
        texts = _all_label_texts(dlg)
        self.assertTrue(any("10/06/2026" in t for t in texts),
                        "'10/06/2026' not found in any dialog label")

    def test_type_badge_required_shown(self):
        """An Obligatory exam must produce a 'Required' mini-badge label."""
        dlg = _make_dialog()
        self.assertIn("Required", _all_label_texts(dlg))

    def test_type_badge_elective_shown(self):
        """An Elective exam must produce an 'Elective' mini-badge label."""
        dlg = _make_dialog(exams=[_make_exam({"type": "Elective"})])
        self.assertIn("Elective", _all_label_texts(dlg))


# ===========================================================================
# Multiple exams
# ===========================================================================

class TestDayDetailDialogMultipleExams(unittest.TestCase):
    """Verify correct rendering when multiple exams share the same day."""

    def test_all_course_numbers_shown(self):
        """Every course number in the exams list must appear in the dialog."""
        exams = [
            _make_exam({"course_number": "CS201"}),
            _make_exam({"course_number": "IS202"}),
            _make_exam({"course_number": "MA101"}),
        ]
        dlg   = _make_dialog(exams=exams)
        texts = _all_label_texts(dlg)
        for code in ["CS201", "IS202", "MA101"]:
            self.assertIn(code, texts, f"Course code '{code}' not found in dialog labels")

    def test_footer_shows_correct_count(self):
        """The footer must say '4 exams on this day' for four exams."""
        exams = [_make_exam({"course_number": f"C{i}"}) for i in range(4)]
        dlg   = _make_dialog(exams=exams)
        texts = _all_label_texts(dlg)
        self.assertTrue(any("4" in t and "exam" in t for t in texts),
                        "Footer count '4 exams' not found")

    def test_footer_singular_for_one_exam(self):
        """Footer must use the singular form '1 exam on this day'."""
        dlg   = _make_dialog()
        texts = _all_label_texts(dlg)
        self.assertTrue(any("1 exam" in t for t in texts),
                        "Singular '1 exam' not found in footer")


# ===========================================================================
# Program abbreviations
# ===========================================================================

class TestDayDetailDialogProgramNames(unittest.TestCase):
    """Verify program abbreviation display with and without a program_names mapping."""

    def _prog_labels(self, dlg: DayDetailDialog) -> list[str]:
        """Return all label texts that contain 'Programs Affected'."""
        return [t for t in _all_label_texts(dlg) if "Programs Affected" in t]

    def test_programs_show_abbreviated_id_when_no_mapping(self):
        """Without program_names the bullet must show 2-char abbreviation of the raw ID."""
        dlg   = _make_dialog(exams=[_make_exam({"programs": ["83101"]})],
                             program_names=None)
        texts = _all_label_texts(dlg)
        # _abbrev("83101") == "83"
        self.assertTrue(any("83" in t for t in texts), "'83' abbreviation not found")

    def test_programs_show_abbreviated_display_name_when_mapping_provided(self):
        """When a mapping is given, the label must show initials of the display name."""
        mapping = {"83101": "Computer Science", "83104": "Software Engineering"}
        dlg  = _make_dialog(
            exams=[_make_exam({"programs": ["83101", "83104"]})],
            program_names=mapping,
        )
        texts = _all_label_texts(dlg)
        # _abbrev("Computer Science") == "CS", _abbrev("Software Engineering") == "SE"
        self.assertTrue(any("CS" in t for t in texts), "'CS' abbreviation not found")
        self.assertTrue(any("SE" in t for t in texts), "'SE' abbreviation not found")

    def test_programs_fall_back_to_id_abbreviation_for_unmapped_entry(self):
        """An unmapped program ID must fall back to 2-char abbreviation of the raw ID."""
        mapping = {"83101": "Computer Science"}
        dlg   = _make_dialog(
            exams=[_make_exam({"programs": ["83101", "99999"]})],
            program_names=mapping,
        )
        texts = _all_label_texts(dlg)
        # "99999" → "99"
        self.assertTrue(any("99" in t for t in texts), "'99' abbreviation not found")

    def test_multiple_programs_appear_in_bullets(self):
        """Each program must produce a bullet row visible as a QLabel."""
        mapping = {"83101": "Computer Science", "83102": "Electrical Engineering",
                   "83104": "Industrial Engineering"}
        dlg   = _make_dialog(
            exams=[_make_exam({"programs": ["83101", "83102", "83104"]})],
            program_names=mapping,
        )
        texts = _all_label_texts(dlg)
        # initials: CS, EE, IE
        for abbr in ["CS", "EE", "IE"]:
            self.assertTrue(any(abbr in t for t in texts),
                            f"Abbreviation '{abbr}' not found in dialog labels")

    def test_empty_programs_shows_count_zero(self):
        """An empty programs list must show 'Programs Affected (0)' without crashing."""
        dlg  = _make_dialog(exams=[_make_exam({"programs": []})])
        prog = self._prog_labels(dlg)
        self.assertTrue(prog, "No 'Programs Affected' label found")
        self.assertIn("0", prog[0])


# ===========================================================================
# Structure
# ===========================================================================

class TestDayDetailDialogStructure(unittest.TestCase):
    """Verify structural / UI properties of the dialog."""

    def test_dialog_has_minimum_width(self):
        """The dialog must have a minimum width ≥ 300 px."""
        dlg = _make_dialog()
        self.assertGreaterEqual(dlg.minimumWidth(), 300)

    def test_dialog_has_close_button(self):
        """A ✕ close button must exist inside the dialog."""
        dlg  = _make_dialog()
        btns = dlg.findChildren(QPushButton)
        self.assertTrue(any("✕" in b.text() for b in btns),
                        "No ✕ close button found in dialog")

    def test_dialog_title_contains_exams_on(self):
        """The title label must start with 'Exams on'."""
        dlg   = _make_dialog()
        texts = _all_label_texts(dlg)
        self.assertTrue(any(t.startswith("Exams on") for t in texts),
                        "'Exams on …' title not found in dialog labels")

    def test_dialog_has_card_frame(self):
        """A QFrame named 'dialogCard' must exist as the card surface."""
        dlg    = _make_dialog()
        frames = [f for f in dlg.findChildren(QFrame)
                  if f.objectName() == "dialogCard"]
        self.assertGreater(len(frames), 0, "No QFrame#dialogCard found")

    def test_format_date_with_date_object(self):
        """_format_date must return DD/MM/YYYY for a datetime.date input."""
        self.assertEqual(DayDetailDialog._format_date(date(2026, 3, 5)), "05/03/2026")

    def test_format_date_with_none_returns_placeholder(self):
        """_format_date must return '—' when passed None."""
        self.assertEqual(DayDetailDialog._format_date(None), "—")

    def test_format_date_with_string_passthrough(self):
        """_format_date must pass non-date values through as str()."""
        self.assertEqual(DayDetailDialog._format_date("2026-06-10"), "2026-06-10")


if __name__ == "__main__":
    unittest.main()
