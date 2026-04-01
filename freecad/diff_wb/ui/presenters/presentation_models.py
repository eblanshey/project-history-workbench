"""File responsibility: UI-friendly presentation models for diff display."""

from dataclasses import dataclass, field
from typing import Any

from ...domain.diff.models import DiffState


__all__ = ["NodePresentation", "PropertyPresentation", "SnapshotPresentation"]


@dataclass(frozen=True)
class NodePresentation:
    """UI-friendly format for a tree node."""

    path: str
    type_id: str
    state: DiffState
    has_changes: bool
    children: list["NodePresentation"] = field(default_factory=list)


@dataclass(frozen=True)
class PropertyPresentation:
    """UI-friendly format for property differences.

    This model stores raw values for computing sub-property diffs when expanded.
    Display formatting is performed on-demand in the view layer using str().
    """

    # Core identification
    name: str
    state: DiffState

    # Value fields - raw values for computing sub-property diffs when expanded
    old_value: Any = None  # Actual old value for expandable properties
    new_value: Any = None  # Actual new value for expandable properties

    # Grouping
    group: str | None = None  # Group name for grouping (e.g., "Base", "Format")


@dataclass(frozen=True)
class SnapshotPresentation:
    """UI-friendly format for snapshot summary."""

    id: str
    name: str
    created_at: str
    node_count: int
