# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines the SettingsRepository Protocol for
# retrieving configuration settings used during diff computation.
"""Settings repository interface (port)."""

from typing import Protocol

from .models import Settings


class SettingsRepository(Protocol):
    """Interface for settings access.

    Implementations can use FreeCAD Preferences, in-memory storage, or any other backend.
    """

    def get_excluded_types(self) -> list[str]:
        """Get list of type IDs to exclude from diff computation.

        Returns:
            List of FreeCAD type IDs to exclude (e.g., ["App::Origin"])
        """
        ...

    def get_excluded_properties(self) -> list[str]:
        """Get list of property names to exclude from comparison.

        Returns:
            List of property names to exclude (e.g., ["TimeStamp", "Label2"])
        """
        ...

    def get_excluded_properties_by_type(self) -> dict[str, list[str]]:
        """Get type-specific property exclusions.

        Returns a mapping of FreeCAD type IDs to lists of property names
        that should be excluded only for objects of that type.

        Returns:
            Dict mapping type IDs to lists of property names to exclude
            for that type (e.g., {"TechDraw::DrawSVGTemplate": ["Template"]})
        """
        ...

    def get_settings(self) -> Settings:
        """Get all settings as a Settings object.

        Returns:
            Settings object containing excluded types, properties, and
            type-specific property exclusions
        """
        ...
