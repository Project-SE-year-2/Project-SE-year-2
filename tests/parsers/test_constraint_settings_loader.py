import sys
import pytest

from src.parsers.constraint_settings_loader import ConstraintSettingsLoader


def test_from_file_loads_enabled_flags_and_k_values(tmp_path):
    """Verify that from_file parses enabled flags and K values from the advanced section."""
    config = tmp_path / "constraints.txt"
    config.write_text(
        """
# ADVANCED_CONSTRAINTS
all_gap_enabled=true
all_gap_k=5
daily_cap_enabled=true
daily_cap_k=3
""",
        encoding="utf-8",
    )

    settings = ConstraintSettingsLoader.from_file(str(config))

    assert settings.all_gap_enabled is True
    assert settings.all_gap_k == 5
    assert settings.daily_cap_enabled is True
    assert settings.daily_cap_k == 3


def test_from_file_ignores_content_before_marker(tmp_path):
    """Verify that from_file ignores unrelated lines before the advanced section marker."""
    config = tmp_path / "constraints.txt"
    config.write_text(
        """
all_gap_enabled=true
all_gap_k=99

# ADVANCED_CONSTRAINTS
all_gap_enabled=false
all_gap_k=4
""",
        encoding="utf-8",
    )

    settings = ConstraintSettingsLoader.from_file(str(config))

    assert settings.all_gap_enabled is False
    assert settings.all_gap_k == 4


def test_from_file_ignores_unknown_keys(tmp_path):
    """Verify that from_file ignores unsupported keys instead of passing them forward."""
    config = tmp_path / "constraints.txt"
    config.write_text(
        """
# ADVANCED_CONSTRAINTS
unknown_setting=true
spread_enabled=true
spread_k=12
""",
        encoding="utf-8",
    )

    settings = ConstraintSettingsLoader.from_file(str(config))

    assert settings.spread_enabled is True
    assert settings.spread_k == 12


def test_from_file_without_section_returns_defaults(tmp_path):
    """Verify that a file without an advanced section returns default settings."""
    config = tmp_path / "constraints.txt"
    config.write_text("some_other_setting=true", encoding="utf-8")

    settings = ConstraintSettingsLoader.from_file(str(config))

    assert settings.all_gap_enabled is False
    assert settings.daily_cap_enabled is False


def test_from_cli_args_loads_flags_and_k_values():
    """Verify that from_cli_args maps CLI tokens into ConstraintSettings."""
    settings = ConstraintSettingsLoader.from_cli_args([
        "--all-gap-enabled",
        "--all-gap-k", "6",
        "--elective-conflicts-enabled",
        "--elective-conflicts-k", "0",
    ])

    assert settings.all_gap_enabled is True
    assert settings.all_gap_k == 6
    assert settings.elective_conflicts_enabled is True
    assert settings.elective_conflicts_k == 0


def test_from_cli_args_missing_values_use_defaults():
    """Verify that omitted CLI arguments do not override ConstraintSettings defaults."""
    settings = ConstraintSettingsLoader.from_cli_args([])

    assert settings.all_gap_enabled is False
    assert settings.spread_enabled is False


def test_from_file_parses_false_boolean_values(tmp_path):
    """Verify that explicit false values are parsed as False."""
    config = tmp_path / "constraints.txt"
    config.write_text(
        """
# ADVANCED_CONSTRAINTS
daily_cap_enabled=false
daily_cap_k=4
""",
        encoding="utf-8",
    )

    settings = ConstraintSettingsLoader.from_file(str(config))

    assert settings.daily_cap_enabled is False
    assert settings.daily_cap_k == 4

def test_from_file_parses_all_supported_constraint_fields(tmp_path):
    """Verify that every supported constraint field can be loaded from file."""
    config = tmp_path / "constraints.txt"
    config.write_text(
        """
# ADVANCED_CONSTRAINTS
mandatory_gap_enabled=true
mandatory_gap_k=2
all_gap_enabled=true
all_gap_k=3
elective_conflicts_enabled=true
elective_conflicts_k=0
spread_enabled=true
spread_k=10
daily_cap_enabled=true
daily_cap_k=4
""",
        encoding="utf-8",
    )

    settings = ConstraintSettingsLoader.from_file(str(config))

    assert settings.mandatory_gap_enabled is True
    assert settings.mandatory_gap_k == 2
    assert settings.all_gap_enabled is True
    assert settings.all_gap_k == 3
    assert settings.elective_conflicts_enabled is True
    assert settings.elective_conflicts_k == 0
    assert settings.spread_enabled is True
    assert settings.spread_k == 10
    assert settings.daily_cap_enabled is True
    assert settings.daily_cap_k == 4

def test_from_cli_args_parses_mandatory_gap_and_daily_cap():
    """Verify that CLI parsing supports multiple constraint families."""
    settings = ConstraintSettingsLoader.from_cli_args([
        "--mandatory-gap-enabled",
        "--mandatory-gap-k", "2",
        "--daily-cap-enabled",
        "--daily-cap-k", "5",
    ])

    assert settings.mandatory_gap_enabled is True
    assert settings.mandatory_gap_k == 2
    assert settings.daily_cap_enabled is True
    assert settings.daily_cap_k == 5

def test_from_file_nonexistent_path_raises_file_not_found():
    """Verify that from_file raises FileNotFoundError when the config path does not exist."""
    with pytest.raises(FileNotFoundError):
        ConstraintSettingsLoader.from_file("missing_constraints_file.txt")


def test_from_file_invalid_k_value_raises_value_error(tmp_path):
    """Verify that from_file rejects non-numeric K values."""
    config = tmp_path / "constraints.txt"
    config.write_text(
        """
# ADVANCED_CONSTRAINTS
daily_cap_enabled=true
daily_cap_k=abc
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        ConstraintSettingsLoader.from_file(str(config))
