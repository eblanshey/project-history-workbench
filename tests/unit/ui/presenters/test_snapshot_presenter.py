"""File responsibility: Unit tests for SnapshotPresenter."""

import pytest

from freecad.diff_wb.application.actions.result_models import SnapshotResult
from freecad.diff_wb.ui.presenters.snapshot_presenter import SnapshotPresenter
from tests.fakes.fake_snapshot_view import FakeSnapshotView


class TestSnapshotPresenter:
    """Tests for SnapshotPresenter."""

    def test_present_result_success_calls_view(self):
        """Calls view.show_success() on successful snapshot."""
        # Arrange
        fake_view = FakeSnapshotView()
        presenter = SnapshotPresenter(fake_view)
        result = SnapshotResult(
            success=True,
            snapshot_id="snap-123",
            snapshot_name="my_snapshot",
            error_message=None,
        )

        # Act
        presenter.present_result(result)

        # Assert
        assert fake_view.get_call_count() == 1
        last_call = fake_view._last_call
        assert last_call["method"] == "show_success"
        assert last_call["snapshot_id"] == "snap-123"

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
        assert last_call["message"] == "Disk space insufficient"

    def test_formats_success_message_correctly(self):
        """Message includes snapshot name."""
        # Arrange
        fake_view = FakeSnapshotView()
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
        last_call = fake_view._last_call
        assert "test_snapshot" in last_call["message"]
        assert "created successfully" in last_call["message"]

    def test_formats_error_message_correctly(self):
        """Error message passed through."""
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
        assert last_call["message"] == "Permission denied"
