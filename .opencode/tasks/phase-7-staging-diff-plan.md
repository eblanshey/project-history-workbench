# Task: Phase 7 - Staging Diff

## Goal

Display the diff between staged files (index) and the last commit (HEAD), showing what changes are ready to be committed. When the user selects "Staging" from the history list, they should see what differences exist between what's currently staged and what exists in HEAD.

## Context

This is Phase 7 of the MVP implementation plan (see `docs/MVP-Implementation.md`). Phase 6 implemented staging files to git. Phase 7 implements viewing what changes are staged - showing the diff between what's in the staging area (index) vs HEAD.

**Key constraints:**
- Domain layer must remain FreeCAD-independent (pure Python)
- All actions return `Result` type with `is_success`, `data`, `message`
- Dependencies flow inward (UI → Application → Domain → Infrastructure)

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| `get_staged_paths` filters for `.FCStd` only | MVP scope - only FreeCAD documents are relevant | Returning all staged files - rejected as unnecessary complexity |
| `get_file_contents` returns None on error | Graceful degradation - view can handle missing files with warnings | Raising exception - rejected as too disruptive to UI |
| Refactor `from_yaml` to take string | Enables loading from git output directly without temp files | Keeping only file-based - would require temp file workaround |
| Missing index snapshot creates flat warning item | Per MVP spec: "create a one-level, flat item for that diff with a Warning icon" | Creating a DiffResult placeholder - rejected as not per spec |
| Sort DiffTreePresentation by git_path at end of present_diffs | Consistent ordering makes UI predictable, applies to all diff types | No sorting - rejected as confusing UX |
| `get_snapshot_yaml_path_for_document` returns yaml path | Single helper serves both StageDocumentsAction and CreateDocumentSnapshotForCommitAction | Having two helpers - rejected per user request |

## Architecture Impact

**Modules affected:**
- `domain/git/ports.py` - Add `get_staged_paths` and `get_file_contents` to GitPort protocol
- `domain/git/git_service.py` - Add `get_staged_files` and `get_file_contents` methods
- `infrastructure/git/git_port_adapter.py` - Implement new port methods via git CLI
- `infrastructure/persistence/snapshot_yaml.py` - Refactor `from_yaml` to take string, create `from_yaml_file`
- `domain/snapshots/__init__.py` - Update `get_snapshot_directory_for_document` to return yaml path
- `application/actions/get_staged_file_paths.py` - NEW action for getting staged FCStd paths
- `application/actions/stage_documents.py` - Update to use new helper signature
- `application/actions/create_document_snapshot_commit.py` - Implement actual snapshot loading from git
- `application/di/container.py` - Wire new action
- `ui/presenters/diff_presenter.py` - Implement `_on_staging_selected` orchestration and sorting in `present_diffs`
- `ui/composer.py` - Wire new action to DiffPresenter

**Public interfaces:**
- `GitPort.get_staged_paths(git_root) -> list[str]` - NEW port method
- `GitPort.get_file_contents(git_root, commit, git_path) -> str|None` - NEW port method
- `GitService.get_staged_files(repo) -> list[str]` - NEW service method
- `GitService.get_file_contents(repo, commit, git_path) -> str|None` - NEW service method
- `SnapshotYamlSerializer.from_yaml(yaml_string) -> Snapshot` - NEW (refactored from file-based)
- `SnapshotYamlSerializer.from_yaml_file(path) -> Snapshot` - RENAMED from original `from_yaml`
- `GetStagedFilePathsAction.execute(repo) -> Result` - NEW action
- `get_snapshot_yaml_path_for_document(document_path: str) -> Path` - RENAMED and returns yaml path

## FreeCAD Dependency

- [x] No FreeCAD required (pure code for GitPort/GitService/SnapshotYamlSerializer/actions)
- [ ] FreeCAD required (DiffPresenter and view use FreeCAD Qt widgets)

**Note:** Tests for domain/infrastructure/application layers will use fakes/mocks. UI component testing is manual only.

## Implementation Plan

**IMPORTANT:** For each phase, ALWAYS write test steps BEFORE implementation steps to follow TDD principles.

### Phase 1: Domain Layer - GitPort and GitService Updates

#### Task 1.1: Write tests for `get_staged_paths` in GitPortAdapter

Create `tests/unit/infrastructure/git/test_git_port_adapter.py` (if not exists) or add tests:

```python
def test_get_staged_paths_returns_staged_fcstd_files():
    # Given a git repo with a staged .FCStd file
    # When get_staged_paths is called
    # Then it returns the relative path of the staged file

def test_get_staged_paths_filters_non_fcstd_files():
    # Given a git repo with staged .txt and .FCStd files
    # When get_staged_paths is called
    # Then only .FCStd files are returned

def test_get_staged_paths_returns_empty_when_nothing_staged():
    # Given a git repo with no staged files
    # When get_staged_paths is called
    # Then it returns an empty list

def test_get_staged_paths_ignores_modified_not_staged():
    # Given a git repo with modified but unstaged files
    # When get_staged_paths is called
    # Then those files are not returned
```

#### Task 1.2: Write tests for `get_file_contents` in GitPortAdapter

```python
def test_get_file_contents_from_index():
    # Given a git repo with a staged file
    # When get_file_contents is called with commit=None
    # Then it returns the file contents from the index

def test_get_file_contents_from_commit():
    # Given a git repo with a committed file
    # When get_file_contents is called with a valid commit hash
    # Then it returns the file contents from that commit

def test_get_file_contents_returns_none_for_nonexistent_file():
    # Given a valid git repo
    # When get_file_contents is called for a nonexistent file
    # Then it returns None

def test_get_file_contents_returns_none_for_invalid_commit():
    # Given a valid git repo
    # When get_file_contents is called with an invalid commit
    # Then it returns None
```

#### Task 1.3: Add `get_staged_paths` and `get_file_contents` to GitPort protocol

In `domain/git/ports.py`, add to `GitPort`:

```python
def get_staged_paths(self, git_root: str) -> list[str]:
    """Get list of staged file paths (relative from git root).

    Filters for FCStd files only (files with .FCStd extension).

    Args:
        git_root: Absolute path to git repository root.

    Returns:
        List of relative paths (from git root) that are staged.
        Empty list if no FCStd files are staged or not a git repo.
    """
    ...

def get_file_contents(self, git_root: str, commit: str | None, git_path: str) -> str | None:
    """Get file contents from git at a specific commit or index.

    Uses `git show` command to retrieve file contents.
    If commit is None, retrieves from the index (staged version).

    Args:
        git_root: Absolute path to git repository root.
        commit: Commit reference (hash, "HEAD", "HEAD~2", etc.) or None for index.
        git_path: Relative path of the file within the repository.

    Returns:
        File contents as string, or None if file doesn't exist or error.
    """
    ...
```

#### Task 1.4: Implement `get_staged_paths` in GitPortAdapter

In `infrastructure/git/git_port_adapter.py`:

```python
def get_staged_paths(self, git_root: str) -> list[str]:
    """Get staged FCStd file paths using git status --porcelain.

    Filters for files that are staged in the index (position 0 status is not space).
    Only returns files with .FCStd extension.

    Args:
        git_root: Absolute path to git repository root.

    Returns:
        List of relative paths (from git root) that are staged and are FCStd files.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return []

        staged_paths = []
        for line in result.stdout.split("\n"):
            line = line.rstrip()
            if not line:
                continue

            # Parse porcelain format: "<index_status><wt_status> <path>"
            if len(line) < 4:
                continue

            index_status = line[0]
            rel_path = line[3:].strip()

            # Check if staged (index_status is not space) and is FCStd file
            if index_status != " " and rel_path.endswith(".FCStd"):
                staged_paths.append(rel_path)

        return staged_paths

    except subprocess.TimeoutExpired:
        Log.warning("Git status command timed out")
        return []
    except FileNotFoundError:
        Log.warning("Git command not found")
        return []
```

#### Task 1.5: Implement `get_file_contents` in GitPortAdapter

In `infrastructure/git/git_port_adapter.py`:

```python
def get_file_contents(self, git_root: str, commit: str | None, git_path: str) -> str | None:
    """Get file contents using git show.

    Args:
        git_root: Absolute path to git repository root.
        commit: Commit reference or None for index.
        git_path: Relative path within repository.

    Returns:
        File contents as string, or None if not found or error.
    """
    try:
        if commit is None:
            # Get from index using :<path> syntax
            cmd = ["git", "show", f":{git_path}"]
        else:
            # Get from specific commit
            cmd = ["git", "show", f"{commit}:{git_path}"]

        result = subprocess.run(
            cmd,
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return result.stdout
        return None

    except subprocess.TimeoutExpired:
        Log.warning(f"Git show command timed out for {git_path}")
        return None
    except FileNotFoundError:
        Log.warning("Git command not found")
        return None
```

#### Task 1.6: Add methods to GitService

In `domain/git/git_service.py`:

```python
def get_staged_files(self, repo: GitRepository) -> list[str]:
    """Get list of staged FCStd file paths.

    Args:
        repo: GitRepository to check.

    Returns:
        List of relative paths (from git root) of staged FCStd files.
    """
    return self._git_port.get_staged_paths(repo.absolute_path)

def get_file_contents(self, repo: GitRepository, commit: str | None, git_path: str) -> str | None:
    """Get file contents from git at a specific commit or index.

    Args:
        repo: GitRepository to get file from.
        commit: Commit reference or None for index.
        git_path: Relative path within repository.

    Returns:
        File contents as string, or None if not found.
    """
    return self._git_port.get_file_contents(repo.absolute_path, commit, git_path)
```

### Phase 2: SnapshotYamlSerializer Refactoring

#### Task 2.1: Write tests for refactored `from_yaml` / `from_yaml_file`

In `tests/unit/infrastructure/persistence/test_snapshot_yaml.py`:

```python
def test_from_yaml_deserializes_from_string():
    # Given a valid YAML string
    # When from_yaml is called
    # Then it returns a valid Snapshot object

def test_from_yaml_file_calls_from_yaml():
    # Given a valid YAML file
    # When from_yaml_file is called
    # Then it reads the file and passes content to from_yaml
```

#### Task 2.2: Refactor SnapshotYamlSerializer

In `infrastructure/persistence/snapshot_yaml.py`:

1. Rename current `from_yaml` to `from_yaml_file`:

```python
@staticmethod
def from_yaml_file(path: Path) -> Snapshot:
    """Deserialize a Snapshot from a YAML file.

    Args:
        path: The path to read the YAML file from.

    Returns:
        The deserialized Snapshot object.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SnapshotYamlSerializer._from_data(data)
```

2. Create new `from_yaml` that takes YAML string:

```python
@staticmethod
def from_yaml(yaml_string: str) -> Snapshot:
    """Deserialize a Snapshot from a YAML string.

    Args:
        yaml_string: The YAML content as a string.

    Returns:
        The deserialized Snapshot object.
    """
    data = yaml.safe_load(yaml_string)
    return SnapshotYamlSerializer._from_data(data)
```

3. Extract common deserialization logic to `_from_data`:

```python
@staticmethod
def _from_data(data: dict[str, Any]) -> Snapshot:
    """Deserialize a Snapshot from parsed YAML data.

    Args:
        data: The parsed YAML dictionary.

    Returns:
        The deserialized Snapshot object.
    """
    # Parse timestamp
    timestamp_raw = data.get("timestamp")
    if isinstance(timestamp_raw, datetime):
        timestamp = timestamp_raw
    elif isinstance(timestamp_raw, str) and timestamp_raw:
        timestamp = datetime.fromisoformat(timestamp_raw)
    else:
        timestamp = datetime.now(UTC)

    # Parse objects
    nodes = []
    for obj in data.get("objects", []):
        properties = SnapshotYamlSerializer._deserialize_properties(obj.get("properties", {}))

        node = TreeNode(
            id=obj["id"],
            name=obj["name"],
            type_id=obj["type_id"],
            label=obj.get("label", obj["name"]),
            path=obj["path"],
            after=obj.get("after"),
            properties=properties,
        )
        nodes.append(node)

    return Snapshot(
        snapshot_id=data.get("uid", ""),
        document_name="",
        timestamp=timestamp,
        nodes=nodes,
    )
```

### Phase 3: Domain Layer - Rename and Update `get_snapshot_yaml_path_for_document`

#### Task 3.1: Write tests for renamed and updated function

In `tests/unit/domain/snapshots/test_snapshot_path.py`:

```python
def test_returns_yaml_path_not_directory():
    # Given a document path "/home/user/project/path/to/mydoc.FCStd"
    # When get_snapshot_yaml_path_for_document is called
    # Then it returns Path("/home/user/project/path/to/.snapshots/mydoc.yaml")

def test_yaml_path_in_root_directory():
    # Given "mydoc.FCStd" (no directory component)
    # When get_snapshot_yaml_path_for_document is called
    # Then it returns Path(".snapshots/mydoc.yaml")
```

#### Task 3.2: Rename and update `get_snapshot_yaml_path_for_document`

In `domain/snapshots/__init__.py`, rename the function and ensure it returns the full yaml path:

```python
def get_snapshot_yaml_path_for_document(document_path: str) -> Path:
    """Get the YAML snapshot path for a given document file path.

    The snapshot is alongside the file in a hidden .snapshots directory.
    Example: /path/to/mydoc.FCStd -> /path/to/.snapshots/mydoc.yaml

    Args:
        document_path: String path to the document file (FCStd or similar).

    Returns:
        Path to the YAML snapshot file.
    """
    import os
    doc_path = Path(document_path)
    parent_dir = doc_path.parent
    doc_name = os.path.splitext(doc_path.name)[0]
    return parent_dir / ".snapshots" / f"{doc_name}.yaml"
```

### Phase 4: Application Layer Actions

#### Task 4.1: Write tests for GetStagedFilePathsAction

Create `tests/unit/application/actions/test_get_staged_file_paths.py`:

```python
def test_execute_returns_staged_paths():
    # Given a mock GitService that returns ["path/to/doc.FCStd"]
    # When execute is called with a repo
    # Then Result.success(["path/to/doc.FCStd"]) is returned

def test_execute_returns_empty_list_when_nothing_staged():
    # Given a mock GitService that returns []
    # When execute is called with a repo
    # Then Result.success([]) is returned

def test_execute_returns_failure_on_error():
    # Given a mock GitService that raises
    # When execute is called
    # Then Result.failure is returned
```

#### Task 4.2: Create GetStagedFilePathsAction

Create `application/actions/get_staged_file_paths.py`:

```python
# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for getting list of staged FCStd files.
"""Application action for getting staged file paths."""

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from .result_models import Result


__all__ = ["GetStagedFilePathsAction"]


class GetStagedFilePathsAction:
    """Get list of FCStd files that are staged in the git repository."""

    def __init__(self, git_service: GitService) -> None:
        """Initialize with GitService.

        Args:
            git_service: GitService for git operations.
        """
        self._git_service = git_service

    def execute(self, repo: GitRepository) -> Result:
        """Get staged FCStd file paths.

        Args:
            repo: GitRepository to get staged files from.

        Returns:
            Result containing list of staged FCStd git_paths on success.
        """
        staged_paths = self._git_service.get_staged_files(repo)
        return Result.success(staged_paths)
```

#### Task 4.3: Write tests for CreateDocumentSnapshotForCommitAction

In `tests/unit/application/actions/test_create_document_snapshot_commit.py`:

```python
def test_execute_with_commit_none_returns_index_snapshot():
    # Given a GitService that returns YAML content from index
    # When execute is called with commit=None and yaml_git_path
    # Then SnapshotYamlSerializer.from_yaml is called with the content

def test_execute_with_commit_hash_returns_commit_snapshot():
    # Given a GitService that returns YAML content from HEAD
    # When execute is called with commit="HEAD" and yaml_git_path
    # Then the snapshot is created from that content

def test_execute_returns_none_when_no_content():
    # Given a GitService that returns None
    # When execute is called
    # Then Result.success(None) is returned

def test_execute_returns_failure_on_deserialization_error():
    # Given a GitService that returns invalid YAML
    # When execute is called
    # Then Result.failure is returned
```

#### Task 4.4: Implement CreateDocumentSnapshotForCommitAction

Replace the stub implementation in `application/actions/create_document_snapshot_commit.py`:

```python
# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for creating snapshot from git commit or index.
"""Application action for creating snapshot from a git commit or index."""

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...domain.snapshots import get_snapshot_yaml_path_for_document
from ...infrastructure.persistence.snapshot_yaml import SnapshotYamlSerializer
from ...utils import Log
from .result_models import Result


__all__ = ["CreateDocumentSnapshotForCommitAction"]


class CreateDocumentSnapshotForCommitAction:
    """Create a snapshot from a document at a specific git commit or from the index.

    This extracts the YAML snapshot file from git (either from the index or a specific
    commit) and deserializes it to create a Snapshot object.
    """

    def __init__(self, git_service: GitService) -> None:
        """Initialize with GitService.

        Args:
            git_service: GitService for git operations.
        """
        self._git_service = git_service

    def execute(self, repo: GitRepository, fcstd_git_path: str) -> Result:
        """Create a snapshot from a git commit or index.

        When `commit` is None, retrieves the YAML snapshot from the git index.
        When `commit` is specified, retrieves from that commit.

        The `fcstd_git_path` is the path to the FCStd file (e.g., "path/to/mydoc.FCStd").
        This action computes the corresponding YAML snapshot path internally.

        Args:
            repo: GitRepository containing the document.
            fcstd_git_path: Relative path of the FCStd file within the repository.
            commit: Git commit hash/name, or None for index.

        Returns:
            Result containing Snapshot if found, None if file doesn't exist.
        """
        # Compute the YAML snapshot path from the FCStd git_path
        yaml_git_path = str(get_snapshot_yaml_path_for_document(fcstd_git_path))

        # Get file contents from git
        yaml_contents = self._git_service.get_file_contents(repo, commit, yaml_git_path)

        if yaml_contents is None:
            Log.debug(f"No snapshot found in {'index' if commit is None else commit} for {yaml_git_path}")
            return Result.success(None)

        try:
            snapshot = SnapshotYamlSerializer.from_yaml(yaml_contents)
            return Result.success(snapshot)
        except Exception as e:
            Log.exception(f"Failed to deserialize snapshot for {yaml_git_path}: {e}")
            return Result.failure(f"Failed to deserialize snapshot: {e}")
```

Note: The signature changed - `git_path` parameter was the FCStd path, and `commit` is now a separate parameter.

#### Task 4.5: Update StageDocumentsAction to use renamed helper

In `application/actions/stage_documents.py`, update how the yaml path is used:

```python
def execute(self, repo: GitRepository, snapshots: list[Snapshot]) -> Result:
    ...
    for snapshot in snapshots:
        git_path = snapshot.git_path
        if not git_path:
            Log.warning(f"Snapshot has no git_path, cannot stage: {snapshot.document_name}")
            continue

        # Get the full yaml path using the helper
        yaml_path = get_snapshot_yaml_path_for_document(git_path)

        # Create snapshot directory if it doesn't exist (use parent of yaml path)
        snapshot_dir = yaml_path.parent
        try:
            snapshot_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            Log.exception(f"Failed to create snapshot directory {snapshot_dir}: {e}")
            return Result.failure(f"Failed to create snapshot directory: {e}")

        # Persist snapshot to YAML
        try:
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            Log.info(f"Persisted snapshot to {yaml_path}")
        except Exception as e:
            Log.exception(f"Failed to persist snapshot for {git_path}: {e}")
            return Result.failure(f"Failed to persist snapshot: {e}")

        # Collect paths to stage (relative to git root)
        all_paths_to_stage.append(git_path)  # The FCStd file
        # Convert yaml_path to relative from repo root
        yaml_relative = str(yaml_path)[len(repo.absolute_path):].lstrip("/")
        all_paths_to_stage.append(yaml_relative)
    ...
```

#### Task 4.6: Update ApplicationContainer

In `application/di/container.py`:

1. Add import:
```python
from ..actions.get_staged_file_paths import GetStagedFilePathsAction
```

2. Add field to `ApplicationContainer` dataclass:
```python
get_staged_file_paths_action: GetStagedFilePathsAction
```

3. Add to `create_application_container`:
```python
get_staged_file_paths_action=GetStagedFilePathsAction(git_service=git_service),
```

### Phase 5: DiffPresenter Implementation

#### Task 5.1: Write tests for `_on_staging_selected`

In `tests/unit/ui/presenters/test_diff_presenter.py`:

```python
def test_on_staging_selected_clears_view_when_no_staged_files():
    # Given no staged files
    # When _on_staging_selected is called
    # Then view.show_diff_trees is called with empty list

def test_on_staging_selected_displays_staged_diffs():
    # Given staged files with changes
    # When _on_staging_selected is called
    # Then diff results are computed and passed to present_diffs

def test_on_staging_selected_handles_missing_snapshot():
    # Given a file staged without a corresponding YAML snapshot
    # When _on_staging_selected is called
    # Then missing_snapshot_paths is passed to present_diffs for flat warning items

def test_on_staging_selected_sorts_results_alphanumerically():
    # Given staged files ["b.FCStd", "a.FCStd", "c.FCStd"]
    # When _on_staging_selected is called
    # Then diff results are presented in alphabetical order
```

#### Task 5.2: Update DiffPresenter imports and constructor

In `ui/presenters/diff_presenter.py`:

1. Add import:
```python
from ...application.actions.get_staged_file_paths import GetStagedFilePathsAction
```

2. Update constructor signature:
```python
def __init__(
    self,
    view: DiffView,
    ui_state: UIState,
    get_eligible_docs_action: GetOpenEligibleDocumentsAction,
    create_working_snapshot_action: CreateDocumentSnapshotForWorkingTreeAction,
    create_commit_snapshot_action: CreateDocumentSnapshotForCommitAction,
    create_diff_action: CreateDiffAction,
    stage_documents_action: StageDocumentsAction,
    get_dirty_documents_action: GetDirtyDocumentsAction,
    get_staged_file_paths_action: GetStagedFilePathsAction,  # NEW
) -> None:
```

3. Store the new action:
```python
self._get_staged_file_paths = get_staged_file_paths_action
```

#### Task 5.3: Implement `_on_staging_selected`

Replace the stub in `ui/presenters/diff_presenter.py`:

```python
def _on_staging_selected(self) -> None:
    """Handle Staging item selection.

    For each staged FCStd file:
    1. Get staged snapshot from index (commit=None)
    2. Get snapshot from HEAD
    3. Create diff between HEAD and index

    Displays resulting diffs. For paths where index snapshot is missing,
    creates flat warning items (no tree below).
    """
    repo = self._ui_state.git_repository
    if repo is None:
        Log.warning("No git repository detected")
        return

    # Get list of staged FCStd files
    staged_result = self._get_staged_file_paths.execute(repo)
    if not staged_result.is_success:
        Log.warning(f"Failed to get staged files: {staged_result.message}")
        return

    staged_paths = staged_result.data or []
    if not staged_paths:
        # No staged files - clear the view
        self._view.show_doc_diffs([])
        return

    all_diff_results: list[DiffResult] = []
    missing_snapshot_paths: list[str] = []

    for git_path in staged_paths:
        # Get snapshot from index (staged version)
        index_result = self._create_commit_snapshot.execute(repo, None, git_path)
        index_snapshot = index_result.data if index_result.is_success else None

        # Get snapshot from HEAD
        head_result = self._create_commit_snapshot.execute(repo, "HEAD", git_path)
        head_snapshot = head_result.data if head_result.is_success else None

        if index_snapshot is None:
            # Snapshot missing in index - track for warning display (per MVP spec)
            missing_snapshot_paths.append(git_path)
            continue

        # Normal case: create diff between HEAD and index
        if head_snapshot is None:
            # HEAD doesn't have this file yet - treat as all new
            diff_result = self._create_diff.execute(None, index_snapshot)
        else:
            diff_result = self._create_diff.execute(head_snapshot, index_snapshot)

        if diff_result.is_success and diff_result.data is not None:
            all_diff_results.append(diff_result.data)
        else:
            Log.warning(f"Failed to compute diff for {git_path}: {diff_result.message}")

    # Sort both lists alphanumerically by git_path (will be re-sorted in present_diffs)
    all_diff_results.sort(key=lambda d: d.new_snapshot.git_path or "")
    missing_snapshot_paths.sort()

    # Store diff results keyed by git_path for later use
    self._diff_results_by_path.clear()
    for result in all_diff_results:
        result_git_path = result.new_snapshot.git_path
        if result_git_path:
            self._diff_results_by_path[result_git_path] = result

    if all_diff_results or missing_snapshot_paths:
        # Present with empty dirty_paths since staged files are, by definition, tracked
        self.present_diffs(all_diff_results, set(), missing_snapshot_paths)
    else:
        Log.warning("No diff results to display for staging")
```

#### Task 5.4: Update `present_diffs` signature and add sorting

Update `present_diffs` in `ui/presenters/diff_presenter.py` to accept `missing_snapshot_paths` and sort at the end:

```python
def present_diffs(self, diff_results: list[DiffResult], dirty_paths: set[str] | None = None, missing_snapshot_paths: list[str] | None = None) -> None:
    """Transform multiple DiffResults into presentation models and display.

    Args:
        diff_results: List of DiffResult objects to present.
        dirty_paths: Set of git paths that have git-tracked changes.
        missing_snapshot_paths: List of git_paths where snapshot is missing (creates flat warning items).
    """
    dirty_paths = dirty_paths or set()
    missing_snapshot_paths = missing_snapshot_paths or []

    if not diff_results and not missing_snapshot_paths:
        self._view.show_doc_diffs([])
        return

    presentations = []
    for diff_result in diff_results:
        nodes = [self._format_node(node) for node in diff_result.hierarchy.roots]
        git_path = diff_result.new_snapshot.git_path or diff_result.new_snapshot.document_name
        warnings = list(diff_result.warnings)

        has_changes = any(node.has_changes for node in nodes)
        is_git_dirty = git_path in dirty_paths
        stage_button_enabled = has_changes or is_git_dirty

        presentations.append(
            DiffTreePresentation(
                nodes=nodes,
                git_path=git_path,
                warnings=warnings,
                stage_button_enabled=stage_button_enabled,
            )
        )

    # Add flat warning items for missing snapshot paths
    for git_path in missing_snapshot_paths:
        presentations.append(
            DiffTreePresentation(
                nodes=[],  # Empty - flat item
                git_path=git_path,
                warnings=[WARNING_OLD_SNAPSHOT_MISSING],
                stage_button_enabled=False,
            )
        )

    # Sort all presentations alphanumerically by git_path
    presentations.sort(key=lambda p: p.git_path)

    self._view.show_doc_diffs(presentations)
    ...
```

#### Task 5.5: Update DiffView protocol and DiffPanelView

In `ui/protocols/diff_view.py`, update `show_diff_trees` signature if needed to match.

In `ui/views/diff_panel_view.py`, update `show_diff_trees` to handle flat warning items (items with empty `nodes` but non-empty `warnings`).

#### Task 5.6: Update UI composer

In `ui/composer.py`, update DiffPresenter instantiation to include the new action:

```python
diff_presenter = DiffPresenter(
    view=view,
    ui_state=ui_state,
    get_eligible_docs_action=container.get_open_eligible_docs_action,
    create_working_snapshot_action=container.create_working_snapshot_action,
    create_commit_snapshot_action=container.create_commit_snapshot_action,
    create_diff_action=container.create_diff_action,
    stage_documents_action=container.stage_documents_action,
    get_dirty_documents_action=container.get_dirty_documents_action,
    get_staged_file_paths_action=container.get_staged_file_paths_action,  # NEW
)
```

## Test Strategy

### Unit Tests

**Files to create/update:**
- `tests/unit/infrastructure/git/test_git_port_adapter.py` - Tests for `get_staged_paths` and `get_file_contents`
- `tests/unit/infrastructure/persistence/test_snapshot_yaml.py` - Tests for refactored `from_yaml` / `from_yaml_file`
- `tests/unit/domain/snapshots/test_snapshot_path.py` - Tests for updated `get_snapshot_directory_for_document`
- `tests/unit/application/actions/test_create_document_snapshot_commit.py` - Tests for loading snapshots from git
- `tests/unit/application/actions/test_get_staged_file_paths.py` - Tests for GetStagedFilePathsAction
- `tests/unit/ui/presenters/test_diff_presenter.py` - Tests for `_on_staging_selected`

**Run with:** `task test`

### Integration Tests

None - FreeCAD-dependent testing is manual only.

## Findings & Notes

### Snapshot Path Computation

The path to the YAML snapshot file is computed using `get_snapshot_yaml_path_for_document` which returns the full yaml path directly:
- FCStd path: `path/to/mydoc.FCStd`
- Snapshot path: `path/to/.snapshots/mydoc.yaml`

This helper is used by:
1. `StageDocumentsAction` - to know where to persist the yaml file
2. `CreateDocumentSnapshotForCommitAction` - to know where to find the yaml file in git

### Git Show Command Behavior

- `git show :<path>` retrieves the file from the index (staged version)
- `git show <commit>:<path>` retrieves the file from a specific commit
- Both return exit code 0 on success, non-zero if file doesn't exist in that location

### Staging vs Working Tree Difference

The key difference in `_on_staging_selected` vs `_on_working_tree_selected`:
- **Working Tree**: Compares working tree snapshot (via SnapshotExtractor) against index snapshot
- **Staging**: Compares index snapshot against HEAD snapshot

Both use the same underlying action (`CreateDocumentSnapshotForCommitAction` with different `commit` values) but interpret the results differently.

### Warning Items for Missing Snapshots

Per MVP spec, when a FCStd file is staged but its YAML snapshot is NOT in the index:
1. `CreateDocumentSnapshotForCommitAction` returns None for index
2. The git_path is added to `missing_snapshot_paths` list
3. `present_diffs` creates a `DiffTreePresentation` with empty `nodes` and `WARNING_OLD_SNAPSHOT_MISSING` in `warnings`
4. The view displays a flat (one-level) item with a warning icon

This is distinct from normal diff results which have a full tree hierarchy below the root node.

### Sorting Behavior

Sorting is done at the end of `present_diffs` on the final `DiffTreePresentation` list by `git_path`. This ensures consistent alphanumeric ordering across all diff types (working tree, staging, commit diffs).
