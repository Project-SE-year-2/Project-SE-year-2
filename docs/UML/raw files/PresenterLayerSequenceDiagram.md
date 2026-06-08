# Presenter Layer Sequence Diagram

The primary use-case flows through the Presenter layer: loading data, selecting programs, streaming generation, and exporting a schedule.

```mermaid
sequenceDiagram
    participant User
    participant MainWindow
    participant InputScreen
    participant GenerateWorker
    participant AppService
    participant DataStore
    participant CourseFileParser
    participant ExamPeriodFileParser
    participant SchedulingEngine
    participant ScheduleCombiner
    participant ScheduleReportWriter
    participant OutputScreen

    User->>InputScreen: clicks Load Data
    InputScreen->>AppService: load_data(courses_path, dates_path, mode)
    AppService->>CourseFileParser: parse(courses_path)
    AppService->>ExamPeriodFileParser: parse(dates_path)
    AppService->>DataStore: set_courses / merge_courses
    AppService->>DataStore: set_periods / merge_periods
    AppService->>DataStore: save()

    User->>InputScreen: selects programs
    InputScreen->>AppService: select_programs(ids)

    User->>InputScreen: clicks Generate
    InputScreen->>GenerateWorker: start()
    GenerateWorker->>AppService: generate_stream()
    Note over AppService: _prepare_engine() — builds ConstraintIndex,<br/>ExamPeriodCatalog, ConstraintValidator, SchedulingEngine

    loop for each exam period
        AppService->>SchedulingEngine: iterPeriodResults(tasks)
        SchedulingEngine-->>AppService: period_result (period + schedules)
        AppService-->>GenerateWorker: yield (period_id, schedules)
        GenerateWorker-->>InputScreen: period_ready(period_id)
    end

    Note over AppService: all periods done — runs Combiner
    AppService->>ScheduleCombiner: combineSubResults(all_period_results)
    ScheduleCombiner-->>AppService: combined and sorted schedules
    Note over AppService: _results populated; generator exhausted

    GenerateWorker->>AppService: get_schedule_count()
    AppService-->>GenerateWorker: total_count
    GenerateWorker-->>InputScreen: finished(total_count)
    InputScreen->>MainWindow: emit switch_to_output
    MainWindow->>OutputScreen: setCurrentIndex(1)

    User->>OutputScreen: requests schedule page
    OutputScreen->>AppService: get_schedule(index)
    AppService-->>OutputScreen: schedule dict

    User->>OutputScreen: clicks Export
    OutputScreen->>AppService: export_schedule(index, path)
    AppService->>ScheduleReportWriter: write(schedules, metadata, programs, path)
```

## Flow Summary
1. **Load Data** — `InputScreen` calls `AppService.load_data()`. The service delegates to the file parsers, then writes results to `DataStore`.
2. **Select Programs** — `InputScreen` calls `AppService.select_programs(ids)` to record the user's selection.
3. **Generate (streaming)** — `InputScreen` creates a `GenerateWorker` and starts it on a background thread. The worker iterates the `AppService.generate_stream()` generator: for each period that finishes, `AppService` yields `(period_id, schedules)` and the worker emits `period_ready`. When all periods are done, `AppService` runs `ScheduleCombiner` internally, then the generator is exhausted, and the worker emits `finished(total_count)`.
4. **Navigate** — `InputScreen` emits `switch_to_output`; `MainWindow` switches the stacked widget to `OutputScreen`.
5. **Browse & Export** — `OutputScreen` calls `get_schedule(index)` to paginate results and `export_schedule(index, path)` to write a report file via `ScheduleReportWriter`.
