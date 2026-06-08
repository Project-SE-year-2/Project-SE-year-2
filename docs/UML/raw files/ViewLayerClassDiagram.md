# View Layer Class Diagram

Detailed structure of the PyQt5 View layer: screens, reusable widgets, view-model dataclasses, and the background worker thread. Everything above the dashed thread boundary runs on the Qt main thread; `GenerateWorker.run()` executes on a dedicated QThread.

```mermaid
classDiagram
    direction TB

    %% ===== Main Thread =====

    class MainWindow {
        -service: AppService
        -stacked_widget: QStackedWidget
        -input_screen: InputScreen
        -output_screen: OutputScreen
        +_init_screens()
        +_show_output_screen()
        +_show_input_screen()
    }

    class InputScreen {
        -service: IAppService
        -_worker: GenerateWorker
        +switch_to_output: pyqtSignal
        +_on_generate_clicked()
        +_on_generation_finished(count)
        +_on_period_ready(period_id)
        +_on_error(message)
    }

    class OutputScreen {
        -service: IAppService
        +switch_to_input: pyqtSignal
        +show_schedule()
        +export_schedule(index, path)
    }

    %% ===== Reusable Widgets (main thread) =====

    class FileLoaderWidget {
        -_service: IAppService
        -_validator: FilePathValidator
        -_courses_path: str
        -_dates_path: str
        +files_loaded: pyqtSignal
        +_choose_courses_file()
        +_choose_dates_file()
        +_load_files()
        -_get_mode() str
        -_set_loading_state(is_loading)
    }

    class FilePathValidator {
        +validate(courses_path, dates_path)
    }

    class ProgramListWidget {
        -_service: IAppService
        -_max_selection: int
        -_selected_ids: set[str]
        -_rows_by_id: dict[str, ProgramRowWidget]
        +programs_selected: pyqtSignal(list)
        +refresh()
        +selected_programs() list[str]
        +clear_selection()
        -_on_program_clicked(program_id)
        -_update_row_states()
    }

    class ProgramRowWidget {
        -program: ProgramItem
        -_selected: bool
        +set_selected(selected)
        +setDisabled(disabled)
    }

    class ProgramItem {
        <<dataclass>>
        +program_id: str
        +name: str
    }

    class PeriodListWidget {
        -_service: IAppService
        -_formatter: PeriodFormatter
        -_selected_period_id: str
        -_rows_by_id: dict[str, PeriodRowWidget]
        +period_selected: pyqtSignal(str)
        +refresh()
        +selected_period_id() str
        +clear_selection()
        -_on_period_clicked(period_id)
        -_update_row_states()
    }

    class PeriodRowWidget {
        -period: PeriodItem
        -_selected: bool
        +set_selected(selected)
    }

    class PeriodItem {
        <<dataclass>>
        +period_id: str
        +title: str
        +start_date: date
        +end_date: date
    }

    class PeriodFormatter {
        +format(period_dict) PeriodItem
        -_format_date(value) str
    }

    %% ===== Worker Thread =====

    class GenerateWorker {
        -_service: IAppService
        +period_ready: pyqtSignal(str)
        +finished: pyqtSignal(int)
        +error: pyqtSignal(str)
        +__init__(service)
        +run()
    }

    note for GenerateWorker "Runs on a background QThread.\nCommunicates back to main thread\nonly via Qt signals (thread-safe)."

    %% ===== Relationships =====
    MainWindow --> InputScreen : creates and injects service
    MainWindow --> OutputScreen : creates and injects service

    InputScreen --> FileLoaderWidget : contains
    InputScreen --> ProgramListWidget : contains
    InputScreen --> PeriodListWidget : contains
    InputScreen --> GenerateWorker : creates on generate click

    FileLoaderWidget --> FilePathValidator : uses
    ProgramListWidget --> ProgramRowWidget : creates per program
    ProgramRowWidget --> ProgramItem : displays
    PeriodListWidget --> PeriodRowWidget : creates per period
    PeriodListWidget --> PeriodFormatter : uses
    PeriodFormatter --> PeriodItem : creates
    PeriodRowWidget --> PeriodItem : displays
```

## Overview
- **MainWindow**: Root QMainWindow; owns a `QStackedWidget` with `InputScreen` at index 0 and `OutputScreen` at index 1. Wires `switch_to_output` / `switch_to_input` signals to navigate between them.
- **InputScreen**: Top-level input screen. Composes `FileLoaderWidget`, `ProgramListWidget`, and `PeriodListWidget`. Creates a `GenerateWorker` when the user clicks Generate.
- **OutputScreen**: Displays and paginates generated schedules; supports export.
- **FileLoaderWidget**: Lets the user pick two files and a load mode (replace/append). Delegates validation to `FilePathValidator` and loading to `IAppService.load_data()`. Emits `files_loaded` on success.
- **ProgramListWidget**: Scrollable, selectable list of academic programs (max 5). Calls `IAppService.select_programs()` on every toggle. Emits `programs_selected`.
- **PeriodListWidget**: Scrollable list of exam periods. Emits `period_selected` when a row is clicked. Uses `PeriodFormatter` to convert raw service dicts into display-friendly `PeriodItem` objects.
- **GenerateWorker**: `QThread` subclass. Iterates `IAppService.generate_stream()` on a **background thread**. Emits `period_ready(period_id)` per period and `finished(count)` when done. All communication back to the UI is through Qt signals (thread-safe crossing of the thread boundary).

## Threading model
| Thread | Runs |
|--------|------|
| Main (Qt event loop) | `MainWindow`, `InputScreen`, `OutputScreen`, all widgets |
| Worker (QThread) | `GenerateWorker.run()` only |

Signals (`period_ready`, `finished`, `error`) are automatically queued across the thread boundary by Qt — no manual locking is needed.
