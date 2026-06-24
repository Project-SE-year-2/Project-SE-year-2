import unittest
from unittest.mock import MagicMock, patch
import sys

from datetime import date
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QShowEvent, QHideEvent
from PyQt5.QtCore import QPoint

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.output_screen.output_screen import OutputScreen
from src.views.output_screen.window_state import WindowState
from src.views.settings_screen.ranking_config_widget import RankingConfigWidget


class TestOutputScreen(unittest.TestCase):

    def setUp(self):
        self.mock_service = MagicMock()
        self.screen = OutputScreen(self.mock_service)

    # ------------------------------------------------------------------
    # Basic structure
    # ------------------------------------------------------------------

    def test_ui_components_exist(self):
        self.assertIsNotNone(self.screen.back_btn)
        self.assertIsNotNone(self.screen.download_btn)
        self.assertIsNotNone(self.screen.four_month)
        self.assertIsNotNone(self.screen.navigator)
        self.assertIsInstance(self.screen.ranking_panel, RankingConfigWidget)

    # ------------------------------------------------------------------
    # Show / hide events
    # ------------------------------------------------------------------

    def test_show_event_calls_get_period_schedule(self):
        """showEvent calls get_period_schedule for the active period."""
        self.mock_service.get_period_schedule.return_value = [_make_minimal_exam()]
        self.mock_service.get_schedule_count.return_value = 1
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen.showEvent(QShowEvent())
        self.mock_service.get_period_schedule.assert_called()

    def test_show_event_with_empty_period_shows_empty_state(self):
        """When get_period_schedule returns [] the screen shows the empty state (no crash)."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        # Must not raise even when there is nothing to display
        self.screen.showEvent(QShowEvent())

    def test_hide_event_stops_polling(self):
        self.mock_service.get_schedule_count.return_value = 1
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_periods.return_value = []
        self.screen.showEvent(QShowEvent())
        self.screen.showEvent(QShowEvent())
        self.assertTrue(self.screen.poll_timer.isActive())
        self.screen.hideEvent(QHideEvent())
        self.assertFalse(self.screen.poll_timer.isActive())

    # ------------------------------------------------------------------
    # Polling / counter
    # ------------------------------------------------------------------

    def test_polling_updates_counter_calls_get_schedule_count(self):
        """Polling calls get_schedule_count(period_id=...) to check for data."""
        self.mock_service.get_schedule_count.return_value = 1
        self.mock_service.get_period_schedule.return_value = [_make_minimal_exam()]
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._poll_schedule_count()
        self.mock_service.get_schedule_count.assert_called()

    def test_polling_with_zero_count_updates_navigator(self):
        """When get_schedule_count returns 0, navigator is hidden."""
        self.mock_service.get_schedule_count.return_value = 0
        self.screen._poll_schedule_count()
        self.mock_service.get_schedule_count.assert_called()

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    @patch('src.views.output_screen.output_screen.QFileDialog.getSaveFileName')
    @patch('src.views.output_screen.output_screen.QMessageBox.information')
    def test_download_calls_export_by_period_indices(self, _mock_msg, mock_dialog):
        """Download must call export_by_period_indices with the current per-period indices."""
        mock_path = 'C:/fake/path/schedule.csv'
        mock_dialog.return_value = (mock_path, '')
        # At least one period has data
        self.mock_service.get_schedule_count.return_value = 1

        self.screen._on_download_clicked()

        self.mock_service.export_by_period_indices.assert_called_once()
        call_args = self.mock_service.export_by_period_indices.call_args
        # Second positional argument is the file path
        self.assertEqual(call_args[0][1], mock_path)

    @patch('src.views.output_screen.output_screen.QFileDialog.getSaveFileName')
    @patch('src.views.output_screen.output_screen.QMessageBox.information')
    def test_download_passes_period_indices_to_export(self, _mock_msg, mock_dialog):
        """export_by_period_indices receives the screen's _period_indices dict."""
        mock_path = 'C:/fake/path/schedule.csv'
        mock_dialog.return_value = (mock_path, '')
        self.mock_service.get_schedule_count.return_value = 1

        self.screen._on_download_clicked()

        call_args = self.mock_service.export_by_period_indices.call_args
        passed_indices = call_args[0][0]
        self.assertIsInstance(passed_indices, dict)

    @patch('src.views.output_screen.output_screen.QMessageBox.warning')
    def test_download_warns_when_no_data_in_either_mode(self, mock_warn):
        """Download shows a warning when no period has any schedules."""
        self.mock_service.get_schedule_count.return_value = 0
        self.screen._on_download_clicked()
        mock_warn.assert_called_once()

    # ------------------------------------------------------------------
    # _get_program_names
    # ------------------------------------------------------------------

    def test_get_program_names_returns_id_to_name_mapping(self):
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
            {"id": "83102", "name": "Electrical Engineering"},
        ]
        result = self.screen._get_program_names()
        self.assertEqual(result, {
            "83101": "Computer Engineering",
            "83102": "Electrical Engineering",
        })

    def test_get_program_names_returns_empty_dict_when_service_raises(self):
        self.mock_service.get_available_programs.side_effect = RuntimeError("db error")
        self.assertEqual(self.screen._get_program_names(), {})

    def test_get_program_names_returns_empty_dict_when_service_returns_empty(self):
        self.mock_service.get_available_programs.return_value = []
        self.assertEqual(self.screen._get_program_names(), {})

    # ------------------------------------------------------------------
    # _on_exam_clicked / _on_exam_day_clicked → DayDetailDialog
    # ------------------------------------------------------------------

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_opens_day_detail_dialog(self, MockDialog):
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
        ]
        exam_data = _make_minimal_exam()

        # _on_exam_clicked is the old compat shim; it still needs to open the dialog
        self.screen._on_exam_clicked(exam_data)

        # Verify the dialog was instantiated and displayed
        MockDialog.assert_called_once()
        call_kwargs = MockDialog.call_args
        # Dialog is now called with keyword args; exams is a list containing the exam
        passed_exams = call_kwargs.kwargs.get("exams", [])
        self.assertIn(exam_data, passed_exams)

        # Verify the dialog was displayed
        MockDialog.return_value.show.assert_called_once()

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_passes_program_names_to_dialog(self, MockDialog):
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
            {"id": "83104", "name": "Industrial Engineering"},
        ]
        self.screen._on_exam_clicked(_make_minimal_exam())

        kw = MockDialog.call_args[1]
        self.assertIn("program_names", kw)
        self.assertEqual(kw["program_names"], {
            "83101": "Computer Engineering",
            "83104": "Industrial Engineering",
        })

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_calendar_exam_clicked_signal_is_NOT_connected(self, MockDialog):
        """calendar.exam_clicked must NOT be connected to any slot in OutputScreen.

        CalendarTableWidget always emits both exam_clicked AND exams_day_clicked
        when a badge is pressed.  Connecting both would cause _on_exam_day_clicked
        to fire twice, opening the detail dialog two times in a row.
        Only exams_day_clicked is wired; exam_clicked must remain silent."""
        self.mock_service.get_available_programs.return_value = []

        # Emit the single-exam signal directly — no dialog should appear.
        self.screen.calendar.exam_clicked.emit(_make_minimal_exam())

        MockDialog.assert_not_called()

    # ------------------------------------------------------------------
    # Isolated per-period fetching (new architecture)
    # ------------------------------------------------------------------

    def test_refresh_display_calls_get_period_schedule(self):
        """_refresh_screen_display fetches from get_period_schedule for the active period."""
        exams = [_make_minimal_exam(), _make_minimal_exam()]
        self.mock_service.get_period_schedule.return_value = exams
        self.mock_service.get_schedule_count.return_value = 1
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._refresh_screen_display()
        self.mock_service.get_period_schedule.assert_called_once_with("FALL_Aleph", 0)

    def test_refresh_display_with_no_data_shows_empty_state(self):
        """When get_period_schedule returns [] the screen shows empty (no exception)."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._refresh_screen_display()  # must not raise

    def test_navigator_index_changed_updates_period_index(self):
        """_on_navigator_index_changed stores the new index for the active period only."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 3
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._on_navigator_index_changed(2)
        self.assertEqual(self.screen._window_states["FALL_Aleph"].current(), 2)

    def test_navigator_index_changed_does_not_affect_other_periods(self):
        """Advancing index for FALL_Aleph must not change SPRI_Aleph's index."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 5
        self.mock_service.get_periods.return_value = []
        self.screen._on_navigator_index_changed(3)
        # Other periods stay at their initial value (0)
        self.assertEqual(self.screen._window_states["SPRI_Aleph"].current(), 0)

    def test_navigator_index_changed_calls_get_period_schedule_with_new_index(self):
        """After advancing the index, _refresh_screen_display fetches at the new index."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 5
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._on_navigator_index_changed(4)
        self.mock_service.get_period_schedule.assert_called_with("FALL_Aleph", 4)

    # ------------------------------------------------------------------
    # exams_day_clicked (list[dict], QPoint) new API
    # ------------------------------------------------------------------

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_signal_connected(self, MockDialog):
        """calendar.exams_day_clicked must be wired to _on_exam_day_clicked."""
        self.mock_service.get_available_programs.return_value = []
        exams = [_make_minimal_exam(), _make_minimal_exam()]

        self.screen.calendar.exams_day_clicked.emit(exams, QPoint(100, 200))

        MockDialog.assert_called_once()

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_passes_full_list_to_dialog(self, MockDialog):
        """_on_exam_day_clicked must forward the complete exam list to DayDetailDialog
        without any secondary lookup into exams_by_date."""
        self.mock_service.get_available_programs.return_value = []
        exam1 = _make_minimal_exam()
        exam2 = {**_make_minimal_exam(), "course_number": "83222"}
        exams = [exam1, exam2]
        # Emit the signal with a dummy anchor point since it's required by the signature
        self.screen._on_exam_day_clicked(exams, QPoint(50, 50))
        # Extract the exams kwarg passed to the dialog constructor and verify it matches
        kw = MockDialog.call_args[1]
        self.assertEqual(kw["exams"], exams)
        self.assertIn(exam1, kw["exams"])
        self.assertIn(exam2, kw["exams"])

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_passes_anchor_to_dialog(self, MockDialog):
        """The QPoint anchor received from the signal must be forwarded to DayDetailDialog."""
        self.mock_service.get_available_programs.return_value = []
        # Emit the signal with a specific anchor point
        anchor = QPoint(123, 456)
        self.screen._on_exam_day_clicked([_make_minimal_exam()], anchor)
        # Extract the anchor_pos kwarg passed to the dialog constructor and verify it matches
        kw = MockDialog.call_args[1]
        self.assertEqual(kw["anchor_pos"], anchor)

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_shim_wraps_single_exam_in_list(self, MockDialog):
        """The backward-compat _on_exam_clicked shim must wrap the single exam dict
        in a list so DayDetailDialog always receives a list[dict]."""
        self.mock_service.get_available_programs.return_value = []
        exam = _make_minimal_exam()

        self.screen._on_exam_clicked(exam)

        kw = MockDialog.call_args[1]
        self.assertIsInstance(kw["exams"], list)
        self.assertIn(exam, kw["exams"])

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_shim_passes_no_anchor(self, MockDialog):
        """When called via the single-exam shim the anchor_pos must be None."""
        self.mock_service.get_available_programs.return_value = []
        self.screen._on_exam_clicked(_make_minimal_exam())

        kw = MockDialog.call_args[1]
        self.assertIsNone(kw["anchor_pos"])

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_opens_dialog(self, MockDialog):
        """DayDetailDialog.show() must be called to display the dialog."""
        self.mock_service.get_available_programs.return_value = []
        # Emit the signal with a dummy exam list and anchor point
        self.screen._on_exam_day_clicked([_make_minimal_exam()], QPoint(0, 0))
        
        # Verify that show() was called (since it's a non-blocking dialog)
        MockDialog.return_value.show.assert_called_once()

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_opens_dialog_with_list(self, MockDialog):
        """Verify the new multi-exam workflow triggered by exams_day_clicked."""
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
        ]

        exam_list = [
            {"course_number": "101", "exam_date": date(2026, 6, 10)},
            {"course_number": "102", "exam_date": date(2026, 6, 10)},
        ]
        anchor_point = QPoint(100, 100)
        # Emit the signal as if the user clicked on a day cell with multiple exams
        self.screen.calendar.exams_day_clicked.emit(exam_list, anchor_point)
        # Verify the dialog was constructed with the full exam list and correct anchor
        MockDialog.assert_called_once()
        _, kwargs = MockDialog.call_args
        self.assertEqual(kwargs["exams"], exam_list)
        self.assertEqual(kwargs["anchor_pos"], anchor_point)
        self.assertEqual(kwargs["program_names"], {"83101": "Computer Engineering"})

    # ------------------------------------------------------------------
    # Semester tab switching
    # ------------------------------------------------------------------

    def test_semester_switch_updates_current_semester(self):
        """Switching semester tab updates _current_semester."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = []

        self.screen._on_semester_changed("SPRING")
        self.assertEqual(self.screen._current_semester, "SPRING")

    def test_semester_switch_restores_stored_index(self):
        """Switching to a semester whose period has a stored index uses that index."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 5
        self.mock_service.get_periods.return_value = []

        # Set a stored index for SPRI_Aleph
        self.screen._window_states["SPRI_Aleph"].move_to(3)
        self.screen._on_semester_changed("SPRING")

        self.assertEqual(self.screen._global_index, 3)

    def test_semester_switch_calls_refresh(self):
        """Semester switch triggers a display refresh."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = []

        self.screen._on_semester_changed("SUMMER")
        # get_period_schedule should be called with the SUMM_Aleph period
        self.mock_service.get_period_schedule.assert_called_with("SUMM_Aleph", 0)

    # ------------------------------------------------------------------
    # Moed switching
    # ------------------------------------------------------------------

    def test_moed_switch_updates_current_moed(self):
        """Switching moed updates _current_moed."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = []

        self.screen._on_moed_changed("Bet")
        self.assertEqual(self.screen._current_moed, "Bet")

    def test_moed_switch_changes_active_period_id(self):
        """After switching moed, _active_period_id reflects the new moed."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = []

        self.screen._on_moed_changed("Bet")
        self.assertEqual(self.screen._active_period_id(), "FALL_Bet")

    # ------------------------------------------------------------------
    # Per-period navigation isolation
    # ------------------------------------------------------------------

    def test_advancing_fall_does_not_change_spring_index(self):
        """Navigating forward in FALL_Aleph must not change SPRI_Aleph."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 10
        self.mock_service.get_periods.return_value = []

        self.screen._current_semester = "FALL"
        self.screen._on_navigator_index_changed(5)

        self.assertEqual(self.screen._window_states["FALL_Aleph"].current(), 5)
        self.assertEqual(self.screen._window_states["SPRI_Aleph"].current(), 0)
        self.assertEqual(self.screen._window_states["SUMM_Aleph"].current(), 0)

    def test_switching_semester_preserves_previous_index(self):
        """Going FALL→SPRING→FALL restores FALL's stored index."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 10
        self.mock_service.get_periods.return_value = []

        self.screen._current_semester = "FALL"
        self.screen._on_navigator_index_changed(7)

        self.screen._on_semester_changed("SPRING")
        self.screen._on_semester_changed("FALL")

        self.assertEqual(self.screen._global_index, 7)

    # ------------------------------------------------------------------
    # Polling behavior
    # ------------------------------------------------------------------

    def test_polling_detects_first_data_arrival(self):
        """When polling detects the first data (was_empty=True), refresh is triggered."""
        self.mock_service.get_period_schedule.return_value = [_make_minimal_exam()]
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]

        # Start with no data
        self.screen._global_total = 0
        self.mock_service.get_schedule_count.return_value = 5

        self.screen._poll_schedule_count()
        # Total should now be updated
        self.assertEqual(self.screen._global_total, 5)

    def test_polling_with_exception_does_not_crash(self):
        """Polling must not crash if get_schedule_count raises."""
        self.mock_service.get_schedule_count.side_effect = RuntimeError("db error")
        self.mock_service.get_period_schedule.return_value = []
        # Must not raise
        self.screen._poll_schedule_count()

    # ------------------------------------------------------------------
    # Listener integration signals
    # ------------------------------------------------------------------

    def test_on_period_ready_updates_total_for_active_period(self):
        """_on_period_ready updates _global_total when the active period gets data."""
        self.mock_service.get_schedule_count.return_value = 42
        self.mock_service.get_period_schedule.return_value = [_make_minimal_exam()]
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]

        self.screen._current_semester = "FALL"
        self.screen._current_moed = "Aleph"
        self.screen._on_period_ready("FALL_Aleph")

        self.assertGreaterEqual(self.screen._global_total, 42)

    def test_on_period_ready_ignores_non_active_period(self):
        """_on_period_ready for a different semester does not trigger refresh."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0

        self.screen._current_semester = "FALL"
        self.screen._on_period_ready("SPRI_Aleph")

        # get_period_schedule should NOT be called since SPRI is not active
        self.mock_service.get_period_schedule.assert_not_called()

    def test_on_generation_finished_resets_all_indices(self):
        """_on_generation_finished resets all period indices to 0."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 10
        self.mock_service.get_periods.return_value = []

        # Set some non-zero indices for FALL_Aleph and SPRI_Bet
        self.screen._window_states["FALL_Aleph"].move_to(5)
        self.screen._window_states["SPRI_Bet"].move_to(3)

        self.screen._on_generation_finished(100)

        self.assertEqual(self.screen._window_states["FALL_Aleph"].current(), 0)
        self.assertEqual(self.screen._window_states["SPRI_Bet"].current(), 0)
        self.assertEqual(self.screen._window_states["FALL_Aleph"].history_stack, [])
        self.assertEqual(self.screen._window_states["SPRI_Bet"].history_stack, [])
        self.assertEqual(self.screen._global_index, 0)

    def test_on_generation_error_shows_error(self):
        """_on_generation_error re-enables tabs (no crash)."""
        # Must not raise
        self.screen._on_generation_error("Something went wrong")

    # ------------------------------------------------------------------
    # Show/hide re-entry
    # ------------------------------------------------------------------

    def test_show_event_with_existing_data_does_not_reset_indices(self):
        """Re-showing with _global_total > 0 preserves stored indices."""
        self.mock_service.get_period_schedule.return_value = [_make_minimal_exam()]
        self.mock_service.get_schedule_count.return_value = 5
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]

        self.screen._global_total = 5
        self.screen._window_states["FALL_Aleph"].move_to(3)

        self.screen.showEvent(QShowEvent())

        # Index must NOT be reset to 0
        self.assertEqual(self.screen._window_states["FALL_Aleph"].current(), 3)

    # ------------------------------------------------------------------
    # Navigator visibility
    # ------------------------------------------------------------------

    def test_navigator_hidden_when_no_schedules(self):
        """Navigator bar is hidden when the active period has 0 schedules."""
        self.mock_service.get_schedule_count.return_value = 0
        self.screen._update_navigator()
        self.assertTrue(self.screen.navigator.isHidden())

    def test_navigator_visible_when_schedules_exist(self):
        """Navigator bar is visible when the active period has schedules."""
        self.mock_service.get_schedule_count.return_value = 5
        self.screen._update_navigator()
        self.assertFalse(self.screen.navigator.isHidden())

    # ------------------------------------------------------------------
    # Back button
    # ------------------------------------------------------------------

    def test_back_button_emits_switch_to_input(self):
        """Back button emits switch_to_input signal."""
        with unittest.mock.patch.object(self.screen, 'switch_to_input') as mock_signal:
            self.screen._on_back_clicked()
            mock_signal.emit.assert_called_once()


    def test_window_state_starts_at_zero(self):
        """Verify that every OutputScreen WindowState starts at index 0."""
        for state in self.screen._window_states.values():
            self.assertEqual(state.current(), 0)


    def test_period_ready_shows_sorting_update_banner_when_schedule_already_displayed(self):
        """Verify that new active-period data shows a refresh banner instead of auto-refreshing."""
        self.mock_service.get_schedule_count.return_value = 5
        self.screen._current_semester = "FALL"
        self.screen._current_moed = "Aleph"
        self.screen._calendar_displaying_data = True

        self.screen._on_period_ready("FALL_Aleph")

        self.assertTrue(self.screen._active_window_state().has_pending_update)
        self.assertFalse(self.screen._sorting_update_banner.isHidden())


    def test_period_ready_ignores_non_active_period_for_sorting_banner(self):
        """Verify that non-active period updates do not show the refresh banner."""
        self.mock_service.get_schedule_count.return_value = 5
        self.screen._current_semester = "FALL"
        self.screen._current_mode = "Aleph"
        self.screen._calendar_displaying_data = True

        self.screen._on_period_ready("SPRI_Aleph")

        self.assertFalse(self.screen._active_window_state().has_pending_update)
        self.assertFalse(self.screen._sorting_update_banner.isVisible())


    def test_refresh_pending_accepts_update_hides_banner_and_refreshes(self):
        """Verify that Refresh View accepts the pending update, hides the banner, and refreshes display."""
        state = self.screen._active_window_state()
        state.mark_pending()
        self.screen._sorting_update_banner.setVisible(True)

        with patch.object(self.screen, "_refresh_screen_display") as mock_refresh:
            self.screen._on_refresh_pending_clicked()

        self.assertFalse(state.has_pending_update)
        self.assertFalse(self.screen._sorting_update_banner.isVisible())
        mock_refresh.assert_called_once()


    def test_semester_change_hides_sorting_update_banner(self):
        """Verify that changing semester hides any pending update banner."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = []
        self.screen._sorting_update_banner.setVisible(True)

        self.screen._on_semester_changed("SPRING")

        self.assertFalse(self.screen._sorting_update_banner.isVisible())


    def test_generation_finished_clears_pending_update_and_hides_banner(self):
        """Verify that generation completion clears pending state and hides the update banner."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = []

        state = self.screen._active_window_state()
        state.mark_pending()
        self.screen._sorting_update_banner.setVisible(True)

        self.screen._on_generation_finished(0)

        self.assertFalse(state.has_pending_update)
        self.assertFalse(self.screen._sorting_update_banner.isVisible())


    def test_mark_pending_sets_pending_update_flag(self):
        """Verify that mark_pending records that newer optimized results are available."""
        state = WindowState()

        state.mark_pending()

        assert state.has_pending_update is True


    def test_accept_pending_clears_pending_update_flag(self):
        """Verify that accept_pending clears the pending optimized-results marker."""
        state = WindowState()
        state.mark_pending()

        state.accept_pending()

        assert state.has_pending_update is False


    def test_clear_resets_pending_update_flag(self):
        """Verify that clear also removes any pending optimized-results marker."""
        state = WindowState()
        state.mark_pending()

        state.clear()

        assert state.has_pending_update is False

def test_move_to_updates_current_and_history():
    """Verify that move_to stores the previous index and updates current."""
    state = WindowState()
    state.move_to(3)

    assert state.current() == 3
    assert state.history_stack == [0]


def test_back_restores_previous_index():
    """Verify that back returns to the previous index."""
    state = WindowState()
    state.move_to(2)
    state.move_to(5)

    assert state.back() == 2
    assert state.current() == 2


def test_clear_resets_state():
    """Verify that clear resets current, history."""
    state = WindowState()
    state.move_to(3)

    state.clear()

    assert state.current() == 0
    assert state.history_stack == []

# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _make_minimal_exam() -> dict:
    return {
        "course_number": "83111",
        "course_name":   "Data Structures",
        "type":          "Obligatory",
        "programs":      ["83101"],
        "exam_date":     date(2026, 9, 10),
        "semester":      "FALL",
        "moed":          "Aleph",
    }






if __name__ == '__main__':
    unittest.main()

