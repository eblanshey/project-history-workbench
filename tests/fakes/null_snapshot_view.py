"""Module responsibility: Null snapshot view for testing.

This follows the Null Object pattern to avoid passing None to SnapshotPresenter.
All methods are no-ops.
"""

from typing import Any

from freecad.diff_wb.ui.protocols.snapshot_view import SnapshotView


class NullSnapshotView(SnapshotView):
    """Null object implementation of SnapshotView for use when no view is available.

    This follows the Null Object pattern to avoid passing None to SnapshotPresenter,
    which violates the type contract. All methods are no-ops.
    """

    def show_success(self, snapshot_name: str) -> None:
        """Do nothing - null object pattern."""
        pass

    def show_error(self, error_message: str) -> None:
        """Do nothing - null object pattern."""
        pass

    def show_loading(self, message: str | None = None) -> None:
        """Do nothing - null object pattern."""
        pass

    def show_snapshots(self, snapshots: list[Any]) -> None:
        """Do nothing - null object pattern."""
        pass
