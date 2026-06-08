from src.views.input_screen.generate_button_state import GenerateButtonState


# Tests that the Generate button is hidden when no programs and no period are selected.
def test_generate_button_hidden_initially():
    state = GenerateButtonState()

    assert state.should_show_button() is False
    assert state.should_enable_button() is False


# Tests that selecting only programs is not enough to show the Generate button.
def test_generate_button_hidden_when_only_programs_selected():
    state = GenerateButtonState()

    state.set_program_selection(True)

    assert state.should_show_button() is False
    assert state.should_enable_button() is False


# Tests that selecting programs and viewing a period makes the Generate button visible and enabled.
def test_generate_button_visible_after_program_and_period_selection():
    state = GenerateButtonState()

    state.set_program_selection(True)
    state.set_period_viewed(True)

    assert state.should_show_button() is True
    assert state.should_enable_button() is True


# Tests that clearing program selection also clears the viewed-period requirement.
def test_clearing_programs_hides_generate_button():
    state = GenerateButtonState()
    state.set_program_selection(True)
    state.set_period_viewed(True)

    state.set_program_selection(False)

    assert state.has_viewed_period is False
    assert state.should_show_button() is False


# Tests that starting generation keeps the button visible but disables clicking.
def test_generation_disables_button_while_running():
    state = GenerateButtonState()
    state.set_program_selection(True)
    state.set_period_viewed(True)

    state.start_generation()

    assert state.should_show_button() is True
    assert state.should_enable_button() is False


# Tests that finishing generation enables the button again if the selection is still valid.
def test_generation_finish_reenables_button():
    state = GenerateButtonState()
    state.set_program_selection(True)
    state.set_period_viewed(True)
    state.start_generation()

    state.finish_generation()

    assert state.should_show_button() is True
    assert state.should_enable_button() is True


# Tests that loading files resets all Generate button state.
def test_file_load_resets_generate_button_state():
    state = GenerateButtonState()
    state.set_program_selection(True)
    state.set_period_viewed(True)
    state.start_generation()

    state.reset_after_file_load()

    assert state.has_selected_programs is False
    assert state.has_viewed_period is False
    assert state.is_generating is False
    assert state.should_show_button() is False
