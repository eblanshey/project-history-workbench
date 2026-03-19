"""File responsibility: Snapshot view interface definition."""

from typing import Protocol


__all__ = ["SnapshotView"]


class SnapshotView(Protocol):
    """Interface that any snapshot display component must implement.

    Implemented by QtSnapshotView in the UI views layer.
    """

    def show_success(self, message: str, snapshot_id: str) -> None: ...

    def show_error(self, message: str) -> None: ...

    def show_loading(self, message: str = "Creating snapshot...") -> None: ...
