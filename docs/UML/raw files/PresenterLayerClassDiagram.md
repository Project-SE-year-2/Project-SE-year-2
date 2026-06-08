# Presenter Layer Class Diagram

Detailed view of the MVP Presenter layer: the `IAppService` contract, the singleton `AppService`, the `DataStore` model, the `GenerateWorker` background thread, and their relationships to the View screens and external subsystems.

```mermaid
classDiagram
    direction TB

    %% ===== View Layer =====
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

    class GenerateWorker {
        -_service: IAppService
        +period_ready: pyqtSignal(str)
        +finished: pyqtSignal(int)
        +error: pyqtSignal(str)
        +__init__(service)
        +run()
    }

    %% ===== Presenter Layer =====
    class IAppService {
        <<interface>>
        +load_data(courses_path, dates_path, mode)
        +get_available_programs()
        +select_programs(ids)
        +get_courses(program_id)
        +get_periods()
        +toggle_day(period_id, day)
        +shift_period(period_id, start, end)
        +generate()
        +generate_stream()
        +get_period_ids()
        +get_period_schedules(period_id)
        +get_schedule_count()
        +get_schedule(index)
        +export_schedule(index, path)
    }

    class AppService {
        -_datastore: DataStore
        -_selected_programs: list[str]
        -_results: list[ExamSchedule]
        -_results_by_period: dict[str, list[ExamSchedule]]
        -_last_metadata: dict
        +getInstance()$
        +load_data(courses_path, dates_path, mode)
        +get_available_programs()
        +select_programs(ids)
        +get_courses(program_id)
        +get_periods()
        +toggle_day(period_id, day)
        +shift_period(period_id, start, end)
        +generate()
        +generate_stream()
        +get_period_ids()
        +get_period_schedules(period_id)
        +get_schedule_count()
        +get_schedule(index)
        +export_schedule(index, path)
        -_prepare_engine()
        -_validate_paths(paths)
        -_get_period_or_raise(period_id)
    }

    %% ===== Model Layer =====
    class DataStore {
        -_path: Path
        -_courses: list[Course]
        -_periods: list[ExamPeriod]
        +load()
        +save()
        +clear()
        +is_empty()
        +set_courses(courses)
        +set_periods(periods)
        +merge_courses(new_courses)
        +merge_periods(new_periods)
        +get_all_courses()
        +get_courses_for_program(program_id)
        +get_programs()
        +get_periods()
        +get_period_by_id(period_id)
    }

    class ExamPeriod {
        -semester: Semester
        -moed: Moed
        -start_date: date
        -end_date: date
        -possible_dates: list[date]
        -forbidden_days: list[date]
        +toggle_day(day)
        +shift_dates(start, end)
    }

    %% ===== External Subsystems (abbreviated) =====
    class ExamPeriodFileParser {
        +parse(filepath) list[ExamPeriod]
    }

    class CourseFileParser {
        +parse(filepath) list[Course]
    }

    class SchedulingEngine {
        +generateAll(scheduling_tasks) Tuple
        +iterPeriodResults(scheduling_tasks) Generator
    }

    class ScheduleCombiner {
        +combineSubResults(list_of_lists) list[ExamSchedule]
    }

    class ScheduleReportWriter {
        +write(schedules, metadata, programs, output_path)
    }

    %% ===== Relationships =====
    MainWindow --> InputScreen : injects
    MainWindow --> OutputScreen : injects
    InputScreen --> GenerateWorker : creates
    InputScreen --> IAppService : uses
    OutputScreen --> IAppService : uses
    GenerateWorker --> IAppService : calls generate_stream()
    AppService --|> IAppService : implements
    AppService --> DataStore : owns
    AppService --> ExamPeriodFileParser : uses
    AppService --> CourseFileParser : uses
    AppService --> SchedulingEngine : uses
    AppService --> ScheduleCombiner : uses
    AppService --> ScheduleReportWriter : uses
    DataStore --> ExamPeriod : stores
    DataStore --> Course : stores
    ExamPeriodFileParser --> ExamPeriod : creates
    SchedulingEngine --> ExamPeriod : reads
    SchedulingEngine --> Course : reads
```

## Overview
- **MainWindow**: Root PyQt5 scaffold; owns a `QStackedWidget` and wires navigation signals between screens
- **InputScreen**: View for file loading, program selection, period editing, and generation trigger
- **OutputScreen**: View for browsing and exporting generated schedules
- **GenerateWorker**: `QThread` subclass that drives `generate_stream()` off the main thread, emitting `period_ready` and `finished` signals
- **IAppService**: Abstract interface — the only contract Views may use; no direct imports of models, parsers, or algorithm classes allowed in the View layer
- **AppService**: Singleton Presenter implementing `IAppService`; owns `DataStore`, orchestrates parsers, engine, combiner, and writer
- **DataStore**: Persists parsed `Course` and `ExamPeriod` objects to disk via pickle so unchanged files are not re-parsed on every startup
