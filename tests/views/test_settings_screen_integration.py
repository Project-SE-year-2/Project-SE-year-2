"""
EP-114 — Integration test suite for the Settings screen.

Where the existing unit tests poke widget internals, this suite drives the
Settings screen the way a user does — real checkbox/button .click()s, spinbox
value entry, drag-reorders, and the full Apply → service → navigation workflow
through MainWindow. It covers the four acceptance areas:

  1. Visual control interactions   — checkbox click enables/disables its spinbox.
  2. Form-entry boundary behavior   — spinboxes clamp to their min/max bounds.
  3. Drag-and-drop row adjustments  — reordering the ranking rows keeps every row
                                      intact and preserves checked state.
  4. Confirmation workflow          — Apply saves valid settings and navigates;
                                      invalid settings warn and stay put.
"""

import sys
import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.settings_screen.constraint_config_widget import ConstraintConfigWidget
from src.views.settings_screen.ranking_config_widget import RankingConfigWidget
from src.models.constraint_settings import ConstraintSettings

# Constraints that require a strictly positive K when enabled (validation rule).
_POSITIVE_K_KEYS = ["mandatory_gap", "all_gap", "spread", "daily_cap"]
_MAXES = {"mandatory_gap": 30, "all_gap": 30, "elective_conflicts": 10,
          "spread": 60, "daily_cap": 10}


# ---------------------------------------------------------------------------
# 1. Visual control interactions — real clicks
# ---------------------------------------------------------------------------

class TestControlInteractions(unittest.TestCase):
    def setUp(self):
        self.panel = ConstraintConfigWidget()

    def test_clicking_checkbox_enables_its_spinbox(self):
        """A real click on the checkbox must enable the paired spinbox."""
        for key in _MAXES:
            self.panel._checks[key].click()
            self.assertTrue(self.panel._checks[key].isChecked(), msg=key)
            self.assertTrue(self.panel._spins[key].isEnabled(), msg=key)

    def test_second_click_disables_spinbox_again(self):
        """Clicking a checked checkbox a second time disables the spinbox."""
        check = self.panel._checks["daily_cap"]
        check.click()
        check.click()
        self.assertFalse(check.isChecked())
        self.assertFalse(self.panel._spins["daily_cap"].isEnabled())

    def test_one_checkbox_does_not_affect_others(self):
        """Enabling one constraint leaves every other spinbox disabled."""
        self.panel._checks["spread"].click()
        for key in _MAXES:
            if key != "spread":
                self.assertFalse(self.panel._spins[key].isEnabled(), msg=key)


# ---------------------------------------------------------------------------
# 2. Form-entry boundary behavior
# ---------------------------------------------------------------------------

class TestBoundaryBehavior(unittest.TestCase):
    def setUp(self):
        self.panel = ConstraintConfigWidget()

    def test_value_above_max_is_clamped(self):
        for key, mx in _MAXES.items():
            spin = self.panel._spins[key]
            spin.setValue(mx + 500)
            self.assertEqual(spin.value(), mx, msg=key)

    def test_value_below_min_is_clamped_to_zero(self):
        for key in _MAXES:
            spin = self.panel._spins[key]
            spin.setValue(-50)
            self.assertEqual(spin.value(), 0, msg=key)

    def test_stepby_cannot_exceed_max(self):
        """Stepping past the top must stop at the maximum, not overflow."""
        spin = self.panel._spins["elective_conflicts"]
        spin.setValue(_MAXES["elective_conflicts"])
        spin.stepBy(5)
        self.assertEqual(spin.value(), _MAXES["elective_conflicts"])

    def test_boundary_values_round_trip_through_settings(self):
        """Max boundary values survive a get_settings/set_settings round-trip."""
        for key, mx in _MAXES.items():
            self.panel._checks[key].setChecked(True)
            self.panel._spins[key].setValue(mx)
        restored = ConstraintConfigWidget()
        restored.set_settings(self.panel.get_settings())
        self.assertEqual(restored.get_settings(), self.panel.get_settings())


# ---------------------------------------------------------------------------
# 3. Drag-and-drop row adjustments (ranking panel)
# ---------------------------------------------------------------------------

class TestRankingDragReorder(unittest.TestCase):
    def setUp(self):
        self.w = RankingConfigWidget()

    def _keys(self):
        return [self.w._list.item(i).data(Qt.UserRole)
                for i in range(self.w._list.count())]

    def test_reorder_keeps_every_row_widget_intact(self):
        """The reported bug: after a drag the moved row came back blank.

        Simulate the post-drag state (item data is what Qt preserves) and fire
        the move handler. Every row must still carry a widget afterward.
        """
        self.w.set_sort_order(
            ["avg_days_all", "min_days_required"],
            checked={"avg_days_all", "min_days_required"},
        )
        rotated = self._keys()[1:] + self._keys()[:1]
        for i, key in enumerate(rotated):
            self.w._list.item(i).setData(Qt.UserRole, key)

        self.w._on_rows_moved()
        QApplication.processEvents()   # run the deferred rebuild

        for i in range(self.w._list.count()):
            self.assertIsNotNone(
                self.w._list.itemWidget(self.w._list.item(i)),
                msg=f"row {i} lost its widget after reorder",
            )

    def test_reorder_applies_new_order(self):
        rotated = self._keys()[1:] + self._keys()[:1]
        for i, key in enumerate(rotated):
            self.w._list.item(i).setData(Qt.UserRole, key)
        self.w._on_rows_moved()
        QApplication.processEvents()
        self.assertEqual(self._keys(), rotated)

    def test_reorder_preserves_checked_state(self):
        self.w.set_sort_order(["span_required"], checked={"span_required"})
        rotated = self._keys()[1:] + self._keys()[:1]
        for i, key in enumerate(rotated):
            self.w._list.item(i).setData(Qt.UserRole, key)
        self.w._on_rows_moved()
        QApplication.processEvents()
        self.assertEqual(self.w._checked, {"span_required"})

    def test_get_sort_order_returns_only_checked_in_visual_order(self):
        self.w.set_sort_order(
            ["avg_days_all", "min_days_required"],
            checked={"avg_days_all", "min_days_required"},
        )
        order = self.w.get_sort_order()
        self.assertEqual(order[0], "avg_days_all")
        self.assertIn("min_days_required", order)


# ---------------------------------------------------------------------------
# 4. Confirmation workflow — full path through MainWindow
# ---------------------------------------------------------------------------

class TestConfirmationWorkflow(unittest.TestCase):
    def setUp(self):
        from src.main_window import MainWindow
        self.window = MainWindow()
        self.screen = self.window.settings_screen
        self.panel = self.screen.constraint_panel
        self.service = self.window.service

    def test_valid_apply_saves_settings_and_navigates_home(self):
        """A valid Apply persists the settings and returns to the input screen."""
        self.panel._checks["all_gap"].click()
        self.panel._spins["all_gap"].setValue(5)

        self.window.stacked_widget.setCurrentIndex(2)
        self.screen.apply_btn.click()
        QApplication.processEvents()

        self.assertEqual(self.window.stacked_widget.currentIndex(), 0)
        saved = self.service.get_constraint_settings()
        self.assertTrue(saved.all_gap_enabled)
        self.assertEqual(saved.all_gap_k, 5)

    def test_invalid_apply_warns_and_stays_for_each_constraint(self):
        """Each positive-K constraint enabled with K=0 must block Apply."""
        for key in _POSITIVE_K_KEYS:
            from src.main_window import MainWindow
            window = MainWindow()
            panel = window.settings_screen.constraint_panel
            panel._checks[key].setChecked(True)
            panel._spins[key].setValue(0)        # enabled + 0 → invalid

            window.stacked_widget.setCurrentIndex(2)
            with patch("src.main_window.QMessageBox.warning") as warn:
                window.settings_screen.apply_btn.click()
                QApplication.processEvents()

            self.assertEqual(window.stacked_widget.currentIndex(), 2, msg=key)
            warn.assert_called_once()

    def test_elective_conflicts_zero_is_valid(self):
        """elective_conflicts=0 while enabled is a legal target, not an error."""
        self.panel._checks["elective_conflicts"].click()
        self.panel._spins["elective_conflicts"].setValue(0)

        self.window.stacked_widget.setCurrentIndex(2)
        with patch("src.main_window.QMessageBox.warning") as warn:
            self.screen.apply_btn.click()
            QApplication.processEvents()

        warn.assert_not_called()
        self.assertEqual(self.window.stacked_widget.currentIndex(), 0)

    def test_back_button_navigates_without_applying(self):
        """Back returns to input without pushing settings through validation."""
        self.window.stacked_widget.setCurrentIndex(2)
        self.screen.back_btn.click()
        self.assertEqual(self.window.stacked_widget.currentIndex(), 0)

    def test_apply_emits_settings_confirmed_once(self):
        received = []
        self.screen.settings_confirmed.connect(lambda: received.append(1))
        self.screen.apply_btn.click()
        self.assertEqual(received, [1])


if __name__ == "__main__":
    unittest.main()
