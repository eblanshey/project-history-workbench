"""File responsibility: Unit tests for DiffPanelView.show_snapshots() implementation.

These tests verify that the DiffPanelView correctly populates the snapshot list
with SnapshotSummary data, including proper sorting, formatting, and ID storage.
"""

from __future__ import annotations

import pytest


class TestDiffPanelViewShowSnapshots:
    """Tests for DiffPanelView.show_snapshots() method."""

    @pytest.fixture(scope="module")
    def panel(self) -> object:
        """Create a DiffPanelView instance for testing.

        Note: This uses module scope to ensure QApplication is created once
        and reused across all tests in this module.
        """
        from PySide6.QtWidgets import QApplication

        # Ensure QApplication exists before creating widgets
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        from freecad.diff_wb.ui import DiffPanelView

        return DiffPanelView()

    def test_show_snapshots_with_empty_list(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() handles empty list without errors."""

        # Should not raise any exceptions
        panel.show_snapshots([])

        # Snapshot list should be empty
        assert panel.snapshot_list.count() == 0

    def test_show_snapshots_clears_existing_items(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() clears existing items before populating."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        # Add initial items
        panel.show_snapshots(
            [
                SnapshotSummary(id="old-1", name="Old Snapshot 1", created_at="2024-01-01T10:00:00", node_count=10),
            ]
        )
        assert panel.snapshot_list.count() == 1

        # Replace with new list
        panel.show_snapshots(
            [
                SnapshotSummary(id="new-1", name="New Snapshot 1", created_at="2024-02-01T10:00:00", node_count=20),
            ]
        )

        # Should only have the new item
        assert panel.snapshot_list.count() == 1
        assert panel.snapshot_list.item(0).text() == "New Snapshot 1 - Feb 1, 2024 10:00AM"

    def test_show_snapshots_sorts_by_timestamp_newest_first(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() sorts snapshots by timestamp, newest first."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        snapshots = [
            SnapshotSummary(id="snap-1", name="Oldest", created_at="2024-01-01T10:00:00", node_count=10),
            SnapshotSummary(id="snap-2", name="Newest", created_at="2024-03-01T10:00:00", node_count=30),
            SnapshotSummary(id="snap-3", name="Middle", created_at="2024-02-01T10:00:00", node_count=20),
        ]

        panel.show_snapshots(snapshots)

        # Verify order: Newest, Middle, Oldest
        assert panel.snapshot_list.count() == 3
        assert panel.snapshot_list.item(0).text().startswith("Newest")
        assert panel.snapshot_list.item(1).text().startswith("Middle")
        assert panel.snapshot_list.item(2).text().startswith("Oldest")

    def test_show_snapshots_stores_id_in_user_role(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() stores snapshot ID in Qt.UserRole for each item."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        snapshots = [
            SnapshotSummary(id="test-id-123", name="Test Snapshot", created_at="2024-01-15T10:30:00", node_count=42),
        ]

        panel.show_snapshots(snapshots)

        # Verify ID is stored in UserRole
        item = panel.snapshot_list.item(0)
        assert item is not None
        stored_id = item.data(Qt.ItemDataRole.UserRole)
        assert stored_id == "test-id-123"

    def test_show_snapshots_formats_display_correctly(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() formats display as 'name - Month Day, Year Time'."""
        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        snapshots = [
            SnapshotSummary(id="snap-1", name="My Snapshot", created_at="2024-01-15T10:30:00", node_count=42),
        ]

        panel.show_snapshots(snapshots)

        # Check format: "My Snapshot - Jan 15, 2024 10:30 AM"
        item_text = panel.snapshot_list.item(0).text()
        assert item_text == "My Snapshot - Jan 15, 2024 10:30AM"

    def test_show_snapshots_multiple_items_with_ids(self, panel) -> None:  # type: ignore[no-untyped-def]
        """show_snapshots() correctly stores IDs for multiple items."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.application.actions.result_models import SnapshotSummary

        snapshots = [
            SnapshotSummary(id="id-1", name="First", created_at="2024-01-01T09:00:00", node_count=5),
            SnapshotSummary(id="id-2", name="Second", created_at="2024-01-02T10:00:00", node_count=10),
            SnapshotSummary(id="id-3", name="Third", created_at="2024-01-03T11:00:00", node_count=15),
        ]

        panel.show_snapshots(snapshots)

        # Verify all IDs are stored correctly (in sorted order: Third, Second, First)
        assert panel.snapshot_list.item(0).data(Qt.ItemDataRole.UserRole) == "id-3"
        assert panel.snapshot_list.item(1).data(Qt.ItemDataRole.UserRole) == "id-2"
        assert panel.snapshot_list.item(2).data(Qt.ItemDataRole.UserRole) == "id-1"
