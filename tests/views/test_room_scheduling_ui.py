"""
Tests for the Room Scheduling UI feature (Task 140).

Covers:
  - ConstraintConfigWidget: room scheduling toggle exists and serialises correctly
  - DayDetailDialog._ExamRow: renders room info when present, omits it when absent
  - Backward compatibility: date-only exams still render as before

These are unit tests for the View layer only.  They do not invoke the
scheduling engine or the data store.
"""

import sys
import unittest

from PyQt5.QtWidgets import QApplication, QCheckBox, QLabel

# A QApplication instance must exist before any QWidget is constructed.
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.settings_screen.constraint_config_widget import ConstraintConfigWidget
from src.views.output_screen.day_detail_dialog import _ExamRow
from src.models.constraint_settings import ConstraintSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_date_only_exam(**overrides) -> dict:
    """Return a minimal date-only exam dict (no room keys)."""
    base = {
        "course_number": "12345",
        "course_name":   "Test Course",
        "type":          "Obligatory",
        "programs":      ["00001"],
        "exam_date":     None,
        "semester":      "FALL",
        "moed":          "Aleph",
    }
    base.update(overrides)
    return base


def _make_room_exam(**overrides) -> dict:
    """Return an exam dict that carries room-scheduling data."""
    base = _make_date_only_exam()
    base.update({
        "time_slot":      "MORNING",
        "rooms":          [
            {"building": "A", "room_id": "101", "capacity": 80},
            {"building": "A", "room_id": "102", "capacity": 60},
        ],
        "num_students":   120,
        "total_capacity": 140,
    })
    base.update(overrides)
    return base


def _get_label_texts(row: _ExamRow) -> list[str]:
    """Collect the text of all QLabel children in the row widget."""
    return [w.text() for w in row.findChildren(QLabel)]


# ---------------------------------------------------------------------------
# ConstraintConfigWidget - room scheduling toggle
# ---------------------------------------------------------------------------

class TestRoomSchedulingToggle(unittest.TestCase):
    """The widget must expose a boolean-only checkbox for room scheduling."""

    def setUp(self):
        self.widget = ConstraintConfigWidget()

    def test_room_scheduling_check_exists(self):
        """_room_scheduling_check must be a QCheckBox instance."""
        self.assertIsInstance(self.widget._room_scheduling_check, QCheckBox)

    def test_room_scheduling_default_is_off(self):
        """The toggle must be unchecked by default."""
        self.assertFalse(self.widget._room_scheduling_check.isChecked())

    def test_get_values_includes_room_scheduling_enabled(self):
        """get_values() must always include the room_scheduling_enabled key."""
        values = self.widget.get_values()
        self.assertIn("room_scheduling_enabled", values)

    def test_get_values_room_scheduling_default_false(self):
        """room_scheduling_enabled must be False when the toggle is unchecked."""
        self.assertFalse(self.widget.get_values()["room_scheduling_enabled"])

    def test_get_values_room_scheduling_true_when_checked(self):
        """room_scheduling_enabled must be True when the toggle is checked."""
        self.widget._room_scheduling_check.setChecked(True)
        self.assertTrue(self.widget.get_values()["room_scheduling_enabled"])

    def test_set_values_restores_room_scheduling_true(self):
        """set_values() must restore room_scheduling_enabled=True from a dict."""
        self.widget.set_values({"room_scheduling_enabled": True})
        self.assertTrue(self.widget._room_scheduling_check.isChecked())

    def test_set_values_restores_room_scheduling_false(self):
        """set_values() must restore room_scheduling_enabled=False from a dict."""
        self.widget._room_scheduling_check.setChecked(True)  # start checked
        self.widget.set_values({"room_scheduling_enabled": False})
        self.assertFalse(self.widget._room_scheduling_check.isChecked())

    def test_set_values_missing_key_defaults_to_false(self):
        """Omitting room_scheduling_enabled from the dict must default to False.

        This ensures widgets populated from pre-feature saved settings don't crash.
        """
        self.widget._room_scheduling_check.setChecked(True)
        self.widget.set_values({})  # no room_scheduling_enabled key
        self.assertFalse(self.widget._room_scheduling_check.isChecked())

    def test_roundtrip_room_scheduling_enabled_true(self):
        """set_values then get_values must preserve room_scheduling_enabled=True."""
        self.widget.set_values({"room_scheduling_enabled": True})
        self.assertTrue(self.widget.get_values()["room_scheduling_enabled"])

    def test_get_settings_reflects_room_scheduling(self):
        """get_settings() must return a ConstraintSettings with room_scheduling_enabled set."""
        self.widget._room_scheduling_check.setChecked(True)
        settings = self.widget.get_settings()
        self.assertIsInstance(settings, ConstraintSettings)
        self.assertTrue(settings.room_scheduling_enabled)

    def test_set_settings_restores_room_scheduling(self):
        """set_settings() must restore the toggle from a ConstraintSettings object."""
        settings = ConstraintSettings(room_scheduling_enabled=True)
        self.widget.set_settings(settings)
        self.assertTrue(self.widget._room_scheduling_check.isChecked())


# ---------------------------------------------------------------------------
# DayDetailDialog._ExamRow - room info rendering
# ---------------------------------------------------------------------------

class TestExamRowDateOnly(unittest.TestCase):
    """Date-only exams must render exactly as before — no room labels."""

    def _make_row(self, exam: dict) -> _ExamRow:
        return _ExamRow(exam, program_names={})

    def test_course_number_shown(self):
        row = self._make_row(_make_date_only_exam(course_number="99999"))
        self.assertIn("99999", _get_label_texts(row))

    def test_course_name_shown(self):
        row = self._make_row(_make_date_only_exam(course_name="Algebra"))
        texts = _get_label_texts(row)
        self.assertTrue(any("Algebra" in t for t in texts))

    def test_no_time_slot_label(self):
        """Date-only row must not contain any time-slot text."""
        row = self._make_row(_make_date_only_exam())
        texts = " ".join(_get_label_texts(row)).upper()
        self.assertNotIn("MORNING", texts)
        self.assertNotIn("AFTERNOON", texts)
        self.assertNotIn("EVENING", texts)

    def test_no_room_labels(self):
        """Date-only row must not contain room info labels."""
        row = self._make_row(_make_date_only_exam())
        texts = " ".join(_get_label_texts(row))
        self.assertNotIn("Assigned rooms", texts)
        self.assertNotIn("Total capacity", texts)
        self.assertNotIn("seats", texts)


class TestExamRowRoomScheduling(unittest.TestCase):
    """Room-scheduling exams must render time slot, rooms, and capacity info."""

    def _make_row(self, exam: dict) -> _ExamRow:
        return _ExamRow(exam, program_names={})

    def test_time_slot_shown(self):
        row = self._make_row(_make_room_exam(time_slot="MORNING"))
        texts = " ".join(_get_label_texts(row))
        self.assertIn("MORNING", texts)

    def test_afternoon_slot_shown(self):
        row = self._make_row(_make_room_exam(time_slot="AFTERNOON"))
        texts = " ".join(_get_label_texts(row))
        self.assertIn("AFTERNOON", texts)

    def test_room_building_shown(self):
        row = self._make_row(_make_room_exam())
        texts = " ".join(_get_label_texts(row))
        self.assertIn("Building A", texts)

    def test_room_id_shown(self):
        row = self._make_row(_make_room_exam())
        texts = " ".join(_get_label_texts(row))
        self.assertIn("101", texts)
        self.assertIn("102", texts)

    def test_room_capacity_shown(self):
        """Each room's seat count must appear in the card."""
        row = self._make_row(_make_room_exam())
        texts = " ".join(_get_label_texts(row))
        self.assertIn("80 seats", texts)
        self.assertIn("60 seats", texts)

    def test_total_capacity_shown(self):
        """Capacity summary must show students / total_capacity in that order."""
        row = self._make_row(_make_room_exam(total_capacity=140, num_students=120))
        texts = " ".join(_get_label_texts(row))
        self.assertIn("120 / 140", texts)

    def test_assigned_rooms_header_shown(self):
        row = self._make_row(_make_room_exam())
        texts = " ".join(_get_label_texts(row))
        self.assertIn("Assigned rooms", texts)

    def test_course_name_still_shown(self):
        """Room data must not replace existing course fields."""
        row = self._make_row(_make_room_exam(course_name="Physics"))
        texts = _get_label_texts(row)
        self.assertTrue(any("Physics" in t for t in texts))

    def test_single_room_renders(self):
        """A placement with only one room must still render all fields."""
        exam = _make_room_exam(
            rooms=[{"building": "B", "room_id": "201", "capacity": 200}],
            total_capacity=200,
            num_students=150,
        )
        row = self._make_row(exam)
        texts = " ".join(_get_label_texts(row))
        self.assertIn("Building B", texts)
        self.assertIn("200 seats", texts)

    def test_three_rooms_all_rendered(self):
        """Every room in a three-room placement must produce its own bullet label."""
        exam = _make_room_exam(
            rooms=[
                {"building": "A", "room_id": "R01", "capacity": 40},
                {"building": "B", "room_id": "R02", "capacity": 80},
                {"building": "C", "room_id": "R03", "capacity": 120},
            ],
            num_students=220,
            total_capacity=240,
        )
        row = self._make_row(exam)
        texts = " ".join(_get_label_texts(row))
        # Each room's building, ID, and seat count must appear.
        self.assertIn("Building A", texts)
        self.assertIn("Building B", texts)
        self.assertIn("Building C", texts)
        self.assertIn("R01", texts)
        self.assertIn("R02", texts)
        self.assertIn("R03", texts)
        self.assertIn("40 seats", texts)
        self.assertIn("80 seats", texts)
        self.assertIn("120 seats", texts)
        # Capacity summary must show students / total_capacity in that order.
        self.assertIn("220 / 240", texts)


if __name__ == "__main__":
    unittest.main()
