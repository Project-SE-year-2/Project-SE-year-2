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

    class ProgramParserModule {
        <<module>>
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
    CourseFileParser ..|> IFileParser : implements
    ExamPeriodFileParser ..|> IFileParser : implements
    ProgramSelectionParser ..|> IFileParser : implements

    CourseFileParser ..> Course : creates
    CourseFileParser ..> ProgramRequirement : creates
    ExamPeriodFileParser ..> ExamPeriod : creates

    ProgramParserModule --> ProgramSelectionParser : contains

    ParserModule --> CourseFileParser : uses
    ParserModule ..> Course : filters

    Course "1" *-- "1..*" ProgramRequirement : contains
```

## Overview
- **IFileParser**: Generic interface for all file parsers
- **CourseFileParser**: Parses courses and program requirements
- **ExamPeriodFileParser**: Parses exam periods and forbidden dates
- **ProgramSelectionParser**: Parses selected program IDs
- **ProgramParserModule**: Represents `src/parsers/program_parser.py`, which contains `ProgramSelectionParser`
- **ParserModule**: Module-level function `filter_courses_for_scheduling` that filters courses by evaluation type and program membership
