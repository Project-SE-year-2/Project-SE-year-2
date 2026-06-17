from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class ConstraintType(str, Enum):
    """Defines stable names for advanced constraints across the system."""

    MIN_DAYS_REQUIRED = "min_days_required"
    MIN_DAYS_ALL = "min_days_all"
    ELECTIVE_CONFLICTS = "elective_conflicts"
    SPAN_REQUIRED = "span_required"
    MAX_EXAMS_PER_DAY = "max_exams_per_day"


class KValidationRule(Protocol):
    """Validation strategy interface for constraint k values."""

    # Validates the given k value for a specific constraint name.
    def validate(self, constraint_name: str, k: int) -> None:
        ...


@dataclass(frozen=True)
class PositiveIntegerKRule:
    """Validation rule for constraints that require k > 0."""

    # Validates that k is a positive integer.
    def validate(self, constraint_name: str, k: int) -> None:
        if not isinstance(k, int):
            raise ValueError(f"{constraint_name}: k must be an integer.")
        if k <= 0:
            raise ValueError(f"{constraint_name}: k must be a positive integer.")


@dataclass(frozen=True)
class NonNegativeIntegerKRule:
    """Validation rule for constraints that allow k >= 0."""

    # Validates that k is a non-negative integer.
    def validate(self, constraint_name: str, k: int) -> None:
        if not isinstance(k, int):
            raise ValueError(f"{constraint_name}: k must be an integer.")
        if k < 0:
            raise ValueError(f"{constraint_name}: k must be a non-negative integer.")


@dataclass(frozen=True)
class ConstraintDefinition:
    """
    Static metadata for a single advanced constraint.

    This class keeps validation rules outside the runtime config object,
    so new constraints can be added by creating another definition instead
    of changing the validation logic inside ConstraintConfig.
    """

    constraint_type: ConstraintType
    display_name: str
    default_k: int
    validation_rule: KValidationRule


@dataclass
class ConstraintConfig:
    """Runtime setting for one advanced scheduling constraint."""

    enabled: bool = False
    k: int = 1

    # Validates this runtime config against the provided constraint definition.
    def validate(self, definition: ConstraintDefinition) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError(f"{definition.constraint_type.value}: enabled must be a boolean.")
        if self.enabled:
            definition.validation_rule.validate(definition.constraint_type.value, self.k)


DEFAULT_CONSTRAINT_DEFINITIONS: dict[ConstraintType, ConstraintDefinition] = {
    ConstraintType.MIN_DAYS_REQUIRED: ConstraintDefinition(
        constraint_type=ConstraintType.MIN_DAYS_REQUIRED,
        display_name="Minimum days required between exams",
        default_k=1,
        validation_rule=PositiveIntegerKRule(),
    ),
    ConstraintType.MIN_DAYS_ALL: ConstraintDefinition(
        constraint_type=ConstraintType.MIN_DAYS_ALL,
        display_name="Minimum days between all exams in the same program and year",
        default_k=1,
        validation_rule=PositiveIntegerKRule(),
    ),
    ConstraintType.ELECTIVE_CONFLICTS: ConstraintDefinition(
        constraint_type=ConstraintType.ELECTIVE_CONFLICTS,
        display_name="Elective exam conflicts in the same program",
        default_k=0,
        validation_rule=NonNegativeIntegerKRule(),
    ),
    ConstraintType.SPAN_REQUIRED: ConstraintDefinition(
        constraint_type=ConstraintType.SPAN_REQUIRED,
        display_name="Minimum span between first and last obligatory exam",
        default_k=1,
        validation_rule=PositiveIntegerKRule(),
    ),
    ConstraintType.MAX_EXAMS_PER_DAY: ConstraintDefinition(
        constraint_type=ConstraintType.MAX_EXAMS_PER_DAY,
        display_name="Maximum number of exams scheduled on the same day",
        default_k=1,
        validation_rule=PositiveIntegerKRule(),
    ),
}


# Creates a fresh default config dictionary so each settings object owns its own configs.
def _default_configs() -> dict[ConstraintType, ConstraintConfig]:
    return {
        constraint_type: ConstraintConfig(enabled=False, k=definition.default_k)
        for constraint_type, definition in DEFAULT_CONSTRAINT_DEFINITIONS.items()
    }


@dataclass
class ConstraintSettings:
    """
    Central configuration object for all advanced scheduling constraints.

    This object is designed to be shared by the scheduling engine, GUI settings
    screen, and CLI/file-based mode.
    """

    configs: dict[ConstraintType, ConstraintConfig] = field(default_factory=_default_configs)

    # Returns the config object for the requested constraint type.
    def get(self, constraint_type: ConstraintType) -> ConstraintConfig:
        self._ensure_known_constraint(constraint_type)
        return self.configs[constraint_type]

    # Updates one constraint setting and validates the new value immediately.
    def set_constraint(self, constraint_type: ConstraintType, enabled: bool, k: int) -> None:
        self._ensure_known_constraint(constraint_type)
        new_config = ConstraintConfig(enabled=enabled, k=k)
        new_config.validate(DEFAULT_CONSTRAINT_DEFINITIONS[constraint_type])
        self.configs[constraint_type] = new_config

    # Returns True when the requested constraint is enabled.
    def is_enabled(self, constraint_type: ConstraintType) -> bool:
        return self.get(constraint_type).enabled

    # Returns the k value for the requested constraint.
    def k_value(self, constraint_type: ConstraintType) -> int:
        return self.get(constraint_type).k

    # Validates all stored constraint settings.
    def validate(self) -> None:
        for constraint_type, config in self.configs.items():
            self._ensure_known_constraint(constraint_type)
            config.validate(DEFAULT_CONSTRAINT_DEFINITIONS[constraint_type])

    # Converts the settings object into a simple dictionary for UI/file serialization.
    def to_dict(self) -> dict[str, dict]:
        return {
            constraint_type.value: {
                "enabled": config.enabled,
                "k": config.k,
            }
            for constraint_type, config in self.configs.items()
        }

    # Builds a ConstraintSettings object from a dictionary loaded from UI/file input.
    @classmethod
    def from_dict(cls, raw: dict) -> "ConstraintSettings":
        settings = cls()
        for raw_key, raw_config in raw.items():
            constraint_type = ConstraintType(raw_key)
            settings.set_constraint(
                constraint_type=constraint_type,
                enabled=bool(raw_config.get("enabled", False)),
                k=int(raw_config.get("k", DEFAULT_CONSTRAINT_DEFINITIONS[constraint_type].default_k)),
            )
        settings.validate()
        return settings

    # Ensures that the given constraint type exists in the definitions registry and config map.
    def _ensure_known_constraint(self, constraint_type: ConstraintType) -> None:
        if constraint_type not in DEFAULT_CONSTRAINT_DEFINITIONS:
            raise ValueError(f"Unknown constraint type: {constraint_type}")
        if constraint_type not in self.configs:
            definition = DEFAULT_CONSTRAINT_DEFINITIONS[constraint_type]
            self.configs[constraint_type] = ConstraintConfig(False, definition.default_k)
