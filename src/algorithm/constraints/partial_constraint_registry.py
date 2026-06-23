from src.models.constraint_settings import ConstraintSettings
from src.algorithm.constraints.partial_constraint_checker import PartialConstraintChecker
from src.algorithm.constraints.partial_daily_cap_constraint import PartialDailyCapConstraint
from src.algorithm.constraints.partial_collision_constraint import PartialCollisionConstraint
from src.algorithm.constraints.partial_all_gap_constraint import PartialAllGapConstraint


class PartialConstraintRegistry:
    """Builds a PartialConstraintChecker from enabled ConstraintSettings."""

    @staticmethod
    def build(settings: ConstraintSettings | None) -> PartialConstraintChecker | None:
        """Create a checker containing only constraints that are safe for partial pruning."""
        if settings is None:
            return None

        constraints = []

        if settings.all_gap_enabled:
            constraints.append(PartialAllGapConstraint(settings.all_gap_k))

        if settings.daily_cap_enabled:
            constraints.append(PartialDailyCapConstraint(settings.daily_cap_k))

        if settings.elective_conflicts_enabled:
            constraints.append(
                PartialCollisionConstraint(settings.elective_conflicts_k)
            )

        if not constraints:
            return None

        return PartialConstraintChecker(constraints)