"""Module responsibility: List snapshots query action."""

from ....domain.snapshots.repository import SnapshotRepository
from ..result_models import SnapshotSummary


class ListSnapshotsAction:
    """Query all snapshots and return summaries.

    This action retrieves all snapshots from the repository
    and returns them as simplified summary objects suitable
    for display in UI lists.

    Dependencies are injected for testability.
    """

    def __init__(self, snapshot_repo: SnapshotRepository) -> None:
        """Initialize with required dependencies.

        Args:
            snapshot_repo: Repository to retrieve snapshots from
        """
        self._snapshot_repo = snapshot_repo

    def execute(self) -> list[SnapshotSummary]:
        """Return list of all snapshots.

        Returns:
            List of SnapshotSummary objects (read-only query).

        Raises:
            RuntimeError: If snapshot retrieval fails
        """
        try:
            snapshots = self._snapshot_repo.get_all_snapshots()

            return [
                SnapshotSummary(
                    id=snapshot.snapshot_id,
                    name=snapshot.document_name,
                    created_at=snapshot.timestamp.isoformat(),
                    node_count=snapshot.node_count,
                )
                for snapshot in snapshots
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to list snapshots: {str(e)}") from e
