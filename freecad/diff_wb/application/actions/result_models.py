"""File responsibility: Action result models for commands and queries."""

from dataclasses import dataclass

from ...domain.diff import DiffResult


__all__ = ["SnapshotResult", "CompareResult", "SnapshotSummary"]


@dataclass
class SnapshotResult:
    """Result of snapshot creation operation."""

    success: bool
    snapshot_id: str | None
    snapshot_name: str | None
    error_message: str | None


@dataclass
class CompareResult:
    """Result of comparison operation."""

    success: bool
    diff_result: DiffResult | None
    error_message: str | None


@dataclass
class SnapshotSummary:
    """Summary information for a snapshot (for listing)."""

    id: str
    name: str
    created_at: str
    node_count: int
