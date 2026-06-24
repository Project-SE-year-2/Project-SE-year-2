from dataclasses import dataclass


@dataclass
class Room:
    """Represents a physical exam room identified by its building and room number."""

    room_id: str
    building: str
    capacity: int

    def __post_init__(self) -> None:
        # Room capacity must be a positive integer
        if self.capacity <= 0:
            raise ValueError(f"Room capacity must be a positive integer, got {self.capacity}.")