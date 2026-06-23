from src.models.constraint_settings import ConstraintSettings
from src.models.exam_schedule import ExamSchedule

from src.algorithm.constraints.i_constraint import IConstraint
from src.algorithm.constraints.all_gap_constraint import AllGapConstraint
from src.algorithm.constraints.collision_constraint import CollisionConstraint
from src.algorithm.constraints.spread_constraint import SpreadConstraint
from src.algorithm.constraints.daily_cap_constraint import DailyCapConstraint
from src.algorithm.constraints.mandatory_gap_constraint import MandatoryGapConstraint

class ConstraintChecker:
    """
    Centralized validation manager.

    Builds and owns the active constraint registry according to the
    supplied ConstraintSettings and evaluates schedules against all
    enabled constraints.
    """

    _CONSTRAINT_REGISTRY = (
        (
            "mandatory_gap_enabled",
            "mandatory_gap_k",
            MandatoryGapConstraint,
        ),
        (
            "all_gap_enabled",
            "all_gap_k",
            AllGapConstraint,
        ),
        (
            "elective_conflicts_enabled",
            "elective_conflicts_k",
            CollisionConstraint,
        ),
        (
            "spread_enabled",
            "spread_k",
            SpreadConstraint,
        ),
        (
            "daily_cap_enabled",
            "daily_cap_k",
            DailyCapConstraint,
        ),
    )

    # Build the active constraint list from the supplied settings.
    def __init__(self, settings: ConstraintSettings):
        self._constraints: list[IConstraint] = []

        for enabled_attr, k_attr, constraint_cls in self._CONSTRAINT_REGISTRY:
            if getattr(settings, enabled_attr):
                self._constraints.append(
                    constraint_cls(getattr(settings, k_attr))
                )

    # Validate a schedule against all enabled constraints.
    def is_valid(self, schedule: ExamSchedule) -> bool:
        for constraint in self._constraints:
            if not constraint.is_satisfied(schedule):
                return False

        return True