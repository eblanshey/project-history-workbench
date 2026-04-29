"""File responsibility: Unit tests for CompareSnapshotsAction."""

import datetime

from freecad.diff_wb.application.actions.commands import CompareSnapshotsAction
from freecad.diff_wb.domain.snapshots.models import Snapshot, SnapshotObject, SnapshotOccurrence
from freecad.diff_wb.domain.tree import Property
from tests.fakes import FakeDiffEngine, FakeSettingsRepository, FakeSnapshotRepository


def snapshot_from_parts(
    *,
    snapshot_id: str,
    document_name: str,
    timestamp: datetime.datetime,
    objects: list[SnapshotObject],
    occurrences: list[SnapshotOccurrence],
    git_path: str,
) -> Snapshot:
    """Build normalized snapshot from objects and occurrences."""
    return Snapshot(
        snapshot_id=snapshot_id,
        document_name=document_name,
        timestamp=timestamp,
        objects=objects,
        occurrences=occurrences,
        git_path=git_path,
    )


class TestCompareSnapshotsAction:
    """Test suite for CompareSnapshotsAction."""

    def test_execute_success_computes_diff(self) -> None:
        """Happy path: compares two snapshots successfully."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        old_snapshot = snapshot_from_parts(
            snapshot_id="",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            objects=[SnapshotObject(name="Node1", id=1, type_id="Part::Feature", properties={})],
            occurrences=[SnapshotOccurrence(path="Node1", after=None)],
            git_path="",
        )
        new_snapshot = snapshot_from_parts(
            snapshot_id="",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            objects=[SnapshotObject(name="Node1", id=1, type_id="Part::Feature", properties={})],
            occurrences=[SnapshotOccurrence(path="Node1", after=None)],
            git_path="",
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id, new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        assert result.error_message is None
        assert len(diff_engine.compute_diff_calls) == 1

    def test_execute_old_not_found(self) -> None:
        """Error: old snapshot ID doesn't exist."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute("nonexistent-old-id", "some-new-id")

        # Assert
        assert result.success is False
        assert result.diff_result is None
        assert result.error_message == "Old snapshot 'nonexistent-old-id' not found"

    def test_execute_new_not_found(self) -> None:
        """Error: new snapshot ID doesn't exist."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        old_snapshot = snapshot_from_parts(
            snapshot_id="",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
            git_path="",
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id, "nonexistent-new-id")

        # Assert
        assert result.success is False
        assert result.diff_result is None
        assert result.error_message == "New snapshot 'nonexistent-new-id' not found"

    def test_execute_computes_diff(self) -> None:
        """Verifies DiffEngine is called with correct parameters."""
        # Arrange
        snapshot_repo = FakeSnapshotRepository()
        old_snapshot = snapshot_from_parts(
            snapshot_id="",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            objects=[
                SnapshotObject(
                    name="Node1",
                    id=1,
                    type_id="Part::Feature",
                    properties={"Property1": Property.from_freecad("Value1", {}, "Base")},
                )
            ],
            occurrences=[SnapshotOccurrence(path="Node1", after=None)],
            git_path="",
        )
        new_snapshot = snapshot_from_parts(
            snapshot_id="",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            objects=[
                SnapshotObject(
                    name="Node1",
                    id=1,
                    type_id="Part::Feature",
                    properties={"Property1": Property.from_freecad("Value1", {}, "Base")},
                )
            ],
            occurrences=[SnapshotOccurrence(path="Node1", after=None)],
            git_path="",
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        diff_engine = FakeDiffEngine()
        settings_repo = FakeSettingsRepository()

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id, new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        assert result.error_message is None
        assert len(diff_engine.compute_diff_calls) == 1
