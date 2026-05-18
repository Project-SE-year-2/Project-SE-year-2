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
    }

    %% ===== Infrastructure Layer =====
    class IFileParser~T~ {
        <<interface>>
        +parse(path: String) List~T~
    }

    class CourseFileParser {
        +parse(path: String) List~Course~
        ..creates ProgramRequirement
    }

    class ExamPeriodFileParser {
        +parse(path: String) List~ExamPeriod~
        -_parse_forbidden_dates(lines: List~String~, period_start: Date, period_end: Date) Set~Date~
    }

    class ProgramSelectionParser {
        +parse(path: String) List~String~
    }

    class ScheduleReportWriter {
        +write(schedules: List~ExamSchedule~, metadata: Map~ExamPeriod, Map~, programs: List~String~, output_path: String) void
        -_buildReport(schedules: List~ExamSchedule~, metadata: Map~ExamPeriod, Map~, programs: List~String~) List~String~
        -_printSummary(metadata: Map~ExamPeriod, Map~, schedules: List~ExamSchedule~, output_path: String) void
        -_formatSchedule(schedule: ExamSchedule) String
        -_groupByPeriod(schedules: List~ExamSchedule) Map
    }

    %% ===== Domain Layer =====
    class Course {
        -courseId: String
        -name: String
        -instructor: String
        -evaluation: Evaluation
        -requirements: List~ProgramRequirement~
        +hasExam() bool
        +belongsTo(programId: String) bool
        +getRequirementFor(programId: String) ProgramRequirement
    }

    class ProgramRequirement {
        -programId: String
        -year: int
        -semester: Semester
        -requirement: ReqType
        +isObligatory() bool
        +groupKey() Tuple
    }

    class ExamPeriod {
        -semester: Semester
        -moed: Moed
        -startDate: Date
        -endDate: Date
        -excluded: Set~Date~
        +availableDates() List~Date~
        +contains(date: Date) bool
        +isExcluded(date: Date) bool
    }

    class ExamPeriodCatalog {
        -periods: List~ExamPeriod~
        +get(semester: Semester, moed: Moed) ExamPeriod
        +all() List~ExamPeriod~
        +periodFor(course: Course, moed: Moed) ExamPeriod
    }

    class ConstraintIndex {
        -obligatoryGroups: Map
        -examCourses: List~Course~
        -selectedPrograms: List~String~
        +build(courses, programs) void
        +obligatoryGroups() Map
        +groupKeyFor(course: Course) Tuple
        +examCoursesInPrograms() List~Course~
    }

    class ExamSchedule {
        -assignments: Map~Course_Date~
        +assign(course: Course, date: Date) void
        +unassign(course: Course) void
        +sortByDate() List
        +groupBySemesterAndMoed() Map
        +copy() ExamSchedule
    }

    %% ===== Logic Layer =====
    class ConstraintValidator {
        -index: ConstraintIndex
        +canAssign(course, date, schedule) bool
        +collides(c1: Course, c2: Course) bool
        -shareObligatoryGroup(c1, c2) bool
    }

    class SchedulingEngine {
        -validator: ConstraintValidator
        -catalog: ExamPeriodCatalog
        -index: ConstraintIndex
        -solver: BacktrackingSolver
        -combiner: ScheduleCombiner
        +generateAll(scheduling_tasks: Map~ExamPeriod, Map~Course,List~String~) Tuple~List~ExamSchedule~, Map~ExamPeriod, Map~~
        -_orderCourses(courses) List~Course~
    }

    class BacktrackingSolver {
        -validator: ConstraintValidator
        -heuristic: CourseOrderingHeuristic
        -forwardChecker: ForwardChecker
        +solve(subProblem) List~ExamSchedule~
        -backtrack(remaining, partial, results) void
    }

    class CourseOrderingHeuristic {
        +orderByMostConstrained(courses, period) List~Course~
    }

    class ForwardChecker {
        +hasViableAssignment(remaining, partial, period) bool
    }

    %% ===== Enumerations =====
    class Semester {
        <<enumeration>>
        FALL
        SPRI
        SUMM
    }

    class Moed {
        <<enumeration>>
        Aleph
        Bet
        Gimel
    }

    class ReqType {
        <<enumeration>>
        Obligatory
        Elective
    }

    class Evaluation {
        <<enumeration>>
        Exam
        Project
        Attendance
    }

    %% ===== Relationships =====

    %% Application controls everything
    AppController --> CourseFileParser : uses
    AppController --> CourseFileParser : uses
    AppController --> ExamPeriodFileParser : uses
    AppController --> ProgramSelectionParser : uses
    AppController --> SchedulingEngine : uses
    AppController --> ScheduleReportWriter : uses
    AppController --> ConstraintIndex : builds

    %% Parsers implement interface
    CourseFileParser ..|> IFileParser : implements
    ExamPeriodFileParser ..|> IFileParser : implements

    %% Parsers create domain objects
    CourseFileParser ..> Course : creates
    CourseFileParser ..> Course : filters
    ExamPeriodFileParser ..> ExamPeriod : creates

    %% Domain composition
    Course "1" *-- "1..*" ProgramRequirement : owns
    ExamPeriodCatalog "1" *-- "1..*" ExamPeriod : owns
    ExamSchedule "1" o-- "*" Course : references

    %% Constraint index aggregates courses
    ConstraintIndex "1" o-- "*" Course : indexes

    %% Logic layer wiring
    ConstraintValidator --> ConstraintIndex : queries
    SchedulingEngine --> ConstraintValidator : uses
    SchedulingEngine --> ExamPeriodCatalog : reads from
    SchedulingEngine --> ConstraintIndex : iterates
    SchedulingEngine --> BacktrackingSolver : uses
    BacktrackingSolver --> CourseOrderingHeuristic : uses
    BacktrackingSolver --> ForwardChecker : uses
    BacktrackingSolver --> ConstraintValidator : uses
    BacktrackingSolver ..> ExamSchedule : produces

    %% Writer consumes results
    ScheduleReportWriter ..> ExamSchedule : reads

    %% Enum usage
    ProgramRequirement --> Semester : has
    ProgramRequirement --> ReqType : has
    ExamPeriod --> Semester : has
    ExamPeriod --> Moed : has
    Course --> Evaluation : has
```