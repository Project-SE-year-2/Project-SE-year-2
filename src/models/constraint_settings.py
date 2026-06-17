from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass
class ConstraintSettings:
    mandatory_gap_enabled: bool = False
    mandatory_gap_k: int = 0

    all_gap_enabled: bool = False
    all_gap_k: int = 0

    elective_conflicts_enabled: bool = False
    elective_conflicts_k: int = 0

    spread_enabled: bool = False
    spread_k: int = 0

    daily_cap_enabled: bool = False
    daily_cap_k: int = 0

    # Convert the settings object into a plain dictionary.
    def to_dict(self) -> dict:
        return asdict(self)

    # Build a ConstraintSettings object from a dictionary while normalizing and validating field types.
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConstraintSettings":
        valid_field_names = {field.name for field in fields(cls)}
        cleaned: dict[str, Any] = {}

        for field_name in valid_field_names:
            if field_name not in data:
                continue

            value = data[field_name]

            if field_name.endswith("_k"):
                cleaned[field_name] = cls._to_int(value)
            elif field_name.endswith("_enabled"):
                cleaned[field_name] = cls._to_bool(value)
            else:
                cleaned[field_name] = value

        settings = cls(**cleaned)
        settings.validate()
        return settings

    # Validate K values according to the enabled constraint rules from the requirements document.
    def validate(self) -> None:
        positive_k_fields = [
            ("mandatory_gap_enabled", "mandatory_gap_k"),
            ("all_gap_enabled", "all_gap_k"),
            ("spread_enabled", "spread_k"),
            ("daily_cap_enabled", "daily_cap_k"),
        ]

        for enabled_field, k_field in positive_k_fields:
            if getattr(self, enabled_field) and getattr(self, k_field) <= 0:
                raise ValueError(f"{k_field} must be a positive integer when enabled.")

        if self.elective_conflicts_enabled and self.elective_conflicts_k < 0:
            raise ValueError(
                "elective_conflicts_k must be a non-negative integer when enabled."
            )

    # Convert a raw value into an integer K value.
    @staticmethod
    def _to_int(value: Any) -> int:
        return int(value)

    # Convert a raw value into a boolean enabled flag.
    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y", "on"}

        return bool(value)