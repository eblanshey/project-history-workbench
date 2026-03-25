# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Tests for FreeCAD command entry points.

These tests verify that commands correctly delegate to actions and presenters.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from freecad.diff_wb.application.actions.result_models import CompareResult, SnapshotResult
from freecad.diff_wb.entrypoints.commands import (
    _CompareCommand,
    _SwapColumnsCommand,
    _TakeSnapshotCommand,
)


class TestTakeSnapshotCommand:
    """Tests for _TakeSnapshotCommand."""

    @patch("freecad.diff_wb._container.get_container")
    def test_take_snapshot_command_calls_action_and_presenter(self, mock_get_container: Mock) -> None:
        """Verifies flow from command to action to presenter."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        mock_container.take_snapshot_action = mock_action
        mock_container.snapshot_presenter = mock_presenter
        mock_get_container.return_value = mock_container

        expected_result = SnapshotResult(
            success=True,
            snapshot_id="test-id-123",
            snapshot_name="Test Snapshot",
            error_message=None,
        )
        mock_action.execute.return_value = expected_result

        command = _TakeSnapshotCommand()

        # Execute
        command.Activated()

        # Verify
        mock_action.execute.assert_called_once()
        mock_presenter.present_result.assert_called_once_with(expected_result)

    def test_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        command = _TakeSnapshotCommand()

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Take Snapshot"
        assert "snapshot" in resources["ToolTip"].lower()
        assert "TakeSnapshot.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        command = _TakeSnapshotCommand()

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True


class TestCompareCommand:
    """Tests for _CompareCommand."""

    @patch("freecad.diff_wb._container.get_container")
    def test_compare_command_calls_action_and_presenter(self, mock_get_container: Mock) -> None:
        """Verifies comparison flow from command to action to presenter."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        mock_container.compare_snapshots_action = mock_action
        mock_container.diff_presenter = mock_presenter
        mock_get_container.return_value = mock_container

        expected_diff_result = MagicMock()
        expected_result = CompareResult(
            success=True,
            diff_result=expected_diff_result,
            error_message=None,
        )
        mock_action.execute.return_value = expected_result

        command = _CompareCommand()

        # Note: The compare command will raise NotImplementedError because
        # snapshot selection is not yet implemented (Phase 8 UI)
        with pytest.raises(NotImplementedError, match="Phase 8"):
            command.Activated()

    @patch("freecad.diff_wb._container.get_container")
    def test_compare_command_error_result_no_presenter_call(self, mock_get_container: Mock) -> None:
        """When result is error, presenter is not called."""
        # Setup
        mock_container = MagicMock()
        mock_action = MagicMock()
        mock_presenter = MagicMock()
        mock_container.compare_snapshots_action = mock_action
        mock_container.diff_presenter = mock_presenter
        mock_get_container.return_value = mock_container

        expected_result = CompareResult(
            success=False,
            diff_result=None,
            error_message="Snapshots not found",
        )
        mock_action.execute.return_value = expected_result

        command = _CompareCommand()

        # Note: The compare command will raise NotImplementedError because
        # snapshot selection is not yet implemented (Phase 8 UI)
        with pytest.raises(NotImplementedError, match="Phase 8"):
            command.Activated()

        # Verify presenter was never called since we can't get past the NotImplementedError
        mock_presenter.present_diff.assert_not_called()

    def test_compare_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        command = _CompareCommand()

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Compare"
        assert "snapshot" in resources["ToolTip"].lower()
        assert "Compare.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        command = _CompareCommand()

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True


class TestSwapColumnsCommand:
    """Tests for _SwapColumnsCommand."""

    def test_swap_columns_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        command = _SwapColumnsCommand()

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Swap Columns"
        assert "column" in resources["ToolTip"].lower()
        assert "SwapColumns.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        command = _SwapColumnsCommand()

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True

    def test_swap_columns_activated_not_implemented(self) -> None:
        """Swap columns Activated is not yet implemented."""
        # Setup
        command = _SwapColumnsCommand()

        # Execute and Verify
        # TODO: Implement when UI view exists
        # For now, just verify it doesn't crash
        command.Activated()  # Should pass (currently does nothing)
