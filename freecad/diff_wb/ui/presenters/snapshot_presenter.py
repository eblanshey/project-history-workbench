"""Module responsibility: Snapshot result presenter.

This presenter transforms SnapshotResult into view protocol calls.
It passes RAW DATA only - it NEVER formats user-facing messages.
Translation and parameter substitution are handled by the view.

Translation Strategy:
    The presenter passes raw values (e.g., snapshot_name) without formatting.
    The view is responsible for:
    1. Looking up the translation template from translation_strings.py
    2. Applying Qt translation via QCoreApplication.translate()
    3. Substituting parameters using Python's % formatting

    Example flow:
        Presenter: self._view.show_success(snapshot_name="my_snapshot")
        View: template = SNAPSHOT_SUCCESS_TEMPLATE  # "Snapshot '%1' created successfully"
        View: translated = QCoreApplication.translate("SnapshotView", template)
        View: final = translated % snapshot_name  # "Snapshot 'my_snapshot' created successfully"
"""

from ...application.actions.queries.list_snapshots import ListSnapshotsAction
from ...application.actions.result_models import SnapshotResult
from ..protocols.snapshot_view import SnapshotView


class SnapshotPresenter:
    """Transform SnapshotResult into view calls.

    This presenter passes raw data to the view for display. It does NOT
    format any user-facing messages - that responsibility belongs to the view.

    Dependencies are injected for testability.
    """

    def __init__(self, view: SnapshotView, list_snapshots_action: ListSnapshotsAction | None = None) -> None:
        """Initialize with required dependencies.

        Args:
            view: SnapshotView implementation to display results
            list_snapshots_action: Action to query all snapshots (optional, required for load_snapshots())
        """
        self._view = view
        self._list_snapshots_action = list_snapshots_action

    def present_result(self, result: SnapshotResult) -> None:
        """Pass result data to view for display.

        On success, also refreshes the snapshot list automatically to show
        the newly created snapshot immediately. The presenter passes raw data
        only. The view handles translation and parameter substitution.

        Args:
            result: SnapshotResult from TakeSnapshotAction.execute()
        """
        if result.success:
            # Pass raw snapshot_name - view handles translation and formatting
            self._view.show_success(snapshot_name=result.snapshot_name)
            # Auto-refresh the snapshot list to show the new snapshot immediately
            self.load_snapshots()
        else:
            # Pass error message as-is - view handles translation of templates
            self._view.show_error(result.error_message or "Unknown error occurred")

    def load_snapshots(self) -> None:
        """Load and display all snapshots.

        Executes ListSnapshotsAction to retrieve all snapshots and passes
        the result to the view for display. The view handles empty lists
        by showing an appropriate placeholder message.

        Any exceptions from the action are caught and passed to
        view.show_error() for user notification.
        """
        try:
            snapshots = self._list_snapshots_action.execute()
            self._view.show_snapshots(snapshots)
        except Exception as e:
            self._view.show_error(str(e))

    def refresh_snapshots(self) -> None:
        """Refresh the snapshot list.

        Convenience alias for load_snapshots(). Used when the semantic
        meaning is "refresh the list" (e.g., user clicked a refresh button).
        Both methods execute the same logic; the distinction is purely
        semantic for code readability.
        """
        self.load_snapshots()
