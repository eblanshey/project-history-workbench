"""File responsibility: Unit tests for SnapshotPresenter.

These tests verify that the presenter passes raw data to views without
formatting user-facing messages. Translation and formatting are handled
by the view layer.

On successful snapshot, the presenter also triggers auto-refresh by calling
load_snapshots() to update the snapshot list immediately.
"""

from unittest.mock import MagicMock

from freecad.diff_wb.application.actions.result_models import SnapshotResult, SnapshotSummary
from freecad.diff_wb.ui.presenters.snapshot_presenter import SnapshotPresenter
from tests.fakes.fake_snapshot_view import FakeSnapshotView


class TestSnapshotPresenter:
    """Tests for SnapshotPresenter."""

    def test_present_result_success_calls_view(self):
        """Calls view.show_success() and auto-refreshes on successful snapshot."""
        # Arrange
        fake_view = FakeSnapshotView()
        mock_action = MagicMock()
        mock_action.execute.return_value = []  # Empty list after refresh
        presenter = SnapshotPresenter(fake_view, list_snapshots_action=mock_action)
        result = SnapshotResult(
            success=True,
            snapshot_id="snap-123",
            snapshot_name="my_snapshot",
            error_message=None,
        )

        # Act
        presenter.present_result(result)

        # Assert
        # Two calls: show_success + show_snapshots (auto-refresh)
        assert fake_view.get_call_count() == 2
        first_call = fake_view._call_log[0]
        assert first_call["method"] == "show_success"
        assert first_call["snapshot_name"] == "my_snapshot"
        # Second call is show_snapshots for auto-refresh
        second_call = fake_view._call_log[1]
        assert second_call["method"] == "show_snapshots"

    def test_present_result_error_calls_view(self):
        """Calls view.show_error() on failed snapshot."""
        # Arrange
        fake_view = FakeSnapshotView()
        presenter = SnapshotPresenter(fake_view)
        result = SnapshotResult(
            success=False,
            snapshot_id=None,
            snapshot_name=None,
            error_message="Disk space insufficient",
        )

        # Act
        presenter.present_result(result)

        # Assert
        assert fake_view.get_call_count() == 1
        last_call = fake_view._last_call
        assert last_call["method"] == "show_error"
        assert last_call["error_message"] == "Disk space insufficient"

    def test_passes_raw_snapshot_name_without_formatting(self):
        """Presenter passes raw snapshot_name - view handles formatting."""
        # Arrange
        fake_view = FakeSnapshotView()
        # Without list_snapshots_action, we only get show_success call
        presenter = SnapshotPresenter(fake_view)
        result = SnapshotResult(
            success=True,
            snapshot_id="snap-456",
            snapshot_name="test_snapshot",
            error_message=None,
        )

        # Act
        presenter.present_result(result)

        # Assert
        # First call is show_success with raw snapshot_name
        first_call = fake_view._call_log[0]
        assert first_call["method"] == "show_success"
        assert first_call["snapshot_name"] == "test_snapshot"
        # No pre-formatted message - that's the view's responsibility
        assert "message" not in first_call or "created successfully" not in str(first_call.get("message", ""))

    def test_passes_error_message_as_is(self):
        """Error message passed through without modification."""
        # Arrange
        fake_view = FakeSnapshotView()
        presenter = SnapshotPresenter(fake_view)
        result = SnapshotResult(
            success=False,
            snapshot_id=None,
            snapshot_name=None,
            error_message="Permission denied",
        )

        # Act
        presenter.present_result(result)

        # Assert
        last_call = fake_view._last_call
        assert last_call["error_message"] == "Permission denied"

    def test_load_snapshots_calls_action_and_view(self):
        """load_snapshots calls action.execute() and passes result to view.show_snapshots()."""
        # Arrange
        fake_view = FakeSnapshotView()
        mock_action = MagicMock()
        snapshots = [
            SnapshotSummary(id="snap-1", name="snapshot_1", created_at="2024-01-01T10:00:00", node_count=5),
            SnapshotSummary(id="snap-2", name="snapshot_2", created_at="2024-01-02T11:00:00", node_count=3),
        ]
        mock_action.execute.return_value = snapshots
        presenter = SnapshotPresenter(fake_view, list_snapshots_action=mock_action)

        # Act
        presenter.load_snapshots()

        # Assert
        mock_action.execute.assert_called_once()
        assert fake_view.get_call_count() == 1
        last_call = fake_view._last_call
        assert last_call["method"] == "show_snapshots"
        assert last_call["snapshots"] == snapshots

    def test_load_snapshots_with_empty_list_shows_placeholder(self):
        """load_snapshots handles empty list correctly (view shows placeholder)."""
        # Arrange
        fake_view = FakeSnapshotView()
        mock_action = MagicMock()
        mock_action.execute.return_value = []
        presenter = SnapshotPresenter(fake_view, list_snapshots_action=mock_action)

        # Act
        presenter.load_snapshots()

        # Assert
        mock_action.execute.assert_called_once()
        assert fake_view.get_call_count() == 1
        last_call = fake_view._last_call
        assert last_call["method"] == "show_snapshots"
        assert last_call["snapshots"] == []

    def test_load_snapshots_handles_action_exception(self):
        """load_snapshots catches exceptions from action and passes to view.show_error()."""
        # Arrange
        fake_view = FakeSnapshotView()
        mock_action = MagicMock()
        mock_action.execute.side_effect = RuntimeError("Database connection failed")
        presenter = SnapshotPresenter(fake_view, list_snapshots_action=mock_action)

        # Act
        presenter.load_snapshots()

        # Assert
        mock_action.execute.assert_called_once()
        assert fake_view.get_call_count() == 1
        last_call = fake_view._last_call
        assert last_call["method"] == "show_error"
        assert "Database connection failed" in last_call["error_message"]

    def test_refresh_snapshots_is_alias_for_load_snapshots(self):
        """refresh_snapshots is an alias for load_snapshots."""
        # Arrange
        fake_view = FakeSnapshotView()
        mock_action = MagicMock()
        snapshots = [SnapshotSummary(id="snap-1", name="test", created_at="2024-01-01T10:00:00", node_count=5)]
        mock_action.execute.return_value = snapshots
        presenter = SnapshotPresenter(fake_view, list_snapshots_action=mock_action)

        # Act
        presenter.refresh_snapshots()

        # Assert
        mock_action.execute.assert_called_once()
        assert fake_view.get_call_count() == 1
        last_call = fake_view._last_call
        assert last_call["method"] == "show_snapshots"

    def test_present_result_success_triggers_auto_refresh(self):
        """After successful snapshot, load_snapshots() is called to refresh the list."""
        # Arrange
        fake_view = FakeSnapshotView()
        mock_action = MagicMock()
        snapshot_result = SnapshotResult(
            success=True,
            snapshot_id="snap-789",
            snapshot_name="new_snapshot",
            error_message=None,
        )
        snapshots_after_refresh = [
            SnapshotSummary(id="snap-789", name="new_snapshot", created_at="2024-01-03T12:00:00", node_count=5),
        ]
        mock_action.execute.return_value = snapshots_after_refresh
        presenter = SnapshotPresenter(fake_view, list_snapshots_action=mock_action)

        # Act
        presenter.present_result(snapshot_result)

        # Assert
        # Two calls: show_success + show_snapshots (auto-refresh)
        assert fake_view.get_call_count() == 2
        first_call = fake_view._call_log[0]
        assert first_call["method"] == "show_success"
        assert first_call["snapshot_name"] == "new_snapshot"

        # Second call: show_snapshots to refresh the list with updated data
        second_call = fake_view._call_log[1]
        assert second_call["method"] == "show_snapshots"
        assert second_call["snapshots"] == snapshots_after_refresh
        mock_action.execute.assert_called_once()

    def test_present_result_error_does_not_trigger_refresh(self):
        """On failed snapshot, load_snapshots() is NOT called - only error shown."""
        # Arrange
        fake_view = FakeSnapshotView()
        mock_action = MagicMock()
        result = SnapshotResult(
            success=False,
            snapshot_id=None,
            snapshot_name=None,
            error_message="Disk space insufficient",
        )
        presenter = SnapshotPresenter(fake_view, list_snapshots_action=mock_action)

        # Act
        presenter.present_result(result)

        # Assert
        # Only one call: show_error
        assert fake_view.get_call_count() == 1
        last_call = fake_view._last_call
        assert last_call["method"] == "show_error"
        assert last_call["error_message"] == "Disk space insufficient"
        # Action should not be called on error
        mock_action.execute.assert_not_called()
