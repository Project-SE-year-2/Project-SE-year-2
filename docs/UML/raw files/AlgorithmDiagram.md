# Algorithm Subsystem Diagram

Detailed view of the scheduling algorithm layer: backtracking solver, constraint validation, heuristics, and schedule combination.

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
    }

    %% ===== Constraint & Index Management =====
    class ConstraintIndex {
        -obligatoryGroups: Map~tuple, List~Course~
        -examCourses: List~Course~
        -selectedPrograms: List~String~
        +build(courses, programs) void
        +obligatoryGroups() Map
        +groupKeyFor(course) Tuple
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

    %% ===== Backtracking Solver =====
    class BacktrackingSolver {
        -validator: ICollisionValidator
        -heuristic: CourseOrderingHeuristic
        -forward_checker: ForwardChecker
        +solve(courses, period, validator) List~ExamSchedule~
        -_backtrack(remaining, partial, period, validator, results) void
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

    %% ===== Result Objects =====
    class ExamSchedule {
        -period: ExamPeriod
        -assignments: Map~tuple, Date~
        +assign(course, date) void
        +unassign(course) void
        +sortByDate() List
        +merge(other) ExamSchedule
    }

    class ExamPeriod {
        -semester: String
        -moed: String
    }

    %% ===== Relationships =====
    SchedulingEngine --> ConstraintValidator : uses
    SchedulingEngine --> ExamPeriodCatalog : reads
    SchedulingEngine --> ConstraintIndex : uses
    SchedulingEngine --> BacktrackingSolver : runs
    SchedulingEngine --> ScheduleCombiner : combines
    SchedulingEngine ..> ExamSchedule : produces

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
- **SchedulingEngine**: Orchestrates scheduling per period
- **ConstraintIndex**: Builds conflict groups for fast lookup
- **ConstraintValidator**: Validates candidate assignments
- **BasicVersionValidator**: Checks assignment conflicts
- **BacktrackingSolver**: Enumerates valid schedules for one period
- **CourseOrderingHeuristic**: Orders courses by constraint level
- **ForwardChecker**: Prunes impossible branches early
- **ScheduleCombiner**: Combines per-period results
