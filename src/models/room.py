from dataclasses import dataclass


@dataclass
class Room:
    """Represents a physical exam room identified by its building and room number."""

    room_id: str
    building: str
    capacity: int

    def __post_init__(self) -> None:
        # bool is a subclass of int so it passes the int check - must be excluded explicitly
        # All other non-int types (str, float, etc.) are caught by the first condition
        if not isinstance(self.capacity, int) or isinstance(self.capacity, bool):
            raise ValueError("Room capacity must be an integer.")
        if self.capacity <= 0:
            raise ValueError(f"Room capacity must be a positive integer, got {self.capacity}.")