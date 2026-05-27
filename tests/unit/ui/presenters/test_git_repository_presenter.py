# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitRepositoryPresenter.
# These tests verify that the presenter correctly orchestrates git repository
# detection and updates both the application state and the view.
"""Unit tests for GitRepositoryPresenter."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from freecad.history_wb.application.actions.result_models import Result
from freecad.history_wb.domain.git.models import GitIdentity
from freecad.history_wb.domain.git.models import GitCommit, GitRepository
from freecad.history_wb.ui.presenters.git_repository_presenter import GitConfigDialogResult, GitRepositoryPresenter


@pytest.fixture
def mock_view() -> MagicMock:
    """Create a mock DiffPanelView."""
    return MagicMock()


@pytest.fixture
def mock_find_action() -> MagicMock:
    """Create a mock FindActiveGitRepositoryAction."""
    return MagicMock()


@pytest.fixture
def mock_get_commits_action() -> MagicMock:
    """Create a mock GetCommitsAction."""
    return MagicMock()


@pytest.fixture
def mock_get_staged_file_paths_action() -> MagicMock:
    """Create a mock GetStagedFilePathsAction."""
    return MagicMock()


@pytest.fixture
def mock_commit_staging_action() -> MagicMock:
    """Create a mock CommitStagingAction."""
    return MagicMock()


@pytest.fixture
def mock_get_git_identity_action() -> MagicMock:
    """Create a mock GetGitIdentityAction."""
    return MagicMock()


@pytest.fixture
def mock_save_git_identity_action() -> MagicMock:
    """Create a mock SaveGitIdentityAction."""
    return MagicMock()


@pytest.fixture
def mock_can_write_global_git_identity_action() -> MagicMock:
    """Create a mock CanWriteGlobalGitIdentityAction."""
    return MagicMock()


@pytest.fixture
def mock_ui_state() -> MagicMock:
    """Create a mock UIState."""
    return MagicMock()


@pytest.fixture
def presenter(
    mock_view: MagicMock,
    mock_find_action: MagicMock,
    mock_get_commits_action: MagicMock,
    mock_get_staged_file_paths_action: MagicMock,
    mock_commit_staging_action: MagicMock,
    mock_get_git_identity_action: MagicMock,
    mock_save_git_identity_action: MagicMock,
    mock_can_write_global_git_identity_action: MagicMock,
    mock_ui_state: MagicMock,
) -> GitRepositoryPresenter:
    """Create a GitRepositoryPresenter instance with mocked dependencies."""
    return GitRepositoryPresenter(
        view=mock_view,
        find_git_repo_action=mock_find_action,
        get_commits_action=mock_get_commits_action,
        get_staged_file_paths_action=mock_get_staged_file_paths_action,
        commit_staging_action=mock_commit_staging_action,
        get_git_identity_action=mock_get_git_identity_action,
        save_git_identity_action=mock_save_git_identity_action,
        can_write_global_git_identity_action=mock_can_write_global_git_identity_action,
        ui_state=mock_ui_state,
        clear_doc_diffs=MagicMock(),
    )


class TestGitRepositoryPresenter:
    """Tests for GitRepositoryPresenter."""

    def test_on_workbench_activated_with_successful_detection(
        self,
        presenter: GitRepositoryPresenter,
        mock_view: MagicMock,
        mock_find_action: MagicMock,
        mock_ui_state: MagicMock,
    ) -> None:
        """on_workbench_activated() updates state and view when detection succeeds."""
        # Arrange
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = repo
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_workbench_activated()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_ui_state.git_repository = repo
        mock_view.show_repository.assert_called_once_with(repo)

    def test_on_workbench_activated_with_failed_detection(
        self,
        presenter: GitRepositoryPresenter,
        mock_view: MagicMock,
        mock_find_action: MagicMock,
        mock_ui_state: MagicMock,
    ) -> None:
        """on_workbench_activated() sets state to None and shows no repo message on failure."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.message = "No active document"
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_workbench_activated()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_ui_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)
        mock_view.show_commits.assert_called_once_with([], show_special_items=False)

    def test_on_workbench_activated_with_none_repository(
        self,
        presenter: GitRepositoryPresenter,
        mock_view: MagicMock,
        mock_find_action: MagicMock,
        mock_ui_state: MagicMock,
    ) -> None:
        """on_workbench_activated() handles case where action returns None repository."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = None  # Action succeeded but found no repo
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_workbench_activated()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_ui_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)

    def test_presenter_initialization_stores_dependencies(
        self,
        mock_view: MagicMock,
        mock_find_action: MagicMock,
        mock_get_commits_action: MagicMock,
        mock_get_staged_file_paths_action: MagicMock,
        mock_commit_staging_action: MagicMock,
        mock_get_git_identity_action: MagicMock,
        mock_save_git_identity_action: MagicMock,
        mock_can_write_global_git_identity_action: MagicMock,
        mock_ui_state: MagicMock,
    ) -> None:
        """Presenter stores all dependencies correctly on initialization."""
        # Act
        presenter = GitRepositoryPresenter(
            view=mock_view,
            find_git_repo_action=mock_find_action,
            get_commits_action=mock_get_commits_action,
            get_staged_file_paths_action=mock_get_staged_file_paths_action,
            commit_staging_action=mock_commit_staging_action,
            get_git_identity_action=mock_get_git_identity_action,
            save_git_identity_action=mock_save_git_identity_action,
            can_write_global_git_identity_action=mock_can_write_global_git_identity_action,
            ui_state=mock_ui_state,
            clear_doc_diffs=MagicMock(),
        )

        # Assert
        assert presenter._view is mock_view
        assert presenter._find_git_repo_action is mock_find_action
        assert presenter._get_commits_action is mock_get_commits_action
        assert presenter._ui_state is mock_ui_state

    def test_on_refresh_clicked_with_successful_detection(
        self,
        presenter: GitRepositoryPresenter,
        mock_view: MagicMock,
        mock_find_action: MagicMock,
        mock_ui_state: MagicMock,
    ) -> None:
        """on_refresh_clicked() updates state and view when detection succeeds."""
        # Arrange
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = repo
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_refresh_clicked()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_ui_state.git_repository = repo
        mock_view.show_repository.assert_called_once_with(repo)

    def test_on_refresh_clicked_with_failed_detection(
        self,
        presenter: GitRepositoryPresenter,
        mock_view: MagicMock,
        mock_find_action: MagicMock,
        mock_ui_state: MagicMock,
    ) -> None:
        """on_refresh_clicked() sets state to None and shows no repo message on failure."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.message = "No active document"
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_refresh_clicked()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_ui_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)
        mock_view.show_commits.assert_called_once_with([], show_special_items=False)

    def test_on_refresh_clicked_with_none_repository(
        self,
        presenter: GitRepositoryPresenter,
        mock_view: MagicMock,
        mock_find_action: MagicMock,
        mock_ui_state: MagicMock,
    ) -> None:
        """on_refresh_clicked() handles case where action returns None repository."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = None  # Action succeeded but found no repo
        mock_find_action.execute.return_value = mock_result

        # Act
        presenter.on_refresh_clicked()

        # Assert
        mock_find_action.execute.assert_called_once()
        mock_ui_state.git_repository = None
        mock_view.show_repository.assert_called_once_with(None)

    def test_presenter_initialization_registers_refresh_callback(
        self,
        mock_view: MagicMock,
        mock_find_action: MagicMock,
        mock_get_commits_action: MagicMock,
        mock_get_staged_file_paths_action: MagicMock,
        mock_commit_staging_action: MagicMock,
        mock_get_git_identity_action: MagicMock,
        mock_save_git_identity_action: MagicMock,
        mock_can_write_global_git_identity_action: MagicMock,
        mock_ui_state: MagicMock,
    ) -> None:
        """Presenter registers its on_refresh_clicked method as the refresh callback on initialization."""
        # Act
        presenter = GitRepositoryPresenter(
            view=mock_view,
            find_git_repo_action=mock_find_action,
            get_commits_action=mock_get_commits_action,
            get_staged_file_paths_action=mock_get_staged_file_paths_action,
            commit_staging_action=mock_commit_staging_action,
            get_git_identity_action=mock_get_git_identity_action,
            save_git_identity_action=mock_save_git_identity_action,
            can_write_global_git_identity_action=mock_can_write_global_git_identity_action,
            ui_state=mock_ui_state,
            clear_doc_diffs=MagicMock(),
        )

        # Assert
        mock_view.set_refresh_callback.assert_called_once_with(presenter.on_refresh_clicked)
        mock_view.set_save_iteration_callback.assert_called_once_with(presenter.on_save_iteration_button_clicked)
        mock_view.set_history_scroll_bottom_callback.assert_called_once_with(presenter.on_history_scroll_near_bottom)

    def test_on_workbench_activated_delegates_to_refresh_repository_and_commits(
        self,
        presenter: GitRepositoryPresenter,
    ) -> None:
        """on_workbench_activated() delegates to refresh_repository_and_commits()."""
        with patch.object(presenter, "refresh_repository_and_commits") as mock_refresh:
            presenter.on_workbench_activated()

        mock_refresh.assert_called_once_with()

    def test_on_refresh_clicked_delegates_to_refresh_repository_and_commits(
        self,
        presenter: GitRepositoryPresenter,
    ) -> None:
        """on_refresh_clicked() delegates to refresh_repository_and_commits()."""
        with patch.object(presenter, "refresh_repository_and_commits") as mock_refresh:
            presenter.on_refresh_clicked()

        mock_refresh.assert_called_once_with()


class TestSaveIterationFlow:
    """Tests for save-iteration orchestration in GitRepositoryPresenter."""

    def test_on_save_iteration_requested_warns_when_no_repository(
        self,
        presenter: GitRepositoryPresenter,
        mock_ui_state: MagicMock,
    ) -> None:
        """No repository shows warning and exits early."""
        mock_ui_state.git_repository = None

        presenter.on_save_iteration_requested()

        presenter._view.show_warning_message.assert_called_once()
        presenter._get_staged_file_paths_action.execute.assert_not_called()

    def test_on_save_iteration_button_clicked_delegates_to_save_flow(
        self,
        presenter: GitRepositoryPresenter,
    ) -> None:
        """Panel save button delegates to main save flow."""

        with patch.object(presenter, "on_save_iteration_requested") as save_requested:
            presenter.on_save_iteration_button_clicked()

        save_requested.assert_called_once_with()

    def test_on_save_iteration_requested_shows_info_when_no_reviewed_files(
        self,
        presenter: GitRepositoryPresenter,
        mock_ui_state: MagicMock,
    ) -> None:
        """No reviewed files shows info and does not open dialog."""
        repo = GitRepository(name="proj", absolute_path="/home/user/proj")
        mock_ui_state.git_repository = repo
        presenter._get_staged_file_paths_action.execute.return_value.is_success = True
        presenter._get_staged_file_paths_action.execute.return_value.data = []

        presenter.on_save_iteration_requested()

        presenter._view.show_info_message.assert_called_once()
        presenter._commit_staging_action.execute.assert_not_called()

    def test_on_save_iteration_requested_commits_trimmed_message_and_refreshes(
        self,
        presenter: GitRepositoryPresenter,
        mock_ui_state: MagicMock,
    ) -> None:
        """Successful save trims message, commits, logs, then refreshes."""
        repo = GitRepository(name="proj", absolute_path="/home/user/proj")
        mock_ui_state.git_repository = repo
        presenter._get_staged_file_paths_action.execute.return_value.is_success = True
        presenter._get_staged_file_paths_action.execute.return_value.data = ["a.FCStd"]
        presenter._get_git_identity_action.execute.return_value.data = object()
        presenter._commit_staging_action.execute.return_value.is_success = True

        with (
            patch.object(presenter._view, "show_save_iteration_dialog", return_value="  message with spaces  "),
            patch.object(presenter, "refresh_repository_and_commits") as refresh,
        ):
            presenter.on_save_iteration_requested()

        presenter._commit_staging_action.execute.assert_called_once_with(repo, "message with spaces")
        refresh.assert_called_once_with()

    def test_on_save_iteration_requested_shows_error_when_commit_fails(
        self,
        presenter: GitRepositoryPresenter,
        mock_ui_state: MagicMock,
    ) -> None:
        """Failed commit shows critical message with action error."""
        repo = GitRepository(name="proj", absolute_path="/home/user/proj")
        mock_ui_state.git_repository = repo
        presenter._get_staged_file_paths_action.execute.return_value.is_success = True
        presenter._get_staged_file_paths_action.execute.return_value.data = ["a.FCStd"]
        presenter._get_git_identity_action.execute.return_value.data = object()
        presenter._commit_staging_action.execute.return_value.is_success = False
        presenter._commit_staging_action.execute.return_value.message = "git failed"

        with patch.object(presenter._view, "show_save_iteration_dialog", return_value="message"):
            presenter.on_save_iteration_requested()

        presenter._view.show_error_message.assert_called_once()


class TestConfigureAuthorFlow:
    """Tests for configure-author orchestration in GitRepositoryPresenter."""

    def test_on_configure_author_requested_warns_when_no_repository(
        self,
        presenter: GitRepositoryPresenter,
        mock_ui_state: MagicMock,
    ) -> None:
        """No repository shows warning and exits early."""
        mock_ui_state.git_repository = None

        presenter.on_configure_author_requested()

        presenter._view.show_warning_message.assert_called_once()

    def test_configure_repository_saves_identity(
        self,
        presenter: GitRepositoryPresenter,
    ) -> None:
        """Configure dialog values are saved through application action."""
        presenter._get_git_identity_action.execute.return_value = Result.success(None)
        presenter._save_git_identity_action.execute.return_value = Result.success(True)
        presenter._can_write_global_git_identity_action.execute.return_value = Result.success(True)
        mock_repo = MagicMock(spec=GitRepository)
        dialog_result = GitConfigDialogResult(
            author_name="Test User",
            author_email="test@example.com",
            should_save_globally=True,
        )

        with patch.object(presenter._view, "show_configure_author_dialog", return_value=dialog_result):
            result = presenter._configure_repository_identity(mock_repo)

        assert result is True
        presenter._save_git_identity_action.execute.assert_called_once_with(
            mock_repo,
            GitIdentity(name="Test User", email="test@example.com"),
            True,
        )
        presenter._view.show_warning_message.assert_not_called()
        presenter._view.show_error_message.assert_not_called()

    def test_configure_repository_requires_name_and_email(
        self,
        presenter: GitRepositoryPresenter,
    ) -> None:
        """Configure dialog requires both name and email."""
        presenter._get_git_identity_action.execute.return_value = Result.success(None)
        presenter._can_write_global_git_identity_action.execute.return_value = Result.success(True)
        mock_repo = MagicMock(spec=GitRepository)
        dialog_result = GitConfigDialogResult(
            author_name="",
            author_email="test@example.com",
            should_save_globally=False,
        )

        with patch.object(presenter._view, "show_configure_author_dialog", return_value=dialog_result):
            result = presenter._configure_repository_identity(mock_repo)

        assert result is False
        presenter._view.show_warning_message.assert_called_once()
        presenter._save_git_identity_action.execute.assert_not_called()


class TestCommitLoading:
    """Tests for GitRepositoryPresenter commit loading functionality."""

    def test_load_commits_calls_show_commits_on_success(
        self,
        presenter: GitRepositoryPresenter,
        mock_view: MagicMock,
        mock_get_commits_action: MagicMock,
    ) -> None:
        """_load_commits() calls show_commits with commits on success."""
        # Arrange
        commits = [
            GitCommit(
                id="a1b2c3d4e5f67890",
                message="Test commit",
                author="Test Author",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            ),
        ]
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = commits
        mock_get_commits_action.execute.return_value = mock_result

        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")

        # Act
        presenter._load_commits(repo)

        # Assert
        mock_get_commits_action.execute.assert_called_once_with(repo)
        mock_view.show_commits.assert_called_once_with(commits)

    def test_load_commits_shows_empty_list_on_failure(
        self,
        presenter: GitRepositoryPresenter,
        mock_view: MagicMock,
        mock_get_commits_action: MagicMock,
    ) -> None:
        """_load_commits() shows empty list when action fails."""
        # Arrange
        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.message = "Git error"
        mock_get_commits_action.execute.return_value = mock_result

        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")

        # Act
        presenter._load_commits(repo)

        # Assert
        mock_view.show_commits.assert_called_once_with([])

    def test_detect_git_repository_loads_commits_on_success(
        self,
        presenter: GitRepositoryPresenter,
        mock_view: MagicMock,
        mock_find_action: MagicMock,
        mock_get_commits_action: MagicMock,
        mock_ui_state: MagicMock,
    ) -> None:
        """_detect_git_repository() loads commits after detecting repository."""
        # Arrange
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")

        # Mock find action to return repo
        mock_find_result = MagicMock()
        mock_find_result.is_success = True
        mock_find_result.data = repo
        mock_find_action.execute.return_value = mock_find_result

        # Mock get commits action to return commits
        commits = [
            GitCommit(
                id="a1b2c3d",
                message="Test",
                author="Test",
                timestamp=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            )
        ]
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = commits
        mock_get_commits_action.execute.return_value = mock_commit_result

        # Act
        presenter._detect_git_repository()

        # Assert
        mock_get_commits_action.execute.assert_called_once_with(repo)
        mock_view.show_commits.assert_called_once()

    def test_on_history_scroll_near_bottom_loads_next_page(self, presenter: GitRepositoryPresenter) -> None:
        """Scroll near bottom loads next commit page with skip offset."""
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        presenter._ui_state.git_repository = repo
        presenter._active_repo_path = repo.absolute_path
        presenter._loaded_commit_count = 20
        presenter._has_more_commits = True

        commits = [
            GitCommit(
                id="z9y8x7w",
                message="Older commit",
                author="Dev",
                timestamp=datetime.fromisoformat("2024-01-10T10:30:00+00:00"),
            )
        ]
        result = MagicMock()
        result.is_success = True
        result.data = commits
        presenter._get_commits_action.execute.return_value = result

        presenter.on_history_scroll_near_bottom()

        presenter._get_commits_action.execute.assert_called_once_with(repo, limit=20, skip=20)
        presenter._view.append_commits.assert_called_once_with(commits)

    def test_on_history_scroll_near_bottom_skips_when_no_more(self, presenter: GitRepositoryPresenter) -> None:
        """Scroll near bottom does nothing when no further pages exist."""
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        presenter._ui_state.git_repository = repo
        presenter._active_repo_path = repo.absolute_path
        presenter._has_more_commits = False

        presenter.on_history_scroll_near_bottom()

        presenter._get_commits_action.execute.assert_not_called()

    def test_on_history_scroll_near_bottom_throttles_rapid_calls(self, presenter: GitRepositoryPresenter) -> None:
        """Rapid bottom-scroll callbacks are throttled to one load call."""
        repo = GitRepository(name="test_project", absolute_path="/home/user/test_project")
        presenter._ui_state.git_repository = repo
        presenter._active_repo_path = repo.absolute_path
        presenter._loaded_commit_count = 20
        presenter._has_more_commits = True

        result = MagicMock()
        result.is_success = True
        result.data = []
        presenter._get_commits_action.execute.return_value = result

        with patch("freecad.history_wb.ui.presenters.git_repository_presenter.monotonic", return_value=10.0):
            presenter.on_history_scroll_near_bottom()
            presenter.on_history_scroll_near_bottom()

        presenter._get_commits_action.execute.assert_called_once_with(repo, limit=20, skip=20)
