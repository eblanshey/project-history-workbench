# Task: Phase 2 - Loading Git Commits

## Goal
Fetch and display the last 20 Git commits in a new UI list (the "History" widget), replacing the existing snapshot list.

## Context
This is Phase 2 of the MVP implementation plan. Phase 1 established git repository detection. Phase 2 extends this to load and display git commit history. The UI will show a "History" list with commit information instead of snapshots.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| `GitCommit` model returns full message | Full message stored so tooltip can display it | Could truncate and only show first line, but then tooltip would be incomplete |
| `GitPort.get_commits` returns `list[GitCommit]` directly | More type-safe, follows existing model pattern | Could return dicts and convert in service, but adds unnecessary conversion |
| Commits displayed in same column as snapshots | The UI already has a list widget in column 1; reuse for history | Could create new widget, but MVP says "replace" |
| Presenter owns commit loading | Follows existing pattern where `GitRepositoryPresenter` owns git-related UI | Could put in separate presenter, but commits are git-related |
| Full commit message in log format | `%B` (body) included so tooltip can show complete message | `%s` only returns subject line |
| Commit message wraps within list item | List items must not expand horizontally | Could truncate long messages, but wrapping preserves information |

## Architecture Impact

### New Files/Directories

```
freecad/diff_wb/
├── domain/git/
│   └── models.py                     # MODIFY - Add GitCommit dataclass
├── infrastructure/git/
│   └── git_port_adapter.py           # MODIFY - Add get_commits implementation
├── application/actions/
│   ├── __init__.py                   # MODIFY - Export GetCommitsAction
│   └── get_commits.py                # NEW - GetCommitsAction
└── tests/
    └── unit/
        ├── domain/git/
        │   └── test_git_commit.py    # NEW - Tests for GitCommit model
        ├── infrastructure/git/
        │   └── test_git_port_adapter.py  # MODIFY - Add get_commits tests
        └── application/actions/
            └── test_get_commits.py   # NEW - Tests for GetCommitsAction
```

### Modified Files

```
freecad/diff_wb/
├── domain/git/ports.py                      # MODIFY - Add get_commits method to protocol
├── domain/git/git_service.py                # MODIFY - Add get_commits method
├── domain/git/__init__.py                   # MODIFY - Export GitCommit
├── application/di/container.py              # MODIFY - Wire GetCommitsAction
├── ui/views/diff_panel_view.py              # MODIFY - Replace snapshot list with history widget
├── ui/presenters/git_repository_presenter.py # MODIFY - Add commit loading logic
├── ui/presenters/__init__.py                # MODIFY - Export updated modules
├── ui/translation_strings.py                # MODIFY - Add History label string
└── application/actions/__init__.py          # MODIFY - Export GetCommitsAction
```

## FreeCAD Dependency
- [x] No FreeCAD required for domain/infrastructure code (pure Python)
- [x] FreeCAD required for UI integration

## Implementation Plan

### Phase 2.1: Domain Layer - GitCommit Model

**IMPORTANT:** Write tests BEFORE implementation.

- [x] Write tests for `GitCommit` model creation and property access
- [x] Update `domain/git/models.py` to add `GitCommit` dataclass:
  ```python
  @dataclass(frozen=True)
  class GitCommit:
      """A git commit representation.

      Attributes:
          id: The commit hash (full hash, caller can truncate for display)
          message: Full commit message (subject + body)
          author: Author name
          timestamp: ISO format timestamp string
      """
      id: str
      message: str  # Full message, not just subject line
      author: str
      timestamp: str  # ISO format
  ```
- [x] Update `domain/git/__init__.py` to export `GitCommit`

### Phase 2.2: Domain Layer - GitPort Protocol Update

**IMPORTANT:** Write tests BEFORE implementation.

- [x] Write tests for `GitPort.get_commits()` with fake implementation
- [x] Update `domain/git/ports.py` to add new method:
  ```python
  def get_commits(self, path: str, limit: int = 20) -> list[GitCommit]:
      """Get recent commits from git repository.

      Args:
          path: Absolute path to git repository root.
          limit: Maximum number of commits to return (default 20 for MVP).

      Returns:
          List of GitCommit objects in DESC order (newest first).
      """
      ...
  ```

### Phase 2.3: Domain Layer - GitService.get_commits

**IMPORTANT:** Write tests BEFORE implementation.

- [x] Write tests for `GitService.get_commits()` with fakes
- [x] Update `domain/git/git_service.py` to add method:
  ```python
  def get_commits(self, repo: GitRepository, limit: int = 20) -> list[GitCommit]:
      """Get recent commits from git repository.

      Args:
          repo: GitRepository to get commits from.
          limit: Maximum number of commits to return.

      Returns:
          List of GitCommit objects in DESC order.
      """
      return self._git_port.get_commits(repo.absolute_path, limit)
  ```

### Phase 2.4: Infrastructure Layer - GitPortAdapter.get_commits

**IMPORTANT:** Write tests BEFORE implementation.

- [x] Write tests for `GitPortAdapter.get_commits()` using subprocess mocking
- [x] Update `infrastructure/git/git_port_adapter.py` to add:
  ```python
  def get_commits(self, path: str, limit: int = 20) -> list[GitCommit]:
      """Get recent commits using git CLI.

      Uses 'git log' with format: %H|%B|%an|%aI
      - %H: full commit hash
      - %B: full message (subject + body, separated by newline if body exists)
      - %an: author name
      - %aI: author date in ISO 8601 format

      Returns commits in DESC order (newest first).
      """
      # Note: %B includes full body, enabling tooltip with complete message
  ```

### Phase 2.5: Application Layer - GetCommitsAction

**IMPORTANT:** Write tests BEFORE implementation.

- [x] Write tests for `GetCommitsAction` with fakes
- [x] Create `application/actions/get_commits.py`:
  ```python
  class GetCommitsAction:
      """Get recent git commits from a repository."""

      def __init__(
          self,
          git_service: GitService,
      ) -> None:
          self._git_service = git_service

      def execute(self, repo: GitRepository, limit: int = 20) -> Result[list[GitCommit]]:
          """Get recent commits.

          Returns:
              Result with list of GitCommit on success, or failure result.
          """
          if repo is None:
              return Result.failure("No git repository available")

          commits = self._git_service.get_commits(repo, limit)
  return Result.success(commits)
   ```
- [x] Update `application/actions/__init__.py` to export `GetCommitsAction`

### Phase 2.6: Container Wiring

**IMPORTANT:** Write tests BEFORE implementation.

- [x] Write tests for container wiring
- [x] Update `application/di/container.py`:
  ```python
  @dataclass
  class ApplicationContainer:
      # ... existing fields ...

      # New field
      get_commits_action: GetCommitsAction
  ```
- [x] Update `create_application_container()` to wire:
  ```python
  get_commits_action = GetCommitsAction(git_service=git_service)
  ```

### Phase 2.7: Translation Strings

- [x] Update `ui/translation_strings.py` to add:
  ```python
  HISTORY_LABEL = "History"
  """Label for the history/commit list widget.

  No placeholders. This is a static label.
  """
  ```

### Phase 2.8: UI Layer - DiffPanelView History Widget

This is the core UI change. Per the MVP spec:
- Replace "Snapshots" label with "History" label
- The commit list widget displays: 7 char hash, author, timestamp on line 1; first line of message on line 2
- Tooltip shows full commit message
- No automatic selection on load
- First line of commit message must wrap within the list item (no horizontal expansion)

**IMPORTANT:** Write tests BEFORE implementation.

- [x] Write tests for `DiffPanelView.show_commits()` with mocked `GitCommit` objects
- [x] Update `ui/views/diff_panel_view.py`:
  - Add `show_commits(commits: list[GitCommit])` method
  - Create `_CommitListItemDelegate` for commit display (similar to snapshot delegate)
  - Modify `_setup_ui()`:
    - Change `snapshot_placeholder` text from "Snapshots" to "History"
    - Update widget variable names conceptually (snapshot_list → history_list) but preserve functionality
  - The commit display format in list:
    ```
    [7-char hash] [author] [timestamp]
    [first line of commit message (wraps if needed)]
    ```
  - Example:
    ```
    a1b2c3d John Doe 2024-01-15 10:30
    Add new feature for snapshot comparison
    ```
  - Use `QListWidgetItem.setText()` with `\n` for two-line display
  - **Text wrapping**: The first line of the commit message must wrap within the list item width. Use `QListWidgetItem.setText()` with Qt's internal text wrapping, or set `textAlignment` and ensure the list widget has `horizontalScrollBarPolicy` set to `Qt.ScrollBarAlwaysOff` to prevent horizontal expansion.
  - Tooltip should show **full commit message** (not just first line)
  - No selection on load (clear any pre-existing selection)

### Phase 2.9: UI Layer - GitRepositoryPresenter Update

**IMPORTANT:** Write tests BEFORE implementation.

- [x] Write tests for commit loading with fake action
- [x] Update `ui/presenters/git_repository_presenter.py`:
  ```python
  class GitRepositoryPresenter:
      def __init__(
          self,
          view: DiffPanelView,
          find_git_repo_action: FindActiveGitRepositoryAction,
          get_commits_action: GetCommitsAction,  # NEW PARAMETER
          application_state: ApplicationState,
      ) -> None:
          # ... existing init ...
          self._get_commits_action = get_commits_action

      def _detect_git_repository(self) -> None:
          """Detect git repository and update UI and application state."""
          # ... existing detection logic ...

          # After detecting repository, load commits
          if repo is not None:
              self._load_commits(repo)

      def _load_commits(self, repo: GitRepository) -> None:
          """Load and display commits for the repository."""
          result = self._get_commits_action.execute(repo)

          if result.is_success:
              commits = result.data
              self._view.show_commits(commits)
          else:
              # Show empty list on failure
              self._view.show_commits([])
              Log.warning(f"Failed to load commits: {result.message}")
  ```

### Phase 2.10: Integration

- [x] Update `entrypoints/workbench.py` to pass `get_commits_action` to `GitRepositoryPresenter`:
  ```python
  git_repository_presenter = GitRepositoryPresenter(
      view=panel,
      find_git_repo_action=_container.find_active_git_repository_action,
      get_commits_action=_container.get_commits_action,  # NEW
      application_state=_container.application_state,
  )
  ```

## Test Strategy

### Unit Tests (No FreeCAD)
- `GitCommit` model creation and property access
- `GitPort.get_commits()` protocol with fake implementation
- `GitService.get_commits()` with fake GitPort
- `GitPortAdapter.get_commits()` with subprocess mocking
- `GetCommitsAction` with fake GitService
- `DiffPanelView.show_commits()` with mocked GitCommit objects
- `GitRepositoryPresenter._load_commits()` with fake action and view
- Container wiring with mocked dependencies

### Integration Tests (FreeCAD Required)
- Manual testing only - user verifies commit display in UI

## Manual Test Cases

### docs/manual-testing/git_repository_tests.md

#### Git Repository Detection
- **Test Case 1 - No Files Open**: Ensure no documents are open, switch to Diff Workbench, verify "No git repository detected" displays in gray italic, refresh button visible.
- **Test Case 2 - Files Open but No Git Repository**: Create/save document outside git repo, switch to Diff Workbench, verify "No git repository detected" displays.
- **Test Case 3 - Files Open with Git Repository**: Open document within git repo, switch to Diff Workbench, verify repository name and path display in bold above "History" label.
- **Test Case 4 - Multiple Git Repositories**: Open documents from different git repos, ensure one is active, switch to Diff Workbench, verify only active document's repository displays.
- **Refresh Button Verification**: After any detection test, switch workbenches and back, click refresh button, verify detection re-triggers and displays same result.

#### Git Commits (History Widget)
- **Commit List Display**: Open a document in a git repository with existing commits. Verify the "History" label appears above a list showing commit hash (7 chars), author, timestamp, and first line of message for each commit. Verify no commit is auto-selected. Hover over a commit to verify tooltip displays the full commit message.

## Findings & Notes

### Git Log Format
The adapter will use `git log --format="%H|%B|%an|%aI" -n <limit>` which provides:
- `%H`: Full commit hash
- `%B`: Full message (subject + body), enabling complete tooltip
- `%an`: Author name
- `%aI`: Author date in ISO 8601 format

**Note:** We use `%B` (full body) instead of `%s` (subject only) because the tooltip needs to show the complete commit message.

### Sorting
Commits are returned in DESC order (newest first) by the adapter. This matches the existing snapshot sorting pattern.

### Timestamp Format
Git's `%aI` format returns ISO 8601 format (e.g., `2024-01-15T10:30:00+00:00`), which can be parsed directly by `datetime.fromisoformat()`.

### MVP Scope
Phase 2 does NOT include:
- Working Tree and Staging items (Phase 3)
- Click handlers for commits (future phases)
- Commit details view