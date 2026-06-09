# Parser Subsystem Diagram

Detailed view of the parser layer responsible for reading input files and creating domain objects.

```mermaid
classDiagram
    direction TB

    %% ===== Interface =====
    class IFileParser~T~ {
        <<interface>>
        +parse(path: String) List~T~
    }

    %% ===== Parser Classes =====
    class CourseFileParser {
        +parse(path) List~Course~
    }

    class ExamPeriodFileParser {
        +parse(path) List~ExamPeriod~
        -_parse_forbidden_dates(lines, start, end) Set~Date~
        -_generate_date_range(start, end) Generator
    }

    class ProgramSelectionParser {
        +parse(path) List~String~
    }

    class ProgramsParser {
        +parse(filepath)$ dict[str, str]
    }

    %% ===== Module-Level Function =====
    class ParserModule {
        +filter_courses_for_scheduling(courses, programs) List~Course~
    }

    %% ===== Domain Objects Created =====
    class Course {
        -courseId: String
        -name: String
        -instructor: String
        -evaluation: String
        -requirements: List~ProgramRequirement~
    }

    class ProgramRequirement {
        -programId: String
        -year: int
        -semester: String
        -req_type: String
    }

    class ExamPeriod {
        -semester: String
        -moed: String
        -start_date: Date
        -end_date: Date
        -possible_dates: List~Date~
    }

    %% ===== Relationships =====
    IFileParser <|.. CourseFileParser : implements
    IFileParser <|.. ExamPeriodFileParser : implements
    IFileParser <|.. ProgramSelectionParser : implements

    CourseFileParser ..> Course : creates
    CourseFileParser ..> ProgramRequirement : creates
    ExamPeriodFileParser ..> ExamPeriod : creates

    ParserModule --> CourseFileParser : uses
    ParserModule ..> Course : filters

    Course "1" *-- "1..*" ProgramRequirement : contains
```

## Overview
- **IFileParser**: Generic interface for file-based parsers.
- **CourseFileParser**: Parses courses and program requirements from the courses data file.
- **ExamPeriodFileParser**: Parses exam periods and forbidden dates from the dates data file.
- **ProgramSelectionParser**: Parses a list of selected program IDs from a text file (used by the CLI `AppController`).
- **ProgramsParser**: Static parser that reads `data/programsName.txt` and returns a `{program_id: display_name}` mapping. Used by `AppService` to show human-readable program names in the UI.
- **ParserModule** (`filter_courses_for_scheduling`): Module-level function that filters the full course list down to only those belonging to selected programs and having an exam evaluation type.
