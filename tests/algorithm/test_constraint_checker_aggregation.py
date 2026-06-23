"""
EP-94 — Aggregation and short-circuit tests for ConstraintChecker.

The per-constraint unit tests (test_all_gap_constraint, test_collision_constraint,
test_spread_constraint, test_daily_cap_constraint) already prove that each rule
in section 2 of the requirements (2.1-2.5) evaluates correctly in isolation.

What was NOT yet covered, and is required by the EP-94 acceptance criteria
("verify that ConstraintChecker correctly aggregates individual constraint
statuses and short-circuits on failure"), is the *orchestration* behaviour:

  * AND-aggregation  — the schedule is valid only when EVERY enabled constraint
                       passes; a single failure makes the whole schedule invalid.
  * Short-circuit    — evaluation stops at the first failing constraint; the
                       remaining constraints are never asked.

These tests use lightweight spy constraints (implementing IConstraint) instead
of real date-based rules, so the orchestration logic is tested independently of
any single constraint's maths.  Spies are injected into the established
`_constraints` list — the same internal hook the existing checker tests use.
"""

from src.algorithm.constraints.constraint_checker import ConstraintChecker
from src.algorithm.constraints.i_constraint import IConstraint
from src.models.constraint_settings import ConstraintSettings
from src.models.exam_schedule import ExamSchedule


class _SpyConstraint(IConstraint):
    """Records how many times it was evaluated and returns a fixed verdict."""

    def __init__(self, verdict: bool) -> None:
        self._verdict = verdict
        self.calls = 0

    def is_satisfied(self, schedule: ExamSchedule) -> bool:
        self.calls += 1
        return self._verdict


def _empty_checker() -> ConstraintChecker:
    """A checker with no real constraints; spies are injected per test."""
    return ConstraintChecker(ConstraintSettings())


# A bare schedule is enough — spies ignore its contents.
_SCHEDULE = ExamSchedule.__new__(ExamSchedule)


# ---------------------------------------------------------------------------
# AND-aggregation: valid only when every constraint passes
# ---------------------------------------------------------------------------

def test_all_passing_constraints_yield_valid():
    checker = _empty_checker()
    checker._constraints = [_SpyConstraint(True), _SpyConstraint(True), _SpyConstraint(True)]
    assert checker.is_valid(_SCHEDULE) is True


def test_single_failing_constraint_makes_schedule_invalid():
    checker = _empty_checker()
    checker._constraints = [_SpyConstraint(True), _SpyConstraint(False), _SpyConstraint(True)]
    assert checker.is_valid(_SCHEDULE) is False


def test_first_constraint_failing_makes_schedule_invalid():
    """Aggregation must not depend on position — failure anywhere fails the whole."""
    checker = _empty_checker()
    checker._constraints = [_SpyConstraint(False), _SpyConstraint(True)]
    assert checker.is_valid(_SCHEDULE) is False


def test_last_constraint_failing_makes_schedule_invalid():
    checker = _empty_checker()
    checker._constraints = [_SpyConstraint(True), _SpyConstraint(False)]
    assert checker.is_valid(_SCHEDULE) is False


def test_all_failing_constraints_yield_invalid():
    checker = _empty_checker()
    checker._constraints = [_SpyConstraint(False), _SpyConstraint(False)]
    assert checker.is_valid(_SCHEDULE) is False


# ---------------------------------------------------------------------------
# Short-circuit: stop at the first failure
# ---------------------------------------------------------------------------

def test_short_circuits_after_first_failure():
    """Constraints after the first failing one must never be evaluated."""
    first = _SpyConstraint(True)
    failing = _SpyConstraint(False)
    never = _SpyConstraint(True)

    checker = _empty_checker()
    checker._constraints = [first, failing, never]

    assert checker.is_valid(_SCHEDULE) is False
    assert first.calls == 1       # evaluated
    assert failing.calls == 1     # evaluated, triggered the stop
    assert never.calls == 0       # short-circuited — never asked


def test_all_constraints_evaluated_when_all_pass():
    """When nothing fails, every constraint must be evaluated exactly once."""
    spies = [_SpyConstraint(True) for _ in range(4)]

    checker = _empty_checker()
    checker._constraints = spies

    assert checker.is_valid(_SCHEDULE) is True
    assert all(spy.calls == 1 for spy in spies)


def test_short_circuit_stops_on_immediate_first_failure():
    """A failure in the first constraint must skip all the rest."""
    failing = _SpyConstraint(False)
    rest = [_SpyConstraint(True) for _ in range(3)]

    checker = _empty_checker()
    checker._constraints = [failing] + rest

    assert checker.is_valid(_SCHEDULE) is False
    assert failing.calls == 1
    assert all(spy.calls == 0 for spy in rest)


# ---------------------------------------------------------------------------
# Empty registry edge case (no constraints enabled → always valid)
# ---------------------------------------------------------------------------

def test_empty_registry_is_always_valid():
    checker = _empty_checker()
    checker._constraints = []
    assert checker.is_valid(_SCHEDULE) is True
