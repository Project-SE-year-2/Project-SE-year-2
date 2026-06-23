"""Tests for RankingConfigWidget (EP-112 — drag-and-drop with checkbox priority)."""

import sys
import unittest

from PyQt5.QtWidgets import QApplication, QListWidget

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.settings_screen.ranking_config_widget import (
    RankingConfigWidget,
    _RowWidget,
    _DEFAULT_ORDER,
    _METRIC_DESCRIPTIONS,
)

ALL_KEYS = list(_METRIC_DESCRIPTIONS.keys())


class TestRankingConfigWidgetStructure(unittest.TestCase):
    """Widget builds correctly and exposes expected internal components."""

    def setUp(self):
        self.widget = RankingConfigWidget()

    def test_instantiates_without_error(self):
        self.assertIsNotNone(self.widget)

    def test_list_widget_exists(self):
        self.assertIsInstance(self.widget._list, QListWidget)

    def test_list_has_five_rows(self):
        self.assertEqual(self.widget._list.count(), 5)

    def test_drag_drop_mode_is_internal_move(self):
        from PyQt5.QtWidgets import QAbstractItemView
        self.assertEqual(
            self.widget._list.dragDropMode(),
            QAbstractItemView.InternalMove,
        )

    def test_each_item_has_row_widget(self):
        """Every list item must have a _RowWidget set as its item widget."""
        for i in range(self.widget._list.count()):
            item = self.widget._list.item(i)
            w = self.widget._list.itemWidget(item)
            self.assertIsInstance(w, _RowWidget, msg=f"Row {i} has no _RowWidget")

    def test_all_keys_present(self):
        keys = [
            self.widget._list.item(i).data(0x0100)  # Qt.UserRole
            for i in range(self.widget._list.count())
        ]
        self.assertEqual(sorted(keys), sorted(ALL_KEYS))


class TestRankingConfigWidgetDefaultState(unittest.TestCase):
    """On first load all rows are checked and numbered 1-5."""

    def setUp(self):
        self.widget = RankingConfigWidget()

    def test_all_checkboxes_unchecked_by_default(self):
        """No row should be active until the user explicitly selects it."""
        for i in range(self.widget._list.count()):
            w: _RowWidget = self.widget._list.itemWidget(self.widget._list.item(i))
            self.assertFalse(w.checkbox.isChecked(), msg=f"Row {i} should start unchecked")

    def test_all_badges_empty_by_default(self):
        """All badges must show no number when nothing is selected."""
        for i in range(self.widget._list.count()):
            w: _RowWidget = self.widget._list.itemWidget(self.widget._list.item(i))
            self.assertEqual(w.badge.text(), "", msg=f"Row {i} badge should be empty")

    def test_default_sort_order_is_empty(self):
        """get_sort_order() must return an empty list when nothing is checked."""
        self.assertEqual(self.widget.get_sort_order(), [])


class TestRankingConfigWidgetCheckboxBehaviour(unittest.TestCase):
    """Unchecking a row removes it from get_sort_order and clears its badge."""

    def setUp(self):
        self.widget = RankingConfigWidget()

    def _row_widget(self, index: int) -> _RowWidget:
        return self.widget._list.itemWidget(self.widget._list.item(index))

    def test_unchecking_row_removes_it_from_sort_order(self):
        """Unchecking the first row must exclude its key from get_sort_order."""
        self._row_widget(0).checkbox.setChecked(False)
        order = self.widget.get_sort_order()
        self.assertNotIn(_DEFAULT_ORDER[0], order)

    def test_unchecking_row_clears_its_badge(self):
        """Unchecked row badge must be empty."""
        self._row_widget(1).checkbox.setChecked(False)
        self.assertEqual(self._row_widget(1).badge.text(), "")

    def test_unchecking_renumbers_remaining_badges(self):
        """After checking rows 0 and 1 then unchecking row 0, row 1 must become badge 1."""
        self._row_widget(0).checkbox.setChecked(True)
        self._row_widget(1).checkbox.setChecked(True)
        self._row_widget(0).checkbox.setChecked(False)
        self.assertEqual(self._row_widget(1).badge.text(), "1")

    def test_rechecking_restores_badge_number(self):
        """Re-checking a row must assign it the next available number."""
        self._row_widget(0).checkbox.setChecked(False)
        self._row_widget(0).checkbox.setChecked(True)
        # Row 0 is now at the end of the numbering (still row 0 visually → badge 1).
        self.assertEqual(self._row_widget(0).badge.text(), "1")

    def test_unchecking_all_returns_empty_sort_order(self):
        for i in range(self.widget._list.count()):
            self._row_widget(i).checkbox.setChecked(False)
        self.assertEqual(self.widget.get_sort_order(), [])

    def test_partial_selection_returns_only_checked_keys(self):
        """Only checked rows must appear in get_sort_order()."""
        # Check all, then uncheck rows 1 and 3.
        for i in range(self.widget._list.count()):
            self._row_widget(i).checkbox.setChecked(True)
        self._row_widget(1).checkbox.setChecked(False)
        self._row_widget(3).checkbox.setChecked(False)
        order = self.widget.get_sort_order()
        self.assertEqual(len(order), 3)
        self.assertNotIn(_DEFAULT_ORDER[1], order)
        self.assertNotIn(_DEFAULT_ORDER[3], order)


class TestRankingConfigWidgetGetSortOrder(unittest.TestCase):
    """get_sort_order() returns valid keys in correct sequence."""

    def setUp(self):
        self.widget = RankingConfigWidget()

    def test_returns_list_of_strings(self):
        self.assertIsInstance(self.widget.get_sort_order(), list)
        for k in self.widget.get_sort_order():
            self.assertIsInstance(k, str)

    def test_all_returned_keys_are_valid(self):
        for k in self.widget.get_sort_order():
            self.assertIn(k, ALL_KEYS)

    def test_no_duplicates_in_result(self):
        order = self.widget.get_sort_order()
        self.assertEqual(len(order), len(set(order)))


class TestRankingConfigWidgetSetSortOrder(unittest.TestCase):
    """set_sort_order() repopulates list from external sequence."""

    def setUp(self):
        self.widget = RankingConfigWidget()

    def test_set_sort_order_changes_order(self):
        new_order = [
            "elective_conflicts", "max_exams_per_day", "min_days_required",
            "avg_days_all", "span_required",
        ]
        self.widget.set_sort_order(new_order)
        self.assertEqual(self.widget.get_sort_order(), new_order)

    def test_set_sort_order_with_partial_checked(self):
        """Only the keys in the checked set should be active after set."""
        order = _DEFAULT_ORDER[:]
        checked = {"min_days_required", "span_required"}
        self.widget.set_sort_order(order, checked)
        result = self.widget.get_sort_order()
        self.assertIn("min_days_required", result)
        self.assertIn("span_required", result)
        self.assertNotIn("avg_days_all", result)

    def test_set_sort_order_ignores_unknown_keys(self):
        partial = ["min_days_required", "UNKNOWN", "avg_days_all"]
        self.widget.set_sort_order(partial)
        result = self.widget.get_sort_order()
        self.assertNotIn("UNKNOWN", result)

    def test_set_sort_order_roundtrip(self):
        order = ["span_required", "avg_days_all", "elective_conflicts",
                 "min_days_required", "max_exams_per_day"]
        self.widget.set_sort_order(order)
        self.assertEqual(self.widget.get_sort_order(), order)

    def test_set_sort_order_keeps_missing_metrics_visible(self):
        """set_sort_order must keep all known metrics visible even if the saved order is partial."""
        self.widget.set_sort_order(["min_days_required", "avg_days_all"])
        keys = [
            self.widget._list.item(i).data(0x0100)
            for i in range(self.widget._list.count())
        ]
        self.assertEqual(len(keys), 5)
        self.assertEqual(keys[:2], ["min_days_required", "avg_days_all"])
        self.assertEqual(set(keys), set(ALL_KEYS))


class TestRankingConfigWidgetItemData(unittest.TestCase):
    """Each list item stores the metric key as UserRole data."""

    def setUp(self):
        self.widget = RankingConfigWidget()

    def test_user_role_contains_valid_key(self):
        from PyQt5.QtCore import Qt
        for i in range(self.widget._list.count()):
            key = self.widget._list.item(i).data(Qt.UserRole)
            self.assertIn(key, ALL_KEYS, msg=f"Row {i} bad key: {key}")

    def test_row_widget_key_matches_item_user_role(self):
        """_RowWidget.key must match the item's UserRole data."""
        from PyQt5.QtCore import Qt
        for i in range(self.widget._list.count()):
            item = self.widget._list.item(i)
            w: _RowWidget = self.widget._list.itemWidget(item)
            self.assertEqual(w.key, item.data(Qt.UserRole))


if __name__ == "__main__":
    unittest.main()
