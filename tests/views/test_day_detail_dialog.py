import sys
import unittest
from datetime import date

from PyQt5.QtWidgets import QApplication, QLabel, QFrame

# Ensure a QApplication instance exists before creating any widget
app = QApplication.instance() or QApplication(sys.argv)

from src.views.output_screen.day_detail_dialog import DayDetailDialog
from src.views.shared_components.type_badge import TypeBadge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_exam(overrides: dict = None) -> dict:
    """Return a minimal valid exam_data dict, with optional field overrides."""
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


def _make_dialog(exam_data=None, program_names=None) -> DayDetailDialog:
    """Construct a DayDetailDialog without showing it."""
    return DayDetailDialog(
        exam_data    = exam_data    or _make_exam(),
        program_names= program_names,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDayDetailDialogCreation(unittest.TestCase):
    """Verify that the dialog builds without errors under various inputs."""

    def test_dialog_creates_without_crash(self):
        """Dialog must instantiate successfully with a fully populated exam_data dict."""
        try:
            dlg = _make_dialog()
            created = True
        except Exception as exc:
            created = False
            self.fail(f"DayDetailDialog raised an exception on creation: {exc}")
        self.assertTrue(created)

    def test_dialog_creates_with_missing_optional_fields(self):
        """Dialog must not crash when optional fields (semester, moed) are absent."""
        exam = {"course_number": "111", "course_name": "Math", "type": "Elective",
                "programs": [], "exam_date": date(2026, 1, 1)}
        try:
            _make_dialog(exam_data=exam)
            created = True
        except Exception as exc:
            created = False
            self.fail(f"DayDetailDialog crashed with missing fields: {exc}")
        self.assertTrue(created)

    def test_dialog_creates_with_no_program_names(self):
        """Dialog must work when program_names is None (falls back to raw IDs)."""
        dlg = _make_dialog(program_names=None)
        self.assertIsNotNone(dlg)

    def test_dialog_creates_with_empty_programs_list(self):
        """Dialog must not crash when the programs list is empty."""
        exam = _make_exam({"programs": []})
        try:
            _make_dialog(exam_data=exam)
            created = True
        except Exception as exc:
            created = False
            self.fail(f"Dialog crashed with empty programs list: {exc}")
        self.assertTrue(created)


class TestDayDetailDialogFieldValues(unittest.TestCase):
    """Verify that the correct text is rendered for each field."""

    def _find_labels(self, dlg: DayDetailDialog) -> list[str]:
        """Collect all QLabel texts inside the dialog (ignores empty strings)."""
        return [lbl.text() for lbl in dlg.findChildren(QLabel) if lbl.text()]

    def test_course_number_is_displayed(self):
        """The dialog must show the course number string somewhere in its labels."""
        dlg = _make_dialog()
        self.assertIn("83111", self._find_labels(dlg))

    def test_course_name_is_displayed(self):
        """The dialog must show the course name string somewhere in its labels."""
        dlg = _make_dialog()
        self.assertIn("Data Structures", self._find_labels(dlg))

    def test_semester_is_displayed(self):
        """The dialog must show the semester value somewhere in its labels."""
        dlg = _make_dialog()
        self.assertIn("FALL", self._find_labels(dlg))

    def test_moed_is_displayed(self):
        """The dialog must show the moed value somewhere in its labels."""
        dlg = _make_dialog()
        self.assertIn("Aleph", self._find_labels(dlg))

    def test_exam_date_is_formatted_correctly(self):
        """Exam date must be displayed in DD/MM/YYYY format."""
        dlg = _make_dialog()
        self.assertIn("10/06/2026", self._find_labels(dlg))

    def test_type_badge_is_present(self):
        """A TypeBadge widget must exist inside the dialog for the 'type' field."""
        dlg = _make_dialog()
        badges = dlg.findChildren(TypeBadge)
        self.assertGreater(len(badges), 0, "No TypeBadge found in DayDetailDialog")

    def test_type_badge_shows_correct_text(self):
        """The TypeBadge must display the same type string that was passed in exam_data."""
        dlg = _make_dialog(_make_exam({"type": "Elective"}))
        badges = dlg.findChildren(TypeBadge)
        self.assertTrue(
            any(b.text() == "Elective" for b in badges),
            "TypeBadge does not show 'Elective'"
        )


class TestDayDetailDialogProgramNames(unittest.TestCase):
    """Verify program chip display with and without a program_names mapping."""

    def _chip_texts(self, dlg: DayDetailDialog) -> list[str]:
        """Return the text of every QLabel that looks like a program chip (inside the programs row)."""
        # All QLabel texts that are not field captions or values
        # (chips are short — typically program IDs or short names)
        return [lbl.text() for lbl in dlg.findChildren(QLabel) if lbl.text()]

    def test_programs_show_raw_id_when_no_mapping(self):
        """Without program_names, the chip must display the raw program ID."""
        dlg = _make_dialog(
            exam_data     = _make_exam({"programs": ["83101"]}),
            program_names = None,
        )
        texts = self._chip_texts(dlg)
        self.assertIn("83101", texts, "Raw program ID should appear when no mapping is given")

    def test_programs_show_display_name_when_mapping_provided(self):
        """When program_names contains the ID, the chip must show the display name."""
        mapping = {"83101": "Computer Engineering", "83104": "Industrial Engineering"}
        dlg = _make_dialog(
            exam_data     = _make_exam({"programs": ["83101", "83104"]}),
            program_names = mapping,
        )
        texts = self._chip_texts(dlg)
        self.assertIn("Computer Engineering",  texts)
        self.assertIn("Industrial Engineering", texts)

    def test_programs_fall_back_to_id_for_unmapped_entry(self):
        """If a program ID is not in the mapping, the chip must fall back to the raw ID."""
        mapping = {"83101": "Computer Engineering"}
        dlg = _make_dialog(
            exam_data     = _make_exam({"programs": ["83101", "99999"]}),
            program_names = mapping,
        )
        texts = self._chip_texts(dlg)
        # 99999 has no entry in mapping → must appear as-is
        self.assertIn("99999", texts, "Unmapped ID should fall back to the raw ID string")

    def test_multiple_programs_all_appear(self):
        """Every program in the list must produce exactly one chip label."""
        programs = ["83101", "83102", "83104"]
        mapping  = {
            "83101": "CS",
            "83102": "EE",
            "83104": "IE",
        }
        dlg = _make_dialog(
            exam_data     = _make_exam({"programs": programs}),
            program_names = mapping,
        )
        texts = self._chip_texts(dlg)
        for name in ["CS", "EE", "IE"]:
            self.assertIn(name, texts, f"Program chip '{name}' not found in dialog labels")


class TestDayDetailDialogStructure(unittest.TestCase):
    """Verify structural / UI properties of the dialog."""

    def test_dialog_is_modal(self):
        """The dialog must be modal so it blocks the parent window."""
        dlg = _make_dialog()
        self.assertTrue(dlg.isModal())

    def test_dialog_has_minimum_width(self):
        """The dialog must have a minimum width set (ensures it is not too narrow)."""
        dlg = _make_dialog()
        self.assertGreaterEqual(dlg.minimumWidth(), 300)

    def test_dialog_contains_divider_frame(self):
        """A QFrame used as a visual divider must exist inside the dialog."""
        dlg = _make_dialog()
        frames = [f for f in dlg.findChildren(QFrame)
                  if f.frameShape() == QFrame.HLine]
        self.assertGreater(len(frames), 0, "No horizontal divider QFrame found")

    def test_format_date_with_date_object(self):
        """_format_date must return DD/MM/YYYY for a datetime.date input."""
        result = DayDetailDialog._format_date(date(2026, 3, 5))
        self.assertEqual(result, "05/03/2026")

    def test_format_date_with_none_returns_placeholder(self):
        """_format_date must return the '—' placeholder when passed None."""
        result = DayDetailDialog._format_date(None)
        self.assertEqual(result, "—")

    def test_format_date_with_string_passthrough(self):
        """_format_date must convert non-date values to their str() representation."""
        result = DayDetailDialog._format_date("2026-06-10")
        self.assertEqual(result, "2026-06-10")


if __name__ == "__main__":
    unittest.main()
