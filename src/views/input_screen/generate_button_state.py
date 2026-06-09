from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GenerateButtonState:
    """
    Holds the state rules for the Generate Schedule button.

    This class keeps the button logic outside InputScreen so the UI remains
    focused on wiring widgets, while this class owns the visibility/enabled rules.
    """

    has_selected_programs: bool = False
    has_viewed_period: bool = False
    is_generating: bool = False

    # Resets all selection and generation state after new files are loaded.
    def reset_after_file_load(self) -> None:
        self.has_selected_programs = False
        self.has_viewed_period = False
        self.is_generating = False

    # Updates whether at least one program is currently selected.
    def set_program_selection(self, has_selection: bool) -> None:
        self.has_selected_programs = has_selection

        if not has_selection:
            self.has_viewed_period = False

    # Records that the user selected/viewed an exam period.
    def set_period_viewed(self, has_period: bool) -> None:
        self.has_viewed_period = has_period

    # Marks generation as running so the button can be disabled.
    def start_generation(self) -> None:
        self.is_generating = True

    # Marks generation as finished or failed so the button can be re-enabled.
    def finish_generation(self) -> None:
        self.is_generating = False

    # Returns True only when the Generate button should be visible.
    def should_show_button(self) -> bool:
        return self.has_selected_programs

    # Returns True only when the Generate button should be clickable.
    def should_enable_button(self) -> bool:
        return self.should_show_button() and not self.is_generating
