# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Tests for FreeCAD command entry points.

These tests verify that commands correctly delegate to actions and presenters.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from freecad.diff_wb.entrypoints.commands import (
    _CommitCommand,
    _OpenAllDocumentsInRepositoryCommand,
    _OpenDiffWindowCommand,
    _RecomputeActiveDocumentCommand,
    _RecomputeAllOpenDocumentsCommand,
    _RefreshRepositoryCommand,
    _SwapColumnsCommand,
)


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


class TestRefreshRepositoryCommand:
    """Tests for _RefreshRepositoryCommand."""

    @patch("freecad.diff_wb.ui.registry.ui_registry")
    def test_refresh_repository_command_calls_git_repository_presenter(
        self,
        mock_ui_registry: Mock,
    ) -> None:
        """Activated delegates to GitRepositoryPresenter refresh API."""
        mock_presenter = MagicMock()
        mock_ui_registry.git_repository_presenter = mock_presenter

        command = _RefreshRepositoryCommand()

        command.Activated()

        mock_presenter.refresh_repository_and_commits.assert_called_once_with()

    def test_refresh_repository_command_resources_correct(self) -> None:
        """Menu text, tooltip, and icon path are correct."""
        command = _RefreshRepositoryCommand()

        resources = command.GetResources()

        assert resources["MenuText"] == "Refresh Git Repository and Commits"
        assert "refresh" in resources["ToolTip"].lower()
        assert resources["Pixmap"].endswith("RefreshRepository.svg")
        assert command.IsActive() is True


class TestRecomputeAllOpenDocumentsCommand:
    """Tests for _RecomputeAllOpenDocumentsCommand."""

    @patch("freecad.diff_wb._container.get_container")
    def test_activated_calls_application_action(self, mock_get_container: Mock) -> None:
        """Activated delegates to application action execute API."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        command = _RecomputeAllOpenDocumentsCommand()

        command.Activated()

        mock_container.recompute_all_open_documents_action.execute.assert_called_once_with()

    def test_resources_and_activation(self) -> None:
        """Command resources are valid and command active."""
        command = _RecomputeAllOpenDocumentsCommand()

        resources = command.GetResources()

        assert resources["MenuText"] == "Recompute All"
        assert "recompute" in resources["ToolTip"].lower()
        assert resources["Pixmap"].endswith("RecomputeAll.svg")
        assert command.IsActive() is True


class TestRecomputeActiveDocumentCommand:
    """Tests for _RecomputeActiveDocumentCommand."""

    @patch("freecad.diff_wb._container.get_container")
    def test_activated_calls_freecad_port_recompute(self, mock_get_container: Mock) -> None:
        """Activated delegates to FreeCAD port recompute API."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        command = _RecomputeActiveDocumentCommand()

        command.Activated()

        mock_container._freecad_port.try_recompute_active_document.assert_called_once_with()

    def test_resources_and_activation(self) -> None:
        """Command resources are valid and command active."""
        command = _RecomputeActiveDocumentCommand()

        resources = command.GetResources()

        assert resources["MenuText"] == "Recompute Active Document"
        assert "recompute" in resources["ToolTip"].lower()
        assert resources["Pixmap"] == "view-refresh"
        assert command.IsActive() is True


class TestCommitCommand:
    """Tests for _CommitCommand."""

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_commit_command_no_repository_shows_warning(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When no git repository, shows warning and doesn't proceed."""
        # Setup
        mock_ui_registry.ui_state.git_repository = None

        command = _CommitCommand()

        # Execute
        command.Activated()

        # Verify
        mock_message_box.warning.assert_called_once()

    def test_commit_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        # Setup
        command = _CommitCommand()

        # Execute
        resources = command.GetResources()

        # Verify
        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Commit"
        assert "commit" in resources["ToolTip"].lower()
        assert "Commit.svg" in resources["Pixmap"]

    def test_is_active_returns_true(self) -> None:
        """Command is always active."""
        # Setup
        command = _CommitCommand()

        # Execute
        result = command.IsActive()

        # Verify
        assert result is True


class TestOpenAllDocumentsInRepositoryCommand:
    """Tests for _OpenAllDocumentsInRepositoryCommand."""

    @patch("PySide6.QtWidgets.QMessageBox")
    @patch("freecad.diff_wb.ui.registry.ui_registry")
    @patch("freecad.diff_wb._container.get_container")
    def test_open_all_documents_no_repository_shows_warning(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
        mock_message_box: Mock,
    ) -> None:
        """When no git repository, shows warning and doesn't proceed."""
        # Setup
        mock_ui_registry.ui_state.git_repository = None

        command = _OpenAllDocumentsInRepositoryCommand()

        # Execute
        command.Activated()

        # Verify
        mock_message_box.warning.assert_called_once()

    def test_resources_and_activation(self) -> None:
        """Command resources are valid and command active."""
        command = _OpenAllDocumentsInRepositoryCommand()

        resources = command.GetResources()

        assert resources["MenuText"] == "Open All Documents in Repository"
        assert "open" in resources["ToolTip"].lower()
        assert resources["Pixmap"].endswith("OpenAllDocuments.svg")
        assert command.IsActive() is True


class TestOpenDiffWindowCommand:
    """Tests for _OpenDiffWindowCommand."""

    def test_activated_calls_create_or_show_diff_panel(self) -> None:
        """Activated calls workbench create_or_show_diff_panel method."""
        # Skip this test if FreeCADGui is not available (unit test environment)
        try:
            import FreeCADGui  # pylint: disable=import-error
        except ImportError:
            pytest.skip("FreeCADGui not available in test environment")

        # Setup
        mock_workbench = MagicMock()
        with patch.object(FreeCADGui, "getWorkbench", return_value=mock_workbench):
            command = _OpenDiffWindowCommand()

            # Execute
            command.Activated()

            # Verify
            FreeCADGui.getWorkbench.assert_called_once_with("DiffWorkbench")
            mock_workbench.create_or_show_diff_panel.assert_called_once_with()

    def test_resources_and_activation(self) -> None:
        """Command resources are valid and command active."""
        command = _OpenDiffWindowCommand()

        resources = command.GetResources()

        assert resources["MenuText"] == "Open Diff Window"
        assert "diff" in resources["ToolTip"].lower()
        assert resources["Pixmap"].endswith("Logo.svg")
        assert command.IsActive() is True
