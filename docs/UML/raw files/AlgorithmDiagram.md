# Algorithm Subsystem Diagram

Detailed view of the scheduling algorithm layer: backtracking solver, constraint validation, heuristics, schedule combination, and disk-based result storage.

```mermaid
classDiagram
    direction TB

    %% ===== Main Orchestrator =====
    class SchedulingEngine {
        -validator: ConstraintValidator
        -catalog: ExamPeriodCatalog
        -index: ConstraintIndex
        -solver: BacktrackingSolver
        -combiner: ScheduleCombiner
        +generateAll(scheduling_tasks) Tuple~List, Map~
        +iterPeriodResults(scheduling_tasks) Generator
        +solve_to_disk(period, courses_dict, writer) int
    }

    %% ===== Constraint & Index Management =====
    class ConstraintIndex {
        -obligatoryGroups: Map~tuple, List~Course~~
        -examCourses: List~Course~
        -selectedPrograms: List~String~
        +build(courses, programs) void
        +obligatoryGroups() Map
        +groupKeyFor(course) Tuple
        +examCoursesInPrograms() List~Course~
    }

    class ConstraintValidator {
        -index: ConstraintIndex
        -collision_validator: ICollisionValidator
        +canAssign(course, date, schedule) bool
        +collides(c1, c2) bool
    }

    class ICollisionValidator {
        <<interface>>
        +isValid(c1, d1, c2, d2) bool
    }

    class BasicVersionValidator {
        -index: ConstraintIndex
        +isValid(c1, d1, c2, d2) bool
    }

    %% ===== Period Management =====
    class ExamPeriodCatalog {
        -periods: List~ExamPeriod~
        +get(semester, moed) ExamPeriod
        +all() List~ExamPeriod~
        +periodFor(course, moed) ExamPeriod
    }

    %% ===== Backtracking Solver =====
    class BacktrackingSolver {
        -validator: ICollisionValidator
        -heuristic: CourseOrderingHeuristic
        -forward_checker: ForwardChecker
        +solve(courses, period, validator) List~ExamSchedule~
        +solve_stream(courses, period, validator) Generator
        -_backtrack(remaining, partial, period, validator, results) void
        -_backtrack_stream(remaining, partial, period, validator) Generator
    }

    %% ===== Optimization & Heuristics =====
    class CourseOrderingHeuristic {
        -index: ConstraintIndex
        +orderByMostConstrained(courses, period) List~Course~
    }

    class ForwardChecker {
        -validator: ConstraintValidator
        +hasViableAssignment(remaining, partial, period) bool
    }

    %% ===== Schedule Combination =====
    class ScheduleCombiner {
        +combineSubResults(sub_results) List~ExamSchedule~
    }

    %% ===== Disk I/O =====
    class PeriodResultsWriter {
        -_root: Path
        +BATCH_SIZE: int
        +write_batch(period_id, schedules)
        +update_manifest(period_id, count)
    }

    %% ===== Result Objects =====
    class ExamSchedule {
        -period: ExamPeriod
        -assignments: Map~tuple, Date~
        +assign(course, date) void
        +unassign(course) void
        +copy() ExamSchedule
        +merge(other) ExamSchedule
        +sortByDate() List
        +groupBySemesterAndMoed() dict
        +sort_key: str
    }

    class PeriodGenerationResult {
        <<dataclass>>
        +period: ExamPeriod
        +schedules: list
        +metadata: dict
    }

    class ExamPeriod {
        -semester: Semester
        -moed: Moed
        -start_date: date
        -end_date: date
        +period_id: str
        +getAvailableDates() list
        +toggle_day(day)
        +shift_dates(start, end)
    }

    %% ===== Relationships =====
    SchedulingEngine --> ConstraintValidator : uses
    SchedulingEngine --> ExamPeriodCatalog : reads
    SchedulingEngine --> ConstraintIndex : uses
    SchedulingEngine --> BacktrackingSolver : runs
    SchedulingEngine --> ScheduleCombiner : combines
    SchedulingEngine --> PeriodResultsWriter : writes to disk
    SchedulingEngine ..> ExamSchedule : produces
    SchedulingEngine ..> PeriodGenerationResult : yields

    ConstraintValidator --> ConstraintIndex : queries
    ConstraintValidator --> ICollisionValidator : delegates
    BasicVersionValidator ..|> ICollisionValidator : implements

    BacktrackingSolver --> CourseOrderingHeuristic : orders
    BacktrackingSolver --> ForwardChecker : prunes
    BacktrackingSolver --> ConstraintValidator : validates
    BacktrackingSolver ..> ExamSchedule : generates

    CourseOrderingHeuristic --> ConstraintIndex : inspects
    ForwardChecker --> ConstraintValidator : checks
```

## Overview
- **SchedulingEngine**: Main orchestrator. Three entry points: `generateAll()` (blocking, in-memory), `iterPeriodResults()` (streaming generator, in-memory), `solve_to_disk()` (streaming, writes directly to disk for the multi-process architecture).
- **ConstraintIndex**: Pre-computes obligatory-group conflict sets and lists exam-evaluation courses for fast lookup during backtracking.
- **ConstraintValidator**: Validates whether assigning a course to a date is legal given the current partial schedule.
- **BasicVersionValidator**: Implements `ICollisionValidator`; checks that two courses with shared obligatory-program students are not scheduled on the same day.
- **BacktrackingSolver**: Enumerates all valid schedules for one period via recursive backtracking. `solve_stream()` yields solutions one at a time (used by `solve_to_disk`).
- **CourseOrderingHeuristic**: Orders courses by "most constrained first" to reduce the search tree.
- **ForwardChecker**: Prunes branches where a remaining course has no viable date left.
- **ScheduleCombiner**: Takes per-period result lists and computes the Cartesian product to produce combined cross-period schedules.
- **PeriodResultsWriter**: Writes solved `ExamSchedule` objects to batched pickle files (`BATCH_SIZE=50`) and maintains a `manifest.json` index. Used by `SchedulingEngine.solve_to_disk()` in the multi-process architecture.
