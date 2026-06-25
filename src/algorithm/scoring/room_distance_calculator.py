from src.algorithm.scoring.i_metric_calculator import IMetricCalculator
from src.models.exam_schedule import ExamSchedule


class RoomDistanceCalculator(IMetricCalculator):
    """Computes the average number of distinct buildings per exam across all room-based placements.

    Returns 0.0 in date-only mode (no room-based placements).
    Lower is better - 1.0 means every exam fits within a single building.
    """

    def field_name(self) -> str:
        return "avg_room_distance"

    def compute(self, schedule: ExamSchedule) -> float:
        distances = []
        for _, _, placement in schedule.iter_placements():
            # Skip date-only placements - calculator is called in both modes
            if not placement.is_room_based:
                continue
            # Count how many distinct buildings this exam's rooms span
            distinct_buildings = len({room.building for room in placement.rooms})
            distances.append(distinct_buildings)

        # No room-based placements means date-only mode - return default
        return round(sum(distances) / len(distances), 2) if distances else 0.0
