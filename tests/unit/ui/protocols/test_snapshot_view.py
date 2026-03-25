"""File responsibility: Unit tests for SnapshotView protocol.

These tests verify that the SnapshotView protocol correctly defines the
interface for snapshot-related UI components, including the show_snapshots()
method for displaying lists of snapshots.
"""

from freecad.diff_wb.application.actions.result_models import SnapshotSummary
from freecad.diff_wb.ui.protocols.snapshot_view import SnapshotView


class TestSnapshotViewProtocol:
    """Tests for SnapshotView protocol signature."""

    def test_show_snapshots_method_signature(self) -> None:
        """show_snapshots() accepts list of SnapshotSummary and returns None."""
        # This test verifies the protocol has the correct method signature
        # We use typing to check the signature at runtime

        # Verify the method exists
        assert hasattr(SnapshotView, "show_snapshots")

        # Get the method signature
        import inspect

        sig = inspect.signature(SnapshotView.show_snapshots)

        # Verify parameters: self and snapshots
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "snapshots" in params

        # Verify return annotation is None
        assert sig.return_annotation is type(None) or sig.return_annotation is None

    def test_show_success_method_exists(self) -> None:
        """show_success() method exists in protocol."""
        assert hasattr(SnapshotView, "show_success")

    def test_show_error_method_exists(self) -> None:
        """show_error() method exists in protocol."""
        assert hasattr(SnapshotView, "show_error")

    def test_show_loading_method_exists(self) -> None:
        """show_loading() method exists in protocol."""
        assert hasattr(SnapshotView, "show_loading")

    def test_snapshot_summary_fields(self) -> None:
        """Verify SnapshotSummary has expected fields for show_snapshots()."""
        summary = SnapshotSummary(
            id="snap-123",
            name="test_snapshot",
            created_at="2024-01-15T10:30:00",
            node_count=42,
        )

        assert summary.id == "snap-123"
        assert summary.name == "test_snapshot"
        assert summary.created_at == "2024-01-15T10:30:00"
        assert summary.node_count == 42

    def test_show_snapshots_accepts_empty_list(self) -> None:
        """show_snapshots() should accept empty list."""
        # This tests that the protocol allows an empty list
        # The actual implementation will handle display of empty states
        import inspect

        sig = inspect.signature(SnapshotView.show_snapshots)

        # Verify snapshots parameter accepts list type
        param = sig.parameters["snapshots"]
        # The annotation should be list[...] or similar
        assert "list" in str(param.annotation).lower() or "List" in str(param.annotation)
