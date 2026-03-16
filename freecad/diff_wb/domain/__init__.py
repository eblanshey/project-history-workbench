# SPDX-License-Identifier: LGPL-3.0-or-later
"""Domain models for the Diff Workbench.

This package contains the core domain models that represent FreeCAD documents
and snapshots. These models are pure Python with no FreeCAD dependencies,
enabling easy testing and validation.

Note: Diff result models (DiffState, PropertyDiff, NodeDiff, DiffSummary, DiffResult)
are located in the diff/ module, not here.
"""

from .property_value import (
    Placement,
    PropertyType,
    PropertyValue,
    Rotation,
    Vector,
    make_property_value,
)
from .snapshot import Snapshot, TreeNode


__all__ = [
    # Placement
    "Vector",
    "Rotation",
    "Placement",
    # Property values
    "PropertyType",
    "PropertyValue",
    "make_property_value",
    # Snapshots
    "TreeNode",
    "Snapshot",
]
