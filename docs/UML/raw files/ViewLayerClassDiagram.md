# View Layer Class Diagram (Overview)

High-level overview of the PyQt5 View layer: the two screens, the background worker thread, and shared reusable components. For widget-level detail see `InputScreenDiagram` and `OutputScreenDiagram`.

```mermaid
classDiagram
    direction TB

    %% ===== Root Window =====
    class MainWindow {
        -service: AppService
        -stacked_widget: QStackedWidget
        -input_screen: InputScreen
        -output_screen: OutputScreen
        +_init_screens()
        +_show_output_screen()
        +_show_input_screen()
    }

    %% ===== Screens =====
    class InputScreen {
        -service: IAppService
        -_worker: EngineListener
        +switch_to_output: pyqtSignal
        +_on_files_loaded()
        +_on_programs_selected(ids)
        +_on_period_selected(period_id)
        +_on_generate_clicked()
        +_on_generation_finished(count)
        +_on_period_ready(period_id)
        +_on_error(message)
    }


    class OutputScreen {
        -service: IAppService
        +switch_to_input: pyqtSignal
        +connect_listener(listener)
        +_on_period_ready(period_id)
        +_on_generation_finished(total)
    }


    %% ===== Background Thread =====
    class EngineListener {
        -_service: IAppService
        +period_ready: pyqtSignal(str)
        +finished: pyqtSignal(int)
        +error: pyqtSignal(str)
        +__init__(service)
        +run()
    }


    %% ===== Shared Components =====
    class ErrorBanner {
        +dismissed: pyqtSignal
        +show_error(message)
        +hide_error()
    }

    class LoadingSpinner {
        +start()
        +stop()
    }

    class CalendarTableWidget {
        -mode: CalendarMode
        +day_clicked: pyqtSignal
        +exams_day_clicked: pyqtSignal
        +save_requested: pyqtSignal
        +update_schedule(schedule_data, unavailable_dates)
        +set_date_range(start, end)
        +set_unavailable_days(days)
        +get_unavailable_days() list
    }

    class ScheduleNavigatorWidget {
        +navigate_to: pyqtSignal(int)
        +prefetch_needed: pyqtSignal(int)
        +current_index: int
        +set_state(current, total, loaded)
    }

    class TypeBadge {
        +set_type(type_str)
    }

    class PrimaryButton { }
    class SecondaryButton { }
    class DangerButton { }

    %% ===== Calendar Sub-components =====
    class MonthGrid {
        +update_month(year, month, exams, unavailable)
    }

    class InputDayCell {
        -is_forbidden: bool
        -has_exam: bool
    }

    class OutputDayCell {
        -exams: list
        -is_exam_day: bool
    }

    %% ===== Threading Model =====
    %% ===== Relationships =====
    MainWindow --> InputScreen : creates and injects service
    MainWindow --> OutputScreen : creates and injects service

    InputScreen --> EngineListener : creates on generate click
    OutputScreen --> EngineListener : connect_listener()

    CalendarTableWidget --> MonthGrid : contains
    CalendarTableWidget --> InputDayCell : creates in INPUT mode
    CalendarTableWidget --> OutputDayCell : creates in OUTPUT mode

    MonthGrid --> InputDayCell : creates in INPUT mode
    MonthGrid --> OutputDayCell : creates in OUTPUT mode
```

## Overview
- **MainWindow**: Root `QMainWindow`; owns a `QStackedWidget` with `InputScreen` at index 0 and `OutputScreen` at index 1.
- **InputScreen**: The full input flow screen — see `InputScreenDiagram` for all contained widgets.
- **OutputScreen**: The schedule display screen — see `OutputScreenDiagram` for all contained components.
- **EngineListener**: `QThread` subclass (re-exported as `GenerateWorker` for backward compatibility). Runs `IAppService.generate_stream()` on a background thread; emits `period_ready`, `finished`, `error` signals back to the Qt main thread.
- **CalendarTableWidget**: Dual-mode (INPUT/OUTPUT) calendar shared between `PeriodEditorWidget` and `OutputScreen`. In INPUT mode shows forbidden-day toggles; in OUTPUT mode shows exam assignments.
- **MonthGrid / InputDayCell / OutputDayCell**: Low-level calendar rendering components inside `CalendarTableWidget`.
- **ErrorBanner, LoadingSpinner, TypeBadge, PrimaryButton, SecondaryButton, DangerButton**: Shared UI components used across multiple screens and widgets.

## Threading Model
| Thread | Runs |
|--------|------|
| Qt main thread (event loop) | All widgets, screens, `MainWindow` |
| Background QThread | `EngineListener.run()` only |

Signals (`period_ready`, `finished`, `error`) are automatically queued across the thread boundary by Qt — no manual locking needed.
