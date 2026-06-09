# Output Screen Class Diagram

Detailed structure of `OutputScreen` and all its display components: semester tabs, four-month calendar widget, schedule navigator, and day-detail popup.

```mermaid
classDiagram
    direction TB

    class OutputScreen {
        -service: IAppService
        -_nav_widget: ScheduleNavigatorWidget
        -_semester_tabs: SemesterTabsWidget
        -_calendar: FourMonthOutputWidget
        -_active_period_id: str
        -_current_index: int
        -_total_schedules: int
        +switch_to_input: pyqtSignal
        +current_index: int
        +total_schedules: int
        +connect_listener(listener)
        +_on_period_ready(period_id)
        +_on_generation_finished(total)
        +_on_generation_error(message)
        +_on_semester_changed(semester)
        +_on_moed_changed(moed)
        +_on_navigator_index_changed(index)
        +_on_prefetch_needed(loaded_so_far)
        +_on_exam_day_clicked(exams, anchor)
        +_on_back_clicked()
        +_on_download_clicked()
        -_refresh_screen_display()
        -_update_navigator()
        -_poll_schedule_count()
        -_get_program_names() dict
    }

    %% ===== Semester Navigation =====
    class SemesterTabsWidget {
        -_selected: str
        +semester_changed: pyqtSignal(str)
        +set_selected(semester)
        +current_semester() str
        +set_enabled_all(enabled)
    }

    class _SemesterTabCard {
        +clicked: pyqtSignal
        +set_selected(selected)
        +set_card_enabled(enabled)
    }

    %% ===== Calendar Display =====
    class FourMonthOutputWidget {
        +exam_day_clicked: pyqtSignal
        +moed_changed: pyqtSignal(str)
        +show_loading(semester)
        +show_error(message)
        +show_empty(semester)
        +show_schedule()
        +show_no_period(semester, moed)
        +update_schedule(rows, unavailable_dates, semester, start_date, end_date)
        -_rebuild_month_cards()
        -_on_cell_clicked(exams, anchor)
    }

    class MonthGrid {
        +update_month(year, month, exams, unavailable)
    }

    class OutputDayCell {
        -exams: list
        -is_exam_day: bool
    }

    %% ===== Schedule Navigation =====
    class ScheduleNavigatorWidget {
        +navigate_to: pyqtSignal(int)
        +prefetch_needed: pyqtSignal(int)
        +current_index: int
        +set_state(current, total, loaded)
    }

    %% ===== Day Detail Popup =====
    class DayDetailDialog {
        -exams: list[dict]
        -program_names: dict[str, str]
        +_build_ui()
    }

    class _ExamRow {
        -exam: dict
        -program_names: dict
    }

    %% ===== Shared Calendar Widget =====
    class CalendarTableWidget {
        -mode: CalendarMode
        +exams_day_clicked: pyqtSignal
        +exam_clicked: pyqtSignal
        +update_schedule(schedule_data, unavailable_dates)
        +set_month_schedule(year, month, exams, unavailable_dates)
    }

    %% ===== Relationships =====
    OutputScreen --> SemesterTabsWidget : contains
    OutputScreen --> FourMonthOutputWidget : contains
    OutputScreen --> ScheduleNavigatorWidget : contains
    OutputScreen --> DayDetailDialog : creates on cell click
    OutputScreen --> CalendarTableWidget : uses

    SemesterTabsWidget --> _SemesterTabCard : creates per semester

    FourMonthOutputWidget --> MonthGrid : creates 4 grids
    FourMonthOutputWidget --> ScheduleNavigatorWidget : contains

    MonthGrid --> OutputDayCell : creates per day

    DayDetailDialog --> _ExamRow : creates per exam
```

## Overview
- **OutputScreen**: Root output view. Connects to `EngineListener` signals via `connect_listener()` so it receives `period_ready` and `finished` events. Polls `get_schedule_count()` periodically while generation is in progress.
- **SemesterTabsWidget**: Horizontal tab row (FALL / SPRING / SUMMER). Emits `semester_changed` when the user switches tabs, triggering a calendar refresh.
- **FourMonthOutputWidget**: The main calendar display. Shows 4 `MonthGrid` cards side by side, one per calendar month. Supports loading/error/empty/no-period state pages. Emits `exam_day_clicked` when a cell with exams is clicked. Also contains the moed selector buttons (Aleph/Bet/Gimel).
- **MonthGrid**: Renders one calendar month as a grid of `OutputDayCell` objects.
- **OutputDayCell**: A single calendar cell that highlights exam days and fires a click signal when the user selects it.
- **ScheduleNavigatorWidget**: Prev/Next buttons with a counter ("3 / 120"). Emits `navigate_to(index)` and `prefetch_needed(loaded_so_far)` for lazy loading.
- **DayDetailDialog**: Popup that appears when the user clicks a day with exams. Lists each exam with its course name, type badge, programs, and date.
- **CalendarTableWidget**: Shared INPUT/OUTPUT calendar widget (also used by `PeriodEditorWidget` in INPUT mode for editing forbidden days).
