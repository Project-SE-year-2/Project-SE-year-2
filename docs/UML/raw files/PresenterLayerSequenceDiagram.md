# Presenter Layer Sequence Diagram

The primary use-case flow through the Presenter layer in **multiprocessing mode (EP-83)**: loading data, selecting programs, streaming generation across two processes, per-period navigation, and export.

```mermaid
sequenceDiagram
    participant User
    participant MainWindow
    participant InputScreen
    participant EngineListener
    participant AppService
    participant EngineProcess
    participant EngineSubprocess
    participant PeriodResultsWriter
    participant ResultsReader
    participant ScheduleReportWriter
    participant OutputScreen

    Note over EngineListener: QThread (UI process)
    Note over EngineSubprocess: Separate OS process

    User->>InputScreen: clicks Load Data
    InputScreen->>AppService: load_data(courses_path, dates_path, mode)
    AppService->>CourseFileParser: parse(courses_path)
    AppService->>ExamPeriodFileParser: parse(dates_path)
    AppService->>ProgramsParser: parse(programs_path)
    AppService->>DataStore: set_courses / set_periods / set_program_names
    AppService->>DataStore: save()

    User->>InputScreen: selects programs
    InputScreen->>AppService: select_programs(ids)

    User->>InputScreen: clicks Generate
    InputScreen->>EngineListener: start()
    EngineListener->>AppService: generate_stream() [iterates generator]
    Note over AppService: _prepare_engine()
    Note over AppService: builds ConstraintIndex, ExamPeriodCatalog,<br/>ConstraintValidator, SchedulingEngine

    AppService->>EngineProcess: submit(engine, scheduling_tasks)
    Note over EngineProcess: sends {type:solve} via task_queue

    loop for each exam period (inside subprocess)
        EngineSubprocess->>SchedulingEngine: solve_to_disk(period, courses_dict, writer)
        SchedulingEngine->>PeriodResultsWriter: write_batch(period_id, schedules)
        PeriodResultsWriter->>PeriodResultsWriter: update_manifest(period_id, count)
        Note over PeriodResultsWriter: writes batch_0000.pkl …<br/>to data/results/<period_id>/
        EngineSubprocess-->>AppService: notify_queue: {type:period_done, period_id}
        AppService-->>EngineListener: yield (period_id, [])
        EngineListener-->>InputScreen: period_ready(period_id)
        InputScreen-->>OutputScreen: (output screen polls for new data)
    end

    EngineSubprocess-->>AppService: notify_queue: {type:all_done}
    Note over AppService: generator exhausted
    EngineListener->>AppService: get_schedule_count()
    AppService->>ResultsReader: get_count(period_id) [per period]
    ResultsReader-->>AppService: count from manifest.json
    AppService-->>EngineListener: total_count
    EngineListener-->>InputScreen: finished(total_count)
    InputScreen->>MainWindow: emit switch_to_output
    MainWindow->>OutputScreen: setCurrentIndex(1)

    User->>OutputScreen: browses schedule tab
    OutputScreen->>AppService: get_period_schedule(period_id, index)
    AppService->>ResultsReader: get_schedule_at(period_id, index)
    ResultsReader-->>AppService: ExamSchedule (from batch file)
    AppService-->>OutputScreen: formatted schedule rows

    User->>OutputScreen: navigates to next combination
    OutputScreen->>AppService: navigate_global(+1)
    AppService->>ResultsReader: get_count / get_schedule_at [per period]
    AppService-->>OutputScreen: updated period indices

    User->>OutputScreen: clicks Export
    OutputScreen->>AppService: export_current(path)
    AppService->>ResultsReader: get_schedule_at(period_id, idx) [per period]
    AppService->>ScheduleReportWriter: write(combined_schedules, metadata, programs, path)
```

## Flow Summary
1. **Load Data** — `InputScreen` calls `AppService.load_data()`. Parsers run, results saved to `DataStore`.
2. **Select Programs** — `InputScreen` calls `AppService.select_programs(ids)`.
3. **Generate (multiprocessing)** — `InputScreen` creates `EngineListener` and starts it. The listener iterates `AppService.generate_stream()`, which submits tasks to the `EngineProcess`. The daemon subprocess calls `SchedulingEngine.solve_to_disk()` for each period, writing batched pickle files. For each finished period it sends a `period_done` notification back through `notify_queue`. The listener translates each yield into a `period_ready` signal.
4. **Navigate** — `InputScreen` emits `switch_to_output`; `MainWindow` switches the stacked widget.
5. **Browse** — `OutputScreen` calls `get_period_schedule(period_id, index)` and `navigate_global(±1)` to page through results. All reads go through `ResultsReader` directly from disk — no results are held in RAM.
6. **Export** — `OutputScreen` calls `export_current(path)`. `AppService` reads one schedule per period from disk, merges them with `ScheduleCombiner`, and writes via `ScheduleReportWriter`.

## Generation Modes
| Mode | Trigger | Where schedules live |
|------|---------|---------------------|
| Multiprocessing (EP-83) | `_engine_process` is set | Engine subprocess → disk (batch files) |
| File-based single-process (EP-82) | `_results_writer` is set | AppService → disk (batch files) |
| Legacy in-memory | neither is set | RAM (`_results_by_period` + `_results`) |
