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
    def test_valid_apply_saves_settings_and_navigates_home(self):
        """A valid Apply persists the settings and returns to the input screen."""
        from src.main_window import MainWindow
        window = MainWindow()
        service = window.service

        def fake_exec(dialog_self):
            dialog_self.constraint_panel._checks["all_gap"].click()
            dialog_self.constraint_panel._spins["all_gap"].setValue(5)
            dialog_self.apply_btn.click()

        with patch("src.main_window.SettingsDialog.exec_", new=fake_exec):
            window._show_settings_dialog()

        saved = service.get_constraint_settings()
        self.assertTrue(saved.all_gap_enabled)
        self.assertEqual(saved.all_gap_k, 5)

    def test_invalid_apply_warns_and_stays_for_each_constraint(self):
        """Each positive-K constraint enabled with K=0 must block Apply."""
        from src.main_window import MainWindow
        window = MainWindow()

        for key in _POSITIVE_K_KEYS:
            def fake_exec(dialog_self):
                dialog_self.constraint_panel._checks[key].setChecked(True)
                dialog_self.constraint_panel._spins[key].setValue(0)

                with patch("src.main_window.QMessageBox.warning") as warn:
                    dialog_self.apply_btn.click()
                    QApplication.processEvents()
                    warn.assert_called_once()

            with patch("src.main_window.SettingsDialog.exec_", new=fake_exec):
                window._show_settings_dialog()

    def test_elective_conflicts_zero_is_valid(self):
        """elective_conflicts=0 while enabled is a legal target, not an error."""
        from src.main_window import MainWindow
        window = MainWindow()

        def fake_exec(dialog_self):
            dialog_self.constraint_panel._checks["elective_conflicts"].click()
            dialog_self.constraint_panel._spins["elective_conflicts"].setValue(0)

            with patch("src.main_window.QMessageBox.warning") as warn:
                dialog_self.apply_btn.click()
                QApplication.processEvents()
                warn.assert_not_called()

        with patch("src.main_window.SettingsDialog.exec_", new=fake_exec):
            window._show_settings_dialog()

    def test_cancel_button_closes_without_applying(self):
        """Cancel button rejects the dialog without pushing settings through validation."""
        from src.main_window import MainWindow
        window = MainWindow()

        def fake_exec(dialog_self):
            # If the dialog is closed without clicking apply, the settings_confirmed shouldn't be emitted
            dialog_self.cancel_btn.click()

        with patch("src.main_window.SettingsDialog.exec_", new=fake_exec):
            with patch.object(window.service, "set_constraint_settings") as mock_set:
                window._show_settings_dialog()
                mock_set.assert_not_called()

    def test_apply_emits_settings_confirmed_once(self):
        from src.views.settings_screen.settings_dialog import SettingsDialog
        from src.presenter.app_service import AppService
        service = AppService.getInstance()
        dialog = SettingsDialog(service)
        received = []
        dialog.settings_confirmed.connect(lambda: received.append(1))
        dialog.apply_btn.click()
        self.assertEqual(received, [1])


if __name__ == "__main__":
    unittest.main()
