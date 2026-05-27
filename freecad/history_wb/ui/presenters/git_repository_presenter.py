# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Presents git repository information and manages commit loading in the UI.
"""Git repository presenter for UI layer."""

from collections.abc import Callable
from time import monotonic

from freecad.history_wb.application.actions.can_write_global_git_identity import (
    CanWriteGlobalGitIdentityAction,
)
from freecad.history_wb.application.actions.commit_staging import CommitStagingAction
from freecad.history_wb.application.actions.find_active_git_repository import (
    FindActiveGitRepositoryAction,
)
from freecad.history_wb.application.actions.get_git_identity import GetGitIdentityAction
from freecad.history_wb.application.actions.get_staged_file_paths import GetStagedFilePathsAction
from freecad.history_wb.application.actions.get_commits import GetCommitsAction
from freecad.history_wb.application.actions.save_git_identity import SaveGitIdentityAction
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.ui.state import UIState
from freecad.history_wb.ui.views.diff_panel_view import DiffPanelView
from freecad.history_wb.ui.views.models import GitConfigDialogResult
from freecad.history_wb.utils import Log, translate


class GitRepositoryPresenter:
    """Handles git repository detection and UI display.

    This presenter is responsible for:
    1. Detecting the active git repository when the workbench is activated
    2. Updating the UI state with the detected repository
    3. Displaying the repository information in the view
    4. Loading and displaying commits for the repository

    Attributes:
        _view: The DiffPanelView instance for displaying repository info.
        _find_git_repo_action: The action for finding the active git repository.
        _get_commits_action: The action for getting git commits.
        _ui_state: The UI state holder for storing repository.
    """

    def __init__(
        self,
        view: DiffPanelView,
        find_git_repo_action: FindActiveGitRepositoryAction,
        get_commits_action: GetCommitsAction,
        get_staged_file_paths_action: GetStagedFilePathsAction,
        commit_staging_action: CommitStagingAction,
        get_git_identity_action: GetGitIdentityAction,
        save_git_identity_action: SaveGitIdentityAction,
        can_write_global_git_identity_action: CanWriteGlobalGitIdentityAction,
        ui_state: UIState,
        clear_doc_diffs: Callable[[], None],
    ) -> None:
        """Initialize the presenter with required dependencies.

        Args:
            view: The DiffPanelView instance for displaying repository info.
            find_git_repo_action: The action for finding the active git repository.
            get_commits_action: The action for getting git commits.
            ui_state: The UI state holder for storing repository.
        """
        self._view = view
        self._find_git_repo_action = find_git_repo_action
        self._get_commits_action = get_commits_action
        self._get_staged_file_paths_action = get_staged_file_paths_action
        self._commit_staging_action = commit_staging_action
        self._get_git_identity_action = get_git_identity_action
        self._save_git_identity_action = save_git_identity_action
        self._can_write_global_git_identity_action = can_write_global_git_identity_action
        self._ui_state = ui_state
        self._clear_doc_diffs = clear_doc_diffs
        self._page_size = 20
        self._loaded_commit_count = 0
        self._has_more_commits = False
        self._is_loading_commits = False
        self._active_repo_path: str | None = None
        self._last_scroll_load_ts = 0.0
        self._scroll_load_interval_seconds = 0.2
        self._view.set_refresh_callback(self.on_refresh_clicked)
        self._view.set_save_iteration_callback(self.on_save_iteration_button_clicked)
        self._view.set_history_scroll_bottom_callback(self.on_history_scroll_near_bottom)

    def on_workbench_activated(self) -> None:
        """Detect and display git repository when workbench activates.

        This method is called when the workbench is activated to detect
        the current git repository and display it in the UI.
        """
        self.refresh_repository_and_commits()

    def refresh_repository_and_commits(self) -> None:
        """Refresh repository detection and reload commit list.

        This method provides a UI-agnostic entry point for any caller
        that needs to re-detect the current repository, update UI state,
        and repopulate commits in the view.
        """
        self._detect_git_repository()

    def on_refresh_clicked(self) -> None:
        """Re-detect and display git repository when refresh is clicked."""
        self.refresh_repository_and_commits()

    def on_save_iteration_requested(self) -> None:
        """Execute save-iteration flow from toolbar or panel button."""
        repo = self._ui_state.git_repository

        if repo is None:
            self._view.show_warning_message(
                translate("History", "No Project"),
                translate("History", "No project detected. Please open a document from a project."),
            )
            return

        staged_result = self._get_staged_file_paths_action.execute(repo)
        if not staged_result.is_success or not staged_result.data:
            self._view.show_info_message(
                translate("History", "No Reviewed Files"),
                translate("History", "There are no reviewed files to save."),
            )
            return

        if self._identity_missing_after_configuration(repo):
            return

        commit_message = self._view.show_save_iteration_dialog()
        if commit_message is None:
            return

        trimmed_message = commit_message.strip()
        if not trimmed_message:
            self._view.show_warning_message(
                translate("History", "Empty Notes"),
                translate("History", "Iteration notes cannot be empty"),
            )
            return

        result = self._commit_staging_action.execute(repo, trimmed_message)
        if result.is_success:
            Log.info("Commit successful")
            self.refresh_repository_and_commits()
            return

        self._view.show_error_message(
            translate("History", "Save Iteration Failed"),
            result.message or translate("History", "Git commit failed"),
        )

    def on_save_iteration_button_clicked(self) -> None:
        """Handle save-iteration button click by delegating to command path."""
        self.on_save_iteration_requested()

    def on_configure_author_requested(self) -> None:
        """Open author configuration flow from toolbar command."""
        repo = self._ui_state.git_repository
        if repo is None:
            self._view.show_warning_message(
                translate("History", "No Project"),
                translate("History", "No project detected. Please open a document from a project."),
            )
            return

        self._configure_repository_identity(repo)

    def _identity_missing_after_configuration(
        self,
        repo: GitRepository,
    ) -> bool:
        """Return whether git identity is still missing after configuration attempt."""
        identity_result = self._get_git_identity_action.execute(repo)
        if identity_result.data is not None:
            return False

        return not self._configure_repository_identity(repo)

    def _configure_repository_identity(self, repo: GitRepository) -> bool:
        """Show git config dialog and save identity for repository."""
        from freecad.history_wb.domain.git.models import GitIdentity

        retry_message: str | None = None
        initial_values = self._configured_identity_dialog_values(repo)
        global_config_writable = self._can_write_global_identity()
        while True:
            dialog_result = self._view.show_configure_author_dialog(
                message=retry_message,
                initial_values=initial_values,
                global_config_writable=global_config_writable,
            )
            if dialog_result is None:
                return False

            if not dialog_result.author_name or not dialog_result.author_email:
                self._view.show_warning_message(
                    translate("History", "Save Iteration Failed"),
                    translate("History", "Name and email are required to save iteration"),
                )
                return False

            save_result = self._save_git_identity_action.execute(
                repo,
                GitIdentity(name=dialog_result.author_name, email=dialog_result.author_email),
                dialog_result.should_save_globally,
            )
            if save_result.is_success:
                return True

            if not dialog_result.should_save_globally:
                self._view.show_error_message(
                    translate("History", "Save Iteration Failed"),
                    translate("History", "Git identity could not be saved"),
                )
                return False

            retry_message = translate(
                "History",
                "Could not save git identity for all projects. "
                "Uncheck the global option to save it only for this project.",
            )
            initial_values = dialog_result

    def _can_write_global_identity(self) -> bool:
        """Return whether global git identity config can be written."""
        result = self._can_write_global_git_identity_action.execute()
        if not result.is_success:
            return False
        return bool(result.data)

    def _configured_identity_dialog_values(
        self,
        repo: GitRepository,
    ) -> GitConfigDialogResult | None:
        """Return existing git identity as dialog defaults when configured."""
        identity_result = self._get_git_identity_action.execute(repo)
        identity = identity_result.data
        if identity is None:
            return None
        return GitConfigDialogResult(
            author_name=identity.name,
            author_email=identity.email,
            should_save_globally=False,
        )

    def _detect_git_repository(self) -> None:
        """Detect git repository and update UI and application state.

        This protected method encapsulates the common logic for git repository
        detection used by both workbench activation and refresh button clicks.
        """
        result = self._find_git_repo_action.execute()

        if result.is_success:
            repo = result.data
            self._ui_state.git_repository = repo
            self._view.show_repository(repo)
            self._reset_commit_pagination(repo)

            # After detecting repository, load commits
            if repo is not None:
                self._load_initial_commits(repo)
        else:
            self._ui_state.git_repository = None
            self._reset_commit_pagination(None)
            self._view.show_repository(None)
            self._view.show_commits([], show_special_items=False)
            self._clear_doc_diffs()
            Log.info(f"Git detection failed: {result.message}")

    def _load_initial_commits(self, repo: GitRepository) -> None:
        """Load first commit page and replace list content.

        Args:
            repo: The GitRepository to load commits from.
        """
        if self._is_loading_commits:
            return
        self._is_loading_commits = True
        result = self._get_commits_action.execute(repo)
        self._is_loading_commits = False

        if result.is_success:
            commits = result.data
            self._loaded_commit_count = len(commits)
            self._has_more_commits = len(commits) == self._page_size
            self._clear_doc_diffs()
            self._view.show_commits(commits)
        else:
            self._loaded_commit_count = 0
            self._has_more_commits = False
            self._clear_doc_diffs()
            # Show empty list on failure
            self._view.show_commits([])
            Log.warning(f"Failed to load commits: {result.message}")

    def _load_commits(self, repo: GitRepository) -> None:
        """Backward-compatible wrapper for tests and callers."""
        self._load_initial_commits(repo)

    def on_history_scroll_near_bottom(self) -> None:
        """Load next commit page when history scroll reaches bottom area."""
        now = monotonic()
        if now - self._last_scroll_load_ts < self._scroll_load_interval_seconds:
            return

        repo = self._ui_state.git_repository
        if repo is None:
            return
        if self._active_repo_path != repo.absolute_path:
            return
        if self._is_loading_commits or not self._has_more_commits:
            return

        self._last_scroll_load_ts = now
        self._is_loading_commits = True
        result = self._get_commits_action.execute(
            repo,
            limit=self._page_size,
            skip=self._loaded_commit_count,
        )
        self._is_loading_commits = False

        if not result.is_success:
            self._has_more_commits = False
            Log.warning(f"Failed to load more commits: {result.message}")
            return

        commits = result.data
        if not commits:
            self._has_more_commits = False
            return

        self._view.append_commits(commits)
        self._loaded_commit_count += len(commits)
        self._has_more_commits = len(commits) == self._page_size

    def _reset_commit_pagination(self, repo: GitRepository | None) -> None:
        """Reset pagination state for current repository."""
        self._loaded_commit_count = 0
        self._has_more_commits = repo is not None
        self._is_loading_commits = False
        self._active_repo_path = repo.absolute_path if repo is not None else None
        self._last_scroll_load_ts = 0.0
