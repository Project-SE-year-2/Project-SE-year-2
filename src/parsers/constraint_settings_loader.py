from __future__ import annotations

import argparse
from pathlib import Path

from src.models.constraint_settings import ConstraintSettings


class ConstraintSettingsLoader:
    """Loads ConstraintSettings from text files or CLI argument tokens."""

    SECTION_MARKER = "# ADVANCED_CONSTRAINTS"

    _FIELDS = (
        ("mandatory_gap_enabled", bool),
        ("mandatory_gap_k", int),
        ("all_gap_enabled", bool),
        ("all_gap_k", int),
        ("elective_conflicts_enabled", bool),
        ("elective_conflicts_k", int),
        ("spread_enabled", bool),
        ("spread_k", int),
        ("daily_cap_enabled", bool),
        ("daily_cap_k", int),
        ("room_scheduling_enabled", bool),
    )

    @staticmethod
    def from_file(path: str) -> ConstraintSettings:
        """Load constraint settings from a text configuration file."""
        raw: dict[str, str] = {}
        in_section = False
        valid_keys = {name for name, _ in ConstraintSettingsLoader._FIELDS}

        for line in Path(path).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()

            if not stripped:
                continue

            if stripped == ConstraintSettingsLoader.SECTION_MARKER:
                in_section = True
                continue

            if not in_section or stripped.startswith("#"):
                continue

            if "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()

            if key in valid_keys:
                raw[key] = value.strip()

        return ConstraintSettings.from_dict(raw)

    @staticmethod
    def from_cli_args(args: list[str]) -> ConstraintSettings:
        """
        Parse constraint settings from command-line arguments.

        This parser is intended to be used independently from from_file().
        Boolean flags use action="store_true", so omitted flags are treated as
        unspecified/disabled by the resulting ConstraintSettings defaults.
        The CLI path does not support explicit --no-* overrides because file-based
        and CLI-based settings are not merged.
        """
        
        parser = argparse.ArgumentParser(add_help=False)

        for field_name, field_type in ConstraintSettingsLoader._FIELDS:
            cli_name = field_name.replace("_", "-")

            if field_type is bool:
                ConstraintSettingsLoader._add_bool_flag(parser, cli_name, field_name)
            else:
                ConstraintSettingsLoader._add_int_option(parser, cli_name, field_name)

        parsed = parser.parse_args(args)

        raw = {
            key: value
            for key, value in vars(parsed).items()
            if value is not None
        }

        return ConstraintSettings.from_dict(raw)

    @staticmethod
    def _add_bool_flag(
        parser: argparse.ArgumentParser,
        cli_name: str,
        dest_name: str,
    ) -> None:
        """Register a boolean CLI flag that maps kebab-case to snake_case."""
        parser.add_argument(
            f"--{cli_name}",
            action="store_true",
            default=None,
            dest=dest_name,
        )

    @staticmethod
    def _add_int_option(
        parser: argparse.ArgumentParser,
        cli_name: str,
        dest_name: str,
    ) -> None:
        """Register an integer CLI option that maps kebab-case to snake_case."""
        parser.add_argument(
            f"--{cli_name}",
            type=int,
            default=None,
            dest=dest_name,
        )