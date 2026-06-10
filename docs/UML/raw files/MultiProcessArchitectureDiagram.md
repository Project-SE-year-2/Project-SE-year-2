# Multi-Process Architecture Diagram

Shows the two-process architecture (EP-83): how the UI process and the Engine subprocess communicate through multiprocessing queues and a shared disk directory. This is a **component/deployment view** — not a class diagram.

```mermaid
flowchart TD
    subgraph UIProcess["UI Process (main)"]
        direction TB
        MainWindow["MainWindow"]
        InputScreen["InputScreen"]
        OutputScreen["OutputScreen"]
        EngineListener["EngineListener\n(QThread)"]
        AppService["AppService\n(Singleton)"]
        ResultsReader["ResultsReader"]
        DataStore["DataStore"]

        MainWindow --> InputScreen
        MainWindow --> OutputScreen
        InputScreen -->|"start()"| EngineListener
        EngineListener -->|"generate_stream()"| AppService
        AppService --> DataStore
        AppService --> ResultsReader
        OutputScreen -->|"get_period_schedule()"| AppService
    end

    subgraph EngineSubprocess["Engine Subprocess (daemon)"]
        direction TB
        EngineWorker["_engine_worker()"]
        SchedulingEngine["SchedulingEngine"]
        PeriodResultsWriter["PeriodResultsWriter"]

        EngineWorker -->|"solve_to_disk()"| SchedulingEngine
        SchedulingEngine -->|"write_batch()"| PeriodResultsWriter
    end

    subgraph DiskStorage["Disk: data/results/"]
        Manifest["manifest.json\n(schedule counts per period)"]
        Batches["FALL_Aleph/batch_0000.pkl\nFALL_Bet/batch_0000.pkl\n..."]
    end

    AppService -->|"task_queue\n{type:solve, engine, tasks}"| EngineSubprocess
    EngineSubprocess -->|"notify_queue\n{type:period_done, period_id}"| AppService
    PeriodResultsWriter -->|"writes batches"| DiskStorage
    ResultsReader -->|"reads batches"| DiskStorage

    style UIProcess fill:#1a1a2e,stroke:#4a90d9,color:#ffffff
    style EngineSubprocess fill:#1a2e1a,stroke:#4a9d4a,color:#ffffff
    style DiskStorage fill:#2e2a1a,stroke:#d9a44a,color:#ffffff
```

## Overview

### Why two processes?
Python has a Global Interpreter Lock (GIL) which prevents true parallelism with threads. Moving the algorithm into a separate OS process gives it its own Python interpreter and its own GIL, so the UI event loop is **never blocked** by solver computation — even for periods with thousands of results.

### Communication protocol
Only **lightweight** messages cross the process boundary:

| Direction | Channel | Message |
|-----------|---------|---------|
| UI → Engine | `task_queue` | `{type: "solve", engine, tasks}` |
| Engine → UI | `notify_queue` | `{type: "period_done", period_id: str}` |
| Engine → UI | `notify_queue` | `{type: "all_done"}` |
| Engine → UI | `notify_queue` | `{type: "error", message: str}` |

`ExamSchedule` objects are **never sent through the queues** — they are written to disk by the subprocess and read back independently by `ResultsReader`.

### Threading model within the UI process
| Component | Thread |
|-----------|--------|
| `MainWindow`, `InputScreen`, `OutputScreen`, all widgets | Qt main thread (event loop) |
| `EngineListener.run()` | Background `QThread` |

`EngineListener` blocks on `notify_queue.get()` (via `AppService.generate_stream()`). Since it never runs CPU-heavy Python work, blocking on a queue is acceptable — it frees the main thread completely.

### Disk storage layout
```
data/results/
├── manifest.json          ← { "FALL_Aleph": 120, "FALL_Bet": 85, … }
├── FALL_Aleph/
│   ├── batch_0000.pkl     ← schedules[0..49]
│   ├── batch_0001.pkl     ← schedules[50..99]
│   └── …
└── FALL_Bet/
    └── batch_0000.pkl
```
`BATCH_SIZE = 50`. `ResultsReader` loads only the one batch file that contains the requested index.
