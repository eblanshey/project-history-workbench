# SPDX-License-Identifier: LGPL-3.0-or-later
"""Settings port interface for persisted settings.

This module defines the SettingsPort Protocol for accessing FreeCAD's
parameter system, allowing for test doubles in unit tests.
"""

from __future__ import annotations

from typing import Protocol

from .freecad_context import FreeCadContext, get_runtime_context


class SettingsPort(Protocol):
    """Interface for persisted settings access.

    This Protocol defines operations for reading and writing settings,
    allowing for test doubles in unit tests.
    """

    def value(self, key: str, default: object | None = None) -> object | None:
        """Get a setting value by key, returning default if not found."""
        ...

    def set_value(self, key: str, value: object) -> None:
        """Set a setting value by key."""
        ...

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get a list setting, parsing from comma-separated string if needed."""
        ...

    def set_list(self, key: str, values: list[str]) -> None:
        """Set a list setting as a comma-separated string."""
        ...


class SettingsPortAdapter:
    """Runtime adapter implementing SettingsPort using FreeCAD's Parameter system."""

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx
        self._group_path = "User parameter:BaseApp/Preferences/Mod/DiffWorkbench"

    def _get_group(self) -> object:
        return self._ctx.app.ParamGet(self._group_path)

    def value(self, key: str, default: object | None = None) -> object | None:
        group = self._get_group()
        full_key = f"DiffWorkbench/{key}"
        try:
            return group.GetString(full_key, "") or default
        except Exception:  # pylint: disable=broad-exception-caught
            return default

    def set_value(self, key: str, value: object) -> None:
        group = self._get_group()
        full_key = f"DiffWorkbench/{key}"
        group.SetString(full_key, str(value))

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get a list setting, parsing from comma-separated string if needed."""
        raw = self.value(key, "")
        if not raw:
            return default or []
        return [item.strip() for item in raw.split(",") if item.strip()]

    def set_list(self, key: str, values: list[str]) -> None:
        """Set a list setting as a comma-separated string."""
        self.set_value(key, ",".join(values))


def get_settings_port(ctx: FreeCadContext | None = None) -> SettingsPort:
    """Get a SettingsPort instance.

    If no context is provided, creates a runtime context.
    """
    if ctx is None:
        ctx = get_runtime_context()
    return SettingsPortAdapter(ctx)
