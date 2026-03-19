"""Module responsibility: Snapshot result presenter."""

from ...application.actions.result_models import SnapshotResult
from ..protocols.snapshot_view import SnapshotView


class SnapshotPresenter:
    """Transform SnapshotResult into view calls.

    This presenter formats snapshot operation results and tells
    the view what to display to the user.

    Dependencies are injected for testability.
    """

    def __init__(self, view: SnapshotView) -> None:
        """Initialize with required dependencies.

        Args:
            view: SnapshotView implementation to display results
        """
        self._view = view

    def present_result(self, result: SnapshotResult) -> None:
        """Format result and tell view what to show.

        Args:
            result: SnapshotResult from TakeSnapshotAction.execute()
        """
        if result.success:
            self._view.show_success(
                message=f"Snapshot '{result.snapshot_name}' created successfully",
                snapshot_id=result.snapshot_id or "",
            )
        else:
            self._view.show_error(result.error_message or "Unknown error occurred")
