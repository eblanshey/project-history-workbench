# Task: Phase 8 - Commit Staging Implementation

## Goal
Implement the git commit functionality that allows users to commit staged files through a UI dialog, with proper feedback and commit list refresh.

## Context
Phase 8 of the MVP implementation focuses on completing the git workflow by enabling users to commit their staged changes. This follows Phase 7 (Staging Diff) where users can stage documents and view staging diffs. The user needs a toolbar button/command to initiate a commit, a dialog to enter a commit message, and feedback upon success.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use QInputDialog.getText() for commit dialog | Simple, native Qt dialog for single-line text input | Custom QDialog with more control, but adds complexity |
| Store commit action in application/actions/commands/ | Follows existing pattern from take_snapshot.py and compare_snapshots.py | Directly in entrypoints/commands.py, but violates separation of concerns |
| Reload commits via GitRepositoryPresenter.on_refresh_clicked() | Reuses existing public refresh logic, maintains encapsulation | Making _load_commits() public, but exposes internal implementation |
| Access UIState via UIRegistry | Ensures commands access same state as presenters | Creating new UIState instance in command, but breaks state consistency |
| Add GitRepositoryPresenter to UIRegistry | Allows commands to trigger refresh after commit | Creating separate registry, but adds unnecessary complexity |

## Architecture Impact
- **freecad/diff_wb/domain/git/ports.py**: Add `commit()` method signature to GitPort protocol
- **freecad/diff_wb/infrastructure/git/git_port_adapter.py**: Implement `commit()` using git CLI
- **freecad/diff_wb/domain/git/git_service.py**: Add `commit()` wrapper method
- **freecad/diff_wb/application/actions/commands/commit_staging.py**: New action file
- **freecad/diff_wb/entrypoints/commands.py**: New `_CommitCommand` class, register in `register_commands()`
- **freecad/diff_wb/ui/state.py**: Already has `git_repository` field for UIState
- **freecad/diff_wb/ui/registry.py**: Add `ui_state` and `git_repository_presenter` properties with registration methods
- **freecad/diff_wb/ui/composer.py**: Register UIState and GitRepositoryPresenter in registry
- **freecad/diff_wb/application/di/container.py**: Add `commit_staging_action` to container
- **tests/fakes/fake_git_port.py**: Add `commit()` method to FakeGitPort

## FreeCAD Dependency
- [x] No FreeCAD required (pure code path)
- [ ] FreeCAD required (follow exploration phase)

**Rationale**: This is pure code implementation. The git operations use subprocess calls (already established in git_port_adapter.py), and the UI components use standard Qt widgets (QMessageBox). No API exploration needed as we're following established patterns.

## Implementation Plan

### Phase 1: Domain Layer - GitPort Protocol Extension
- [x] Write tests for GitPort.commit() method
- [x] Add `commit(git_root: str, message: str) -> bool` to GitPort protocol in `freecad/diff_wb/domain/git/ports.py`

The protocol should define:
```python
def commit(self, git_root: str, message: str) -> bool:
    """Commit staged changes in the git repository.
    
    Args:
        git_root: Absolute path to git repository root.
        message: Commit message text.
    
    Returns:
        True if commit succeeded, False otherwise.
    """
    ...
```

### Phase 2: Infrastructure Layer - GitPortAdapter Implementation
- [x] Write tests for GitPortAdapter.commit()
- [x] Implement `commit()` in `freecad/diff_wb/infrastructure/git/git_port_adapter.py`

Implementation approach:
```python
def commit(self, git_root: str, message: str) -> bool:
    """Commit staged changes using git CLI.
    
    Uses 'git commit -m <message>' command.
    
    Args:
        git_root: Absolute path to git repository root.
        message: Commit message text.
    
    Returns:
        True if git commit succeeded, False otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            Log.debug(f"Commit successful: {result.stdout.strip()}")
            return True
        Log.warning(f"Git commit failed: {result.stderr.strip()}")
        return False
    except subprocess.TimeoutExpired:
        Log.warning("Git commit command timed out")
        return False
    except FileNotFoundError:
        Log.warning("Git command not found")
        return False
```

### Phase 3: Domain Service - GitService Extension
- [x] Write tests for GitService.commit()
- [x] Add `commit(repo: GitRepository, message: str) -> bool` to `freecad/diff_wb/domain/git/git_service.py`

Implementation approach:
```python
def commit(self, repo: GitRepository, message: str) -> bool:
    """Commit staged changes in the repository.
    
    Args:
        repo: GitRepository to commit in.
        message: Commit message text.
    
    Returns:
        True if commit succeeded, False otherwise.
    """
    return self._git_port.commit(repo.absolute_path, message)
```

### Phase 4: Application Layer - CommitStagingAction
- [x] Write tests for CommitStagingAction
- [x] Create `freecad/diff_wb/application/actions/commands/commit_staging.py`

File structure following existing patterns:
```python
"""File responsibility: Commit staging action orchestration."""

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ..result_models import Result


class CommitStagingAction:
    """Action to commit staged changes to git repository.
    
    This action orchestrates the commit workflow by calling GitService
    to perform the actual git commit operation.
    """
    
    def __init__(self, git_service: GitService) -> None:
        """Initialize with required dependencies.
        
        Args:
            git_service: Service for git operations.
        """
        self._git_service = git_service
    
    def execute(self, repo: GitRepository, message: str) -> Result:
        """Commit staged changes.
        
        Args:
            repo: GitRepository to commit in. Must have staged files.
            message: Commit message text.
        
        Returns:
            Result with success status and optional error message.
        """
        # Execute commit
        success = self._git_service.commit(repo, message)
        
        if success:
            return Result.success(True)
        return Result.failure("Git commit failed")
```

**Note**: Input validation (empty message) is handled in the command layer (`_CommitCommand.Activated()`), not here. The action assumes valid input — this follows the existing pattern where `TakeSnapshotAction` does not validate its `name` parameter.

### Phase 5: Dependency Injection - Container Updates
- [x] Update `ApplicationContainer` dataclass in `freecad/diff_wb/application/di/container.py`
- [x] Wire up `commit_staging_action` in `create_application_container()`

Add to dataclass:
```python
commit_staging_action: CommitStagingAction
```

Add to factory function:
```python
from ..actions.commands.commit_staging import CommitStagingAction

# After creating other actions
commit_staging_action = CommitStagingAction(git_service=git_service)

return ApplicationContainer(
    # ... existing fields ...
    commit_staging_action=commit_staging_action,
)
```

### Phase 6: UI Registry - Add UIState and GitRepositoryPresenter
- [x] Update `freecad/diff_wb/ui/registry.py` to include ui_state and git_repository_presenter
- [x] Update `freecad/diff_wb/ui/composer.py` to register UIState and GitRepositoryPresenter

In registry.py:
```python
if TYPE_CHECKING:
    from .presenters.diff_presenter import DiffPresenter
    from .presenters.snapshot_presenter import SnapshotPresenter
    from .presenters.git_repository_presenter import GitRepositoryPresenter
    from .state import UIState  # Add

class UIRegistry:
    def __init__(self) -> None:
        self._snapshot_presenter: SnapshotPresenter | None = None
        self._diff_presenter: DiffPresenter | None = None
        self._git_repository_presenter: GitRepositoryPresenter | None = None
        self._ui_state: UIState | None = None  # Add
    
    @property
    def ui_state(self) -> "UIState":
        """Get UI state.
        
        Raises:
            RuntimeError: If not initialized
        """
        if self._ui_state is None:
            raise RuntimeError("UI state not initialized. Workbench must be activated first.")
        return self._ui_state
    
    @property
    def git_repository_presenter(self) -> "GitRepositoryPresenter":
        """Get git repository presenter.
        
        Raises:
            RuntimeError: If not initialized
        """
        if self._git_repository_presenter is None:
            raise RuntimeError("Git repository presenter not initialized.")
        return self._git_repository_presenter
    
    def register_ui_state(self, state: "UIState") -> None:
        """Register UI state."""
        self._ui_state = state
    
    def register_git_repository_presenter(self, presenter: "GitRepositoryPresenter") -> None:
        """Register git repository presenter."""
        self._git_repository_presenter = presenter
```

In composer.py:
```python
# After creating UI state
ui_state = UIState(git_repository=None)
ui_registry.register_ui_state(ui_state)  # Add this line

# ... (rest of composer code)

# Register git repo presenter
git_repo_presenter = GitRepositoryPresenter(
    view=view,
    find_git_repo_action=container.find_active_git_repository_action,
    get_commits_action=container.get_commits_action,
    ui_state=ui_state,
)
ui_registry.register_git_repository_presenter(git_repo_presenter)  # Add this line
# Trigger git repository detection on workbench activation
git_repo_presenter.on_workbench_activated()
```

### Phase 7: UI Command - CommitCommand Entry Point
- [x] Write tests for _CommitCommand
- [x] Add `_CommitCommand` class to `freecad/diff_wb/entrypoints/commands.py`
- [x] Add command registration in `register_commands()`

Implementation approach - accessing UIState via ui_registry:
```python
class _CommitCommand:
    """Command to commit staged changes."""
    
    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Commit",
            "ToolTip": "Commit staged changes to git",
            "Pixmap": os.path.join(ICONPATH, "Commit.svg"),
        }
    
    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True  # Always enabled; validation happens in Activated()
    
    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from PySide6.QtWidgets import QMessageBox, QInputDialog
        
        from .._container import get_container
        from ..ui.registry import ui_registry
        
        container = get_container()
        
        # Check if we have a git repository via UIState in registry
        repo = ui_registry.ui_state.git_repository
        
        if repo is None:
            QMessageBox.warning(
                None,  # type: ignore[arg-type]
                "No Repository",
                "No git repository detected. Please open a document from a git repository.",
            )
            return
        
        # Show commit dialog
        message, ok = QInputDialog.getText(
            None,
            "Git Commit",
            "Enter commit message:",
            text=""
        )
        
        if not ok:
            # User cancelled
            return
        
        if not message or not message.strip():
            QMessageBox.warning(
                None,  # type: ignore[arg-type]
                "Empty Message",
                "Commit message cannot be empty",
            )
            return
        
        # Execute commit action
        result = container.commit_staging_action.execute(repo, message.strip())
        
        if result.is_success:
            container.log("Commit successful")
            # Reload commits by triggering refresh
            ui_registry.git_repository_presenter.on_refresh_clicked()
        else:
            QMessageBox.critical(
                None,  # type: ignore[arg-type]
                "Commit Failed",
                result.message or "Git commit failed",
            )
```

Register the command in `register_commands()`:
```python
def register_commands() -> None:
    """Register the Diff Workbench commands with FreeCAD."""
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand("DiffTakeSnapshot", _TakeSnapshotCommand())
    Gui.addCommand("DiffCompare", _CompareCommand())
    Gui.addCommand("DiffSwapColumns", _SwapColumnsCommand())
    Gui.addCommand("DiffCommit", _CommitCommand())  # Add
```

## Test Strategy
- **Unit tests**: For all new classes using fakes/mocks
  - [x] `tests/unit/infrastructure/git/test_git_port_adapter_commit.py`: Test subprocess invocation, error handling
  - [x] `tests/unit/domain/git/test_git_service_commit.py`: Test delegation to port
  - [x] `tests/unit/application/actions/commands/test_commit_staging.py`: Test action orchestration
  - [x] `tests/unit/entrypoints/test_commit_command.py`: Test command UI flow (may need GUI test setup)
  - [x] `tests/unit/ui/test_ui_registry.py`: Test UIState and GitRepositoryPresenter access via registry
- **FakeGitPort updates**: Add `commit(git_root, message) -> bool` method with `_fail_commit` flag to `tests/fakes/fake_git_port.py`
  - [x] All tests pass (968 passed, 24 skipped)

## Findings & Notes

1. **UIState Access Pattern**: Updated to register UIState in UIRegistry instead of creating new instances. This ensures commands access the same state that presenters use.

2. **GitRepositoryPresenter Access**: Added to UIRegistry to allow commands to trigger `on_refresh_clicked()` for reload after commit. Follows existing pattern for other presenters.

3. **Dialog Implementation**: Using QInputDialog.getText() for simple single-line commit message input. If multi-line support is needed later, can upgrade to custom QDialog.

4. **Error Handling**: Git commit can fail for various reasons (no staged files, merge conflicts, etc.). The implementation handles these gracefully and shows appropriate error messages.

5. **Refresh Mechanism**: Using existing public `on_refresh_clicked()` method instead of making `_load_commits()` public. This maintains proper encapsulation while achieving the same result.

6. **Input Validation**: Empty message validation is handled only in the command layer (`_CommitCommand.Activated()`), not in the action. This follows the existing pattern where actions assume valid input and commands handle user-facing validation.

7. **Icon**: `freecad/diff_wb/resources/icons/Commit.svg` already exists with the correct git branch/commit design. No icon work needed.

8. **FakeGitPort**: Added `commit(git_root, message) -> bool` method with `_fail_commit` flag to support testing of commit functionality.
