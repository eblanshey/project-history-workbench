# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Unit tests for commit/configure author command delegation."""

from unittest.mock import MagicMock, Mock, patch

from freecad.history_wb.entrypoints.commands import _CommitCommand, _ConfigureAuthorCommand


class TestCommitCommand:
    """Tests for _CommitCommand."""

    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
    def test_commit_command_delegates_to_git_repository_presenter(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
    ) -> None:
        """Activated delegates save flow to git repository presenter."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_presenter = MagicMock()
        mock_ui_registry.git_repository_presenter = mock_presenter

        command = _CommitCommand()
        command.Activated()

        mock_presenter.on_save_iteration_requested.assert_called_once_with()

    @patch("freecad.history_wb.entrypoints.commands._ensure_git_repository_presenter_available", return_value=None)
    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb._container.get_container")
    def test_commit_command_shows_warning_when_history_panel_unavailable(
        self,
        mock_get_container: Mock,
        mock_message_box: Mock,
        _mock_presenter_lookup: Mock,
    ) -> None:
        """Activated shows warning when presenter cannot be initialized."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        command = _CommitCommand()
        command.Activated()

        mock_message_box.warning.assert_called_once()

    def test_commit_command_resources_correct(self) -> None:
        """Menu text, tooltips, icons are correct."""
        command = _CommitCommand()
        resources = command.GetResources()

        assert "MenuText" in resources
        assert "ToolTip" in resources
        assert "Pixmap" in resources
        assert resources["MenuText"] == "Save Iteration"
        assert "iteration" in resources["ToolTip"].lower()
        assert "Commit.svg" in resources["Pixmap"]

    def test_commit_is_active_returns_true(self) -> None:
        """Command is always active."""
        command = _CommitCommand()
        assert command.IsActive() is True


class TestConfigureAuthorCommand:
    """Tests for _ConfigureAuthorCommand."""

    @patch("freecad.history_wb.ui.registry.ui_registry")
    @patch("freecad.history_wb._container.get_container")
    def test_configure_author_command_delegates_to_git_repository_presenter(
        self,
        mock_get_container: Mock,
        mock_ui_registry: Mock,
    ) -> None:
        """Activated delegates author flow to git repository presenter."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_presenter = MagicMock()
        mock_ui_registry.git_repository_presenter = mock_presenter

        command = _ConfigureAuthorCommand()
        command.Activated()

        mock_presenter.on_configure_author_requested.assert_called_once_with()

    @patch("freecad.history_wb.entrypoints.commands._ensure_git_repository_presenter_available", return_value=None)
    @patch("freecad.history_wb.qt.QtWidgets.QMessageBox")
    @patch("freecad.history_wb._container.get_container")
    def test_configure_author_command_shows_warning_when_history_panel_unavailable(
        self,
        mock_get_container: Mock,
        mock_message_box: Mock,
        _mock_presenter_lookup: Mock,
    ) -> None:
        """Activated shows warning when presenter cannot be initialized."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        command = _ConfigureAuthorCommand()
        command.Activated()

        mock_message_box.warning.assert_called_once()
