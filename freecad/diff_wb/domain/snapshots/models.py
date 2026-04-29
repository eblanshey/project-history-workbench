# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Snapshot domain models for normalized snapshot storage
# with unique object payloads and path-based occurrences.
"""Snapshot domain models."""

from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import PurePosixPath

from ..tree.property import Property


@dataclass
class SnapshotMetadata:
    """Metadata for a stored snapshot."""

    id: str
    name: str
    timestamp: datetime


@dataclass(frozen=True)
class SnapshotObject:
    """Unique object payload in a snapshot.

    Note:
        `id` retained for deterministic YAML ordering/readability only.
    """

    name: str
    id: int
    type_id: str
    properties: dict[str, Property] = field(default_factory=dict)


@dataclass(frozen=True)
class SnapshotOccurrence:
    """A single tree occurrence of an object."""

    path: str
    after: str | None = None
    _object_name_cache: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Precompute object name from occurrence path."""
        object.__setattr__(self, "_object_name_cache", self.path.rsplit("/", 1)[-1])

    @property
    def object_name(self) -> str:
        """Return cached object name derived from path tail segment."""
        return self._object_name_cache

    @property
    def parent_path(self) -> str | None:
        """Return parent occurrence path, or None for roots."""
        if "/" not in self.path:
            return None
        return self.path.rsplit("/", 1)[0]


@dataclass(frozen=True)
class Snapshot:
    """A snapshot of a FreeCAD document at a point in time."""

    snapshot_id: str
    document_name: str
    timestamp: datetime
    objects: list[SnapshotObject] = field(default_factory=list)
    occurrences: list[SnapshotOccurrence] = field(default_factory=list)
    git_path: str = ""

    @property
    def node_count(self) -> int:
        return len(self.occurrences)

    def __str__(self) -> str:
        if self.git_path:
            return f"Snapshot({self.git_path}, {len(self.objects)} objects, {self.node_count} occurrences)"
        return f"Snapshot({self.document_name}, {len(self.objects)} objects, {self.node_count} occurrences)"

    def find_object(self, name: str) -> SnapshotObject | None:
        for obj in self.objects:
            if obj.name == name:
                return obj
        return None

    def find_occurrence(self, path: str) -> SnapshotOccurrence | None:
        for occ in self.occurrences:
            if occ.path == path:
                return occ
        return None

    def with_identity(self, git_path: str) -> "Snapshot":
        return replace(self, git_path=git_path, document_name=PurePosixPath(git_path).name)
