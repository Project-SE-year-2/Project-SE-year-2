# AppController & Interaction Diagram

Shows the main application entry point and how it orchestrates the three subsystems (Parsers, Algorithm, Report Writer).

```mermaid
classDiagram
    direction TB

    %% ===== Application Layer =====
    class AppController {
        -courseParser: CourseFileParser
        -periodParser: ExamPeriodFileParser
        -programParser: ProgramSelectionParser
        -engine: SchedulingEngine
        -writer: ScheduleReportWriter
        +run(coursesPath, periodsPath, programsPath) void
        -_validate_paths(paths) void
    }

    %% ===== System Boundaries =====
    class Parsers {
        <<boundary>>
        CourseFileParser
        ExamPeriodFileParser
        ProgramSelectionParser
    }

    class Algorithm {
        <<boundary>>
        SchedulingEngine
    }

    class Output {
        <<boundary>>
        ScheduleReportWriter
    }

    class ScheduleReportWriter {
        +write(schedules, metadata, programs, output_path) void
        -_buildReport(schedules, metadata, programs) List~String~
        -_printSummary(metadata, schedules, output_path) void
    }

    %% ===== Relationships =====
    AppController --> Parsers : uses
    AppController --> Algorithm : uses
    AppController --> Output : uses

    Output --> ScheduleReportWriter : contains
```

## Overview
- **AppController**: Main orchestrator that coordinates parsing, scheduling, and reporting
- **Parsers**: Boundary to the parser subsystem (see `CD_02_Parsers`)
- **Algorithm**: Boundary to the algorithm subsystem (see `CD_03_Algorithm`)
- **Output**: Boundary to the report writer/output handling
