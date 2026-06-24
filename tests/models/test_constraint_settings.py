import pytest

from src.models.constraint_settings import ConstraintSettings


# Test that a new settings object starts with disabled constraints and K values of zero.
def test_default_values_are_disabled_and_zero():
    settings = ConstraintSettings()

    assert settings.mandatory_gap_enabled is False
    assert settings.mandatory_gap_k == 0
    assert settings.all_gap_enabled is False
    assert settings.all_gap_k == 0
    assert settings.elective_conflicts_enabled is False
    assert settings.elective_conflicts_k == 0
    assert settings.spread_enabled is False
    assert settings.spread_k == 0
    assert settings.daily_cap_enabled is False
    assert settings.daily_cap_k == 0
    assert settings.room_scheduling_enabled is False


# Test that to_dict returns all settings fields as a plain dictionary.
def test_to_dict_returns_expected_values():
    settings = ConstraintSettings(
        mandatory_gap_enabled=True,
        mandatory_gap_k=3,
        all_gap_enabled=True,
        all_gap_k=2,
        elective_conflicts_enabled=True,
        elective_conflicts_k=0,
        spread_enabled=True,
        spread_k=4,
        daily_cap_enabled=True,
        daily_cap_k=1,
    )

    assert settings.to_dict() == {
        "mandatory_gap_enabled": True,
        "mandatory_gap_k": 3,
        "all_gap_enabled": True,
        "all_gap_k": 2,
        "elective_conflicts_enabled": True,
        "elective_conflicts_k": 0,
        "spread_enabled": True,
        "spread_k": 4,
        "daily_cap_enabled": True,
        "daily_cap_k": 1,
        "room_scheduling_enabled": False,
    }


# Test that from_dict creates a valid ConstraintSettings object from dictionary data.
def test_from_dict_creates_settings_object():
    data = {
        "mandatory_gap_enabled": True,
        "mandatory_gap_k": 3,
        "daily_cap_enabled": True,
        "daily_cap_k": 2,
    }

    settings = ConstraintSettings.from_dict(data)

    assert isinstance(settings, ConstraintSettings)
    assert settings.mandatory_gap_enabled is True
    assert settings.mandatory_gap_k == 3
    assert settings.daily_cap_enabled is True
    assert settings.daily_cap_k == 2


# Test that K values are converted from strings into integers.
def test_from_dict_converts_k_values_to_int():
    data = {
        "mandatory_gap_k": "3",
        "all_gap_k": "2",
        "elective_conflicts_k": "1",
        "spread_k": "4",
        "daily_cap_k": "5",
    }

    settings = ConstraintSettings.from_dict(data)

    assert settings.mandatory_gap_k == 3
    assert settings.all_gap_k == 2
    assert settings.elective_conflicts_k == 1
    assert settings.spread_k == 4
    assert settings.daily_cap_k == 5


# Test that enabled values are converted from common string values into booleans.
def test_from_dict_converts_enabled_values_to_bool():
    data = {
        "mandatory_gap_enabled": "true",
        "mandatory_gap_k": "3",
        "all_gap_enabled": "1",
        "all_gap_k": "2",
        "elective_conflicts_enabled": "yes",
        "elective_conflicts_k": "0",
        "spread_enabled": "on",
        "spread_k": "4",
        "daily_cap_enabled": "false",
        "daily_cap_k": "0",
    }

    settings = ConstraintSettings.from_dict(data)

    assert settings.mandatory_gap_enabled is True
    assert settings.all_gap_enabled is True
    assert settings.elective_conflicts_enabled is True
    assert settings.spread_enabled is True
    assert settings.daily_cap_enabled is False


# Test that runtime changes are reflected when converting the object back to dictionary.
def test_modified_values_are_reflected_in_to_dict():
    settings = ConstraintSettings()

    settings.mandatory_gap_enabled = True
    settings.mandatory_gap_k = 3

    result = settings.to_dict()

    assert result["mandatory_gap_enabled"] is True
    assert result["mandatory_gap_k"] == 3


# Test that invalid K values raise ValueError instead of being silently accepted.
def test_from_dict_raises_for_invalid_k_value():
    data = {
        "mandatory_gap_k": "not-a-number",
    }

    with pytest.raises(ValueError):
        ConstraintSettings.from_dict(data)


# Test that unknown dictionary keys are ignored and do not break object creation.
def test_from_dict_ignores_unknown_fields():
    data = {
        "mandatory_gap_enabled": True,
        "mandatory_gap_k": 3,
        "unknown_field": "should be ignored",
    }

    settings = ConstraintSettings.from_dict(data)

    assert settings.mandatory_gap_enabled is True
    assert settings.mandatory_gap_k == 3


# Test that positive-K constraints reject zero when the constraint is enabled.
def test_enabled_positive_k_constraint_rejects_zero():
    data = {
        "mandatory_gap_enabled": True,
        "mandatory_gap_k": 0,
    }

    with pytest.raises(ValueError):
        ConstraintSettings.from_dict(data)


# Test that positive-K constraints reject negative values when the constraint is enabled.
def test_enabled_positive_k_constraint_rejects_negative_value():
    data = {
        "daily_cap_enabled": True,
        "daily_cap_k": -1,
    }

    with pytest.raises(ValueError):
        ConstraintSettings.from_dict(data)


# Test that elective conflicts accepts zero because its K value is non-negative.
def test_elective_conflicts_accepts_zero_when_enabled():
    data = {
        "elective_conflicts_enabled": True,
        "elective_conflicts_k": 0,
    }

    settings = ConstraintSettings.from_dict(data)

    assert settings.elective_conflicts_enabled is True
    assert settings.elective_conflicts_k == 0


# Test that elective conflicts rejects negative K values when enabled.
def test_elective_conflicts_rejects_negative_value_when_enabled():
    data = {
        "elective_conflicts_enabled": True,
        "elective_conflicts_k": -1,
    }

    with pytest.raises(ValueError):
        ConstraintSettings.from_dict(data)


# Test that room_scheduling_enabled defaults to False.
def test_room_scheduling_enabled_defaults_to_false():
    settings = ConstraintSettings()
    assert settings.room_scheduling_enabled is False


# Test that room_scheduling_enabled can be set to True directly.
def test_room_scheduling_enabled_can_be_set_to_true():
    settings = ConstraintSettings(room_scheduling_enabled=True)
    assert settings.room_scheduling_enabled is True


# Test that room_scheduling_enabled is loaded correctly as True from a dictionary.
def test_room_scheduling_enabled_loaded_as_true_from_dict():
    settings = ConstraintSettings.from_dict({"room_scheduling_enabled": "true"})
    assert settings.room_scheduling_enabled is True


# Test that room_scheduling_enabled is loaded correctly as False from a dictionary.
def test_room_scheduling_enabled_loaded_as_false_from_dict():
    settings = ConstraintSettings.from_dict({"room_scheduling_enabled": "false"})
    assert settings.room_scheduling_enabled is False


# Test that room_scheduling_enabled is included in to_dict output when True.
def test_room_scheduling_enabled_included_in_to_dict_as_true():
    settings = ConstraintSettings(room_scheduling_enabled=True)
    assert settings.to_dict()["room_scheduling_enabled"] is True


# Test that room_scheduling_enabled is included in to_dict output when False.
def test_room_scheduling_enabled_included_in_to_dict_as_false():
    settings = ConstraintSettings(room_scheduling_enabled=False)
    assert settings.to_dict()["room_scheduling_enabled"] is False