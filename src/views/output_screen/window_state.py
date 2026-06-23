from dataclasses import dataclass, field


@dataclass
class WindowState:
    """Manage navigation state for one schedule-result window."""

    history_stack: list[int] = field(default_factory=list)
    current_pointer: int = 0
    lookahead_buffer: list[int] = field(default_factory=list)

    def current(self) -> int:
        """Return the currently selected schedule index."""
        return self.current_pointer

    def move_to(self, index: int) -> None:
        """Move to a specific index and store the previous index in history."""
        if index != self.current_pointer:
            self.history_stack.append(self.current_pointer)
            self.current_pointer = index

    def back(self) -> int:
        """Move back to the previous index if history exists."""
        if self.history_stack:
            self.current_pointer = self.history_stack.pop()
        return self.current_pointer

    def set_lookahead(self, indices: list[int]) -> None:
        """Replace the lookahead buffer with upcoming schedule indices."""
        self.lookahead_buffer = list(indices)

    def clear(self) -> None:
        """Reset all navigation state."""
        self.history_stack.clear()
        self.current_pointer = 0
        self.lookahead_buffer.clear()