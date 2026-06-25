from src.algorithm.scoring.i_metric_calculator import IMetricCalculator
from src.models.exam_schedule import ExamSchedule


class RoomDistanceCalculator(IMetricCalculator):
    """Computes the average building spread per exam across all room-based placements.

    'Building spread' is the number of distinct buildings used by a single exam's assigned rooms.
    This serves as a proxy for physical distance: rooms in the same building score 1.0 (best),
    rooms spread across more buildings score higher.

    Note: Room has no coordinate data, so true geographical distance cannot be computed.
    This metric uses the building field - the most reliable proximity indicator available.

    Returns 0.0 in date-only mode (no room-based placements). Lower is better.
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
