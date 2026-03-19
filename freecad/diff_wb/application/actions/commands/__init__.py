"""Module responsibility: Command actions that change state."""

from .compare_snapshots import CompareSnapshotsAction
from .take_snapshot import TakeSnapshotAction


__all__ = ["TakeSnapshotAction", "CompareSnapshotsAction"]
