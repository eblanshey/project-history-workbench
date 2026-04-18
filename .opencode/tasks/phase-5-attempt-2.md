# Task: Phase 5 - Start of Working Tree Diff Implementation

## Goal

Implement the initial working tree diff functionality by creating actions for document snapshots, adding the DiffEngine orchestration, and wiring up the History widget selection to trigger diff computation via a single selection handler in the DiffPresenter.

## Context

Phase 5 of the MVP implementation bridges the gap between the commit History widget (Phase 2-3) and actual diff computation. This phase:
- Creates actions to extract snapshots from open documents
- Wires the History widget selection to a single handler in DiffPresenter
- Adds warning display for missing old snapshots
- Introduces the orchestration pattern for multi-document diff scenarios
- Removes legacy multi-selection logic that's no longer needed

This phase builds on:
- Phase 1's `FindActiveGitRepository` action and `ApplicationState`
- Phase 2's `GetCommits` action and History widget
- Phase 3's "Working Tree" and "Staging" pseudo-commits in the History widget
- Phase 4's `DiffEngine.compute_diff(None, snapshot)` support

The next phase (Phase 6) will add staging functionality, which extracts Snapshots from DiffResults.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Add `WARNING_OLD_SNAPSHOT_MISSING` constant | Provides a named constant for the warning, avoiding string typos | Use raw string literals everywhere, but constants are more maintainable |
| Add `get_eligible_docs()` to GitService | Filters documents within git repo before snapshot creation | Let actions filter, but service-level filtering is reusable |
| Create `CreateDocumentSnapshotForCommit` as stub returning None | Placeholder for Phase 7 implementation | Return empty snapshot, but None is clearer for "not yet implemented" |
| Store DiffResults in presenter, not ApplicationState | Domain objects shouldn't live in UI state; presenter orchestrates domain interactions | Store in ApplicationState, but violates dependency rules |
| Use `HistorySelection` dataclass for callbacks | Clear, type-safe way to pass selection data without overloading UserRole | Pass tuple or overloaded strings, but dataclass is more maintainable and self-documenting |
| History selection handled by DiffPresenter | DiffPresenter is responsible for creating tree diffs; GitRepositoryPresenter only handles repo detection | Put selection handling in GitRepositoryPresenter, but that violates single responsibility |
| Log warnings for failed document snapshots | Simple error handling for MVP; user can see issues in console | Show UI errors per document, but adds complexity for now |
| Remove multi-selection logic entirely | No longer needed with single-selection model; reduces code complexity | Keep both modes, but creates confusion and maintenance burden |

## Architecture Impact

### Files to Create

```
freecad/diff_wb/
├── application/actions/
│   ├── get_open_eligible_documents.py     # NEW: List eligible documents in git repo
│   ├── create_document_snapshot_working.py # NEW: Snapshot for working tree
│   ├── create_document_snapshot_commit.py  # NEW: Stub for commit snapshot (returns None)
│   └── create_diff.py                      # NEW: Wrapper for DiffEngine
```

### Files to Modify

```
freecad/diff_wb/
├── domain/
│   ├── diff/
│   │   └── models.py                       # MODIFY: Add WARNING_OLD_SNAPSHOT_MISSING constant
│   └── git/
│       └── git_service.py                  # MODIFY: Add get_eligible_docs() method
├── domain/freecad_ports.py                 # MODIFY: Add get_all_open_documents() to FreeCadPort
├── infrastructure/git/git_port_adapter.py  # MODIFY: Implement is_path_in_repository()
├── infrastructure/freecad/
│   └── ports.py                            # MODIFY: Implement get_all_open_documents() in adapter
├── application/di/
│   └── container.py                        # MODIFY: Wire new actions and DiffPresenter
├── ui/presenters/
│   ├── diff_presenter.py                   # UPDATE: Add actions, state, history selection handling
│   └── presentation_models.py              # UPDATE: Add DiffTreePresentation
├── ui/protocols/
│   └── diff_view.py                        # UPDATE: Add show_diff_trees to DiffView protocol
└── ui/views/
    └── diff_panel_view.py                  # UPDATE: Remove multi-selection, add HistorySelection, show_diff_trees
```

### Dependency Flow

```
History Widget Selection (single item)
         ↓
DiffPanelView triggers callback with HistorySelection
         ↓
DiffPresenter.on_history_item_selected(HistorySelection)
         ↓
         Routes based on selection.item_kind:
         - "WORKING_TREE" → _on_working_tree_selected()
         - "STAGING" → _on_staging_selected() (stub)
         - "COMMIT" → _on_commit_selected(selection.commit_hash) (stub)
         ↓
_on_working_tree_selected():
         ↓
[GetOpenEligibleDocuments] → Returns list of DocumentLike
         ↓
For each document:
         ↓
[CreateDocumentSnapshotForWorkingTree] → Creates Snapshot with git_path
         ↓
[CreateDocumentSnapshotForCommit] → Returns None (stub)
         ↓
[CreateDiff(None, new_snapshot)] → Produces DiffResult
         ↓
If failure: Log warning, continue to next document
         ↓
DiffPresenter collects all DiffResults → list[DiffResult]
         ↓
DiffPresenter.present_diffs(list[DiffResult])
         ↓
DiffView.show_diff_trees(list[DiffTreePresentation])
         ↓
Tree widget displays multiple top-level items (one per document)
         ↓
⚠️ warning indicator per document if DiffResult.warnings is non-empty
```

## FreeCAD Dependency

- [x] No FreeCAD required (pure code path)
- Actions depend on domain services, not FreeCAD directly
- Unit tests can use fakes for FreeCadPort

## Implementation Plan

### Phase 5.1: Add WARNING_OLD_SNAPSHOT_MISSING Constant

**Test First:**
- [x] Write test: `DiffResult` has static attribute `WARNING_OLD_SNAPSHOT_MISSING`
- [x] Write test: Warning string is non-empty and descriptive

**Implementation:**
- [x] Update `domain/diff/models.py`:
  ```python
  WARNING_OLD_SNAPSHOT_MISSING = "Old snapshot missing"
  ```
- [ ] Export in `__all__` if not already: `WARNING_OLD_SNAPSHOT_MISSING`

---

### Phase 5.2: Add is_path_in_repository to GitPort and get_eligible_docs to GitService

**Test First:**
- [x] Write test: `GitService.get_eligible_docs()` returns only documents within git repo
- [x] Write test: Empty list returned when no documents are in git repo
- [x] Write test: Documents outside git repo are filtered out
- [x] Write test: Works with mixed documents (some in, some out)

**Implementation:**
- [x] Update `domain/git/ports.py` - add to `GitPort` protocol:
  ```python
  def is_path_in_repository(self, git_root: str, path: str) -> bool:
      """Check if a path is within the git repository.

      Args:
          git_root: Absolute path to git repository root
          path: Path to check (file or directory)

      Returns:
          True if path is within git_root
      """
      ...
  ```
- [ ] Update `infrastructure/git/git_port_adapter.py` - implement `is_path_in_repository()`:
  ```python
  def is_path_in_repository(self, git_root: str, path: str) -> bool:
      # Normalize paths and check if path starts with git_root
  ```
- [ ] Update `domain/git/git_service.py` - add `get_eligible_docs()`:
  ```python
  def get_eligible_docs(self, repo: GitRepository, documents: list[DocumentLike]) -> list[DocumentLike]:
      """Filter documents to those within the git repository."""
      eligible = []
      for doc in documents:
          doc_path = getattr(doc, 'FileName', '')
          if doc_path and self._git_port.is_path_in_repository(repo.absolute_path, doc_path):
              eligible.append(doc)
      return eligible
  ```

---

### Phase 5.3: Add get_all_open_documents() to FreeCadPort

**Test First:**
- [x] Write test: `FreeCadPort.get_all_open_documents()` returns list of DocumentLike
- [x] Write test: Returns empty list when no documents are open
- [x] Write test: Each returned document has FileName and Objects attributes

**Implementation:**
- [x] Update `domain/freecad_ports.py` - add to `FreeCadPort` protocol:
  ```python
  def get_all_open_documents(self) -> list[DocumentLike]:
      """Get all open documents."""
      ...
  ```
- [ ] Update `infrastructure/freecad/ports.py` - implement in `FreeCadPortAdapter`:
  ```python
  def get_all_open_documents(self) -> list[object]:
      return list(self._ctx.app.Documents) if hasattr(self._ctx.app, 'Documents') else []
  ```

---

### Phase 5.4: Create GetOpenEligibleDocumentsAction

**Test First:**
- [x] Write test: Action returns Result with list of DocumentLike on success
- [x] Write test: Action returns failure Result when no documents eligible
- [x] Write test: Action filters correctly using GitService.get_eligible_docs()

**Implementation:**
- [x] Create `application/actions/get_open_eligible_documents.py`:
  ```python
  """Application action for getting eligible open documents."""

  from ...domain.freecad_ports import FreeCadPort
  from ...domain.git.git_service import GitService
  from ...domain.git.models import GitRepository
  from .result_models import Result

  class GetOpenEligibleDocumentsAction:
      """Get all open documents that are within the git repository."""

      def __init__(
          self,
          freecad_port: FreeCadPort,
          git_service: GitService,
      ) -> None:
          self._freecad_port = freecad_port
          self._git_service = git_service

      def execute(self, repo: GitRepository) -> Result:
          all_docs = self._freecad_port.get_all_open_documents()
          eligible = self._git_service.get_eligible_docs(repo, list(all_docs))
          return Result.success(eligible)
  ```

---

### Phase 5.5: Create CreateDocumentSnapshotForWorkingTreeAction

**Test First:**
- [x] Write test: Action returns Result with Snapshot on success
- [x] Write test: Action returns failure Result when document not in git repo
- [x] Write test: Snapshot has correct git_path set
- [x] Write test: Snapshot has correct document_name and nodes

**Implementation:**
- [x] Create `application/actions/create_document_snapshot_working.py`:
  ```python
  """Application action for creating snapshot from working tree document."""

  from ...domain.freecad_ports import DocumentLike, FreeCadPort
  from ...domain.git.git_service import GitService
  from ...domain.git.models import GitRepository
  from ...domain.snapshots.extractor import SnapshotExtractor
  from ...utils import Log
  from .result_models import Result

  class CreateDocumentSnapshotForWorkingTreeAction:
      """Create a snapshot for a document in the working tree."""

      def __init__(
          self,
          freecad_port: FreeCadPort,
          git_service: GitService,
          extractor: SnapshotExtractor,
      ) -> None:
          self._freecad_port = freecad_port
          self._git_service = git_service
          self._extractor = extractor

      def execute(self, repo: GitRepository, document: DocumentLike) -> Result:
          doc_path = getattr(document, 'FileName', '')
          if not doc_path:
              return Result.failure("Document has no file path (unsaved)")

          eligible_docs = self._git_service.get_eligible_docs(repo, [document])
          if not eligible_docs:
              return Result.failure("Document is not in the git repository")

          git_path = doc_path[len(repo.absolute_path):].lstrip('/')
          snapshot = self._extractor.extract_tree(document, git_path=git_path)

          Log.info(f"Created working tree snapshot for {git_path}")
          return Result.success(snapshot)
  ```

- [ ] Update `domain/snapshots/gui_extractor.py` to accept `git_path` parameter:
  ```python
  def _extract_tree_single_pass(
      doc: DocumentLike,
      gui_doc: Any,
      document_name: str,
      git_path: str = "",  # NEW
  ) -> Snapshot:
      return Snapshot(
          snapshot_id=str(uuid.uuid4()),
          document_name=document_name,
          timestamp=datetime.now(),
          nodes=nodes,
          git_path=git_path,
      )

  class SnapshotExtractor:
      def extract_tree(self, doc: DocumentLike, git_path: str = "") -> Snapshot:
          return _extract_tree_single_pass(doc, gui_doc, document_name, git_path)
  ```

---

### Phase 5.6: Create CreateDocumentSnapshotForCommitAction (Stub)

**Test First:**
- [x] Write test: Action returns Result with None (for stub)
- [x] Write test: Action signature accepts repo, commit, git_path parameters

**Implementation:**
- [x] Create `application/actions/create_document_snapshot_commit.py`:
  ```python
  """Application action for creating snapshot from a git commit (STUB)."""

  from ...domain.git.git_service import GitService
  from ...domain.git.models import GitRepository
  from .result_models import Result

  class CreateDocumentSnapshotForCommitAction:
      """Create a snapshot from a document at a specific git commit.

      STUB: Currently returns None. Will be implemented in Phase 7.
      """

      def __init__(self, git_service: GitService) -> None:
          self._git_service = git_service

      def execute(self, repo: GitRepository, commit: str, git_path: str) -> Result:
          """STUB: Always returns None until Phase 7 implementation."""
          return Result.success(None)
  ```

---

### Phase 5.7: Create CreateDiffAction

**Test First:**
- [x] Write test: Action returns Result with DiffResult on success
- [x] Write test: When old_snapshot is None, DiffResult has WARNING_OLD_SNAPSHOT_MISSING
- [x] Write test: When old_snapshot equals new_snapshot, DiffResult has "same snapshot" warning

**Implementation:**
- [x] Create `application/actions/create_diff.py`:
  ```python
  """Application action for computing diff between snapshots."""

  from ...domain.diff.engine import DiffEngine
  from ...domain.snapshots.models import Snapshot
  from ...utils import Log
  from .result_models import Result

  class CreateDiffAction:
      """Compute diff between two snapshots using DiffEngine."""

      def __init__(self, diff_engine: DiffEngine) -> None:
          self._diff_engine = diff_engine

      def execute(self, old_snapshot: Snapshot | None, new_snapshot: Snapshot) -> Result:
          try:
              diff_result = self._diff_engine.compute_diff(old_snapshot, new_snapshot)
              return Result.success(diff_result)
          except Exception as e:
              Log.exception(f"Failed to compute diff: {e}")
              return Result.failure(f"Failed to compute diff: {e}")
  ```

---

### Phase 5.8: Add DiffTreePresentation Model

**Test First:**
- [x] Write test: `DiffTreePresentation` dataclass can be created with nodes, git_path, warnings
- [x] Write test: All fields are properly accessible

**Implementation:**
- [x] Add to `ui/presenters/presentation_models.py`:
  ```python
  @dataclass(frozen=True)
  class DiffTreePresentation:
      """Wrapper for presenting a single diff tree with metadata.

      Attributes:
          nodes: Transformed list of root NodePresentation objects
          git_path: Git path of the document
          warnings: List of warning strings from DiffResult.warnings
      """
      nodes: list[NodePresentation]
      git_path: str
      warnings: list[str]
  ```
- [ ] Update `__all__` in presentation_models.py

---

### Phase 5.9: Update DiffView Protocol for Multi-Document

**Test First:**
- [x] Write test: DiffView has `show_diff_trees()` method in protocol
- [x] Write test: Signature accepts `list[DiffTreePresentation]`

**Implementation:**
- [x] Update `ui/protocols/diff_view.py`:
  ```python
  from ..presenters.presentation_models import DiffTreePresentation, NodePresentation, PropertyPresentation

  # Add to DiffView protocol:
  def show_diff_trees(self, diffs: list[DiffTreePresentation]) -> None:
      """Display multiple diff trees (one per document)."""
  ```

---

### Phase 5.10: Implement show_diff_trees in DiffPanelView

**Test First:**
- [x] Write test: `show_diff_trees()` clears existing items and displays multiple diffs
- [x] Write test: Each diff appears as top-level item with its git_path
- [x] Write test: Warning emoji (⚠️) appears when DiffTreePresentation.warnings is non-empty
- [x] Write test: Warning tooltip contains the warning text

**Implementation:**

#### Step 1: Add show_diff_trees method

- [x] Add to `ui/views/diff_panel_view.py`:
  ```python
  def show_diff_trees(self, diffs: list[DiffTreePresentation]) -> None:
      """Display multiple diff trees in the tree widget."""
      self.tree_widget.clear()

      if not diffs:
          return

      for diff in diffs:
          top_level_text = diff.git_path or "Unnamed Document"

          if diff.warnings:
              warning_text = " ⚠️ ".join(diff.warnings)
              top_level_text = f"{top_level_text} ⚠️"
              root_item = QTreeWidgetItem([top_level_text])
              root_item.setToolTip(0, warning_text)
          else:
              root_item = QTreeWidgetItem([top_level_text])

          for node in diff.nodes:
              item = self._create_tree_item(node)
              root_item.addChild(item)

          self.tree_widget.addTopLevelItem(root_item)
          self._expand_nodes_with_changes(root_item)

      self.tree_widget.show()
  ```

---

### Phase 5.11: Add HistorySelection and Remove Multi-Selection Logic

**Context:** The legacy multi-selection logic (from/to comparison with custom coloring) is no longer needed. We're moving to a single-selection model where selecting any item immediately triggers the appropriate action. We add the `HistorySelection` dataclass first so it can be used in the refactoring steps.

**Implementation:**

#### Step 1: Add HistorySelection dataclass

- [x] Add to `ui/views/diff_panel_view.py` near top of file (after imports):
  ```python
  from dataclasses import dataclass

  @dataclass(frozen=True)
  class HistorySelection:
      """Represents a selected item in the history list.

      Attributes:
          item_kind: One of "WORKING_TREE", "STAGING", or "COMMIT"
          commit_hash: Only set when item_kind == "COMMIT"
      """
      item_kind: Literal["WORKING_TREE", "STAGING", "COMMIT"]
      commit_hash: str | None

- [x] Write test: `HistorySelection` dataclass can be created with all three item kinds
- [x] Write test: `HistorySelection` stores commit_hash correctly for COMMIT kind
- [x] Write test: `HistorySelection` has commit_hash=None for WORKING_TREE and STAGING

#### Step 2: Remove selection tracking data structures

- [x] Remove from `ui/views/diff_panel_view.py`:
  ```python
  # REMOVE: _SelectedItem dataclass
  # REMOVE: self._selected_items: dict[int, _SelectedItem] in __init__
  # REMOVE: _WORKING_TREE_ROLE, _STAGING_ROLE constants (no longer needed with HistorySelection)

#### Step 3: Remove custom delegate for role-based coloring

- [x] Remove from `ui/views/diff_panel_view.py`:
  ```python
  # REMOVE: _SnapshotListItemDelegate class entirely
  # REMOVE: self._delegate initialization in __init__
  # REMOVE: history_list.setItemDelegate(self._delegate)
  # REMOVE: _delegate._parent = self.history_list

#### Step 4: Remove all selection management methods

- [x] Remove from `ui/views/diff_panel_view.py`:
  ```python
  # REMOVE: _on_selection_changed()
  # REMOVE: _handle_deselection()
  # REMOVE: _handle_new_selections()
  # REMOVE: _reject_selection()
  # REMOVE: _assign_role()
  # REMOVE: _apply_selection_style()
  # REMOVE: _get_item_role()
  # REMOVE: get_selected_snapshot_ids()
  # REMOVE: clear_selection()
  # REMOVE: _get_default_background()

#### Step 5: Simplify history list setup

- [x] Update `ui/views/diff_panel_view.py` in `_setup_ui()`:
  ```python
  # Change from MultiSelection to SingleSelection
  self.history_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
  # REMOVE: self.history_list.itemSelectionChanged.connect(self._on_selection_changed)
  # Now we'll connect to a simpler handler that just calls the callback

#### Step 6: Update show_commits to use HistorySelection

- [x] Update `ui/views/diff_panel_view.py` in `show_commits()`:
  ```python
  def show_commits(self, commits: list[GitCommit]) -> None:
      """Display git commits in the history list."""
      # Clear existing items and selections
      self.history_list.clear()

      # Add "Working Tree" item
      working_tree_item = QListWidgetItem("Working Tree")
      working_tree_item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignCenter)
      working_tree_item.setData(
          Qt.ItemDataRole.UserRole,
          HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
      )
      self.history_list.addItem(working_tree_item)

      # Add "Staging" item
      staging_item = QListWidgetItem("Staging")
      staging_item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignCenter)
      staging_item.setData(
          Qt.ItemDataRole.UserRole,
          HistorySelection(item_kind="STAGING", commit_hash=None)
      )
      self.history_list.addItem(staging_item)

      # Guard: no commits to display after adding special items
      if not commits:
          return

      # Add each commit to the list
      for commit in sorted_commits:
          # ... (existing display text formatting) ...

          item = QListWidgetItem(display_text)
          item.setToolTip(commit.message)
          item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignLeft)
          # Store HistorySelection with COMMIT kind
          item.setData(
              Qt.ItemDataRole.UserRole,
              HistorySelection(item_kind="COMMIT", commit_hash=commit.id)
          )
          self.history_list.addItem(item)
  ```

**Note:** Fix any existing tests that reference removed methods or expect old multi-selection behavior. No new tests needed for code removal.

---

### Phase 5.12: Add Callback Wiring

**Test First:**
- [x] Write test: View has `set_history_selection_callback()` method
- [x] Write test: Selecting any item triggers callback immediately with correct `HistorySelection`

**Implementation:**

#### Step 1: Add callback mechanism

- [x] Add to `ui/views/diff_panel_view.py` in `__init__`:
  ```python
  self._on_history_selection_callback: Callable[[HistorySelection], None] | None = None

#### Step 2: Add setter method and click handler

- [x] Add setter method:
  ```python
  def set_history_selection_callback(self, callback: Callable[[HistorySelection], None]) -> None:
      """Set the callback for history list selection.

      Args:
          callback: A callable that receives HistorySelection with item_kind and commit_hash
      """
      self._on_history_selection_callback = callback
      # Connect to item clicked signal for immediate response
      self.history_list.itemClicked.connect(self._on_item_clicked)

  def _on_item_clicked(self, item: QListWidgetItem) -> None:
      """Handle item click by triggering callback with HistorySelection."""
      if self._on_history_selection_callback is None:
          return

      item_data = item.data(Qt.ItemDataRole.UserRole)
      if isinstance(item_data, HistorySelection):
          self._on_history_selection_callback(item_data)
  ```

---

### Phase 5.13: Refactor DiffPresenter for Multi-Document and History Selection

**Test First:**
- [x] Write test: `DiffPresenter` has `on_history_item_selected()` method
- [x] Write test: `on_history_item_selected()` routes WORKING_TREE to `_on_working_tree_selected()`
- [x] Write test: `on_history_item_selected()` routes STAGING to `_on_staging_selected()`
- [x] Write test: `on_history_item_selected()` routes COMMIT to `_on_commit_selected()`
- [x] Write test: `present_diffs()` accepts `list[DiffResult]`
- [x] Write test: Each DiffResult is transformed to `DiffTreePresentation`
- [x] Write test: `_on_working_tree_selected()` calls `GetOpenEligibleDocumentsAction.execute()` with correct repo
- [x] Write test: For each eligible document, creates working tree snapshot
- [x] Write test: Creates diff with None old_snapshot and working tree snapshot as new
- [x] Write test: Logs warning for failed snapshots but continues processing
- [x] Write test: Collects all successful DiffResults and passes to `present_diffs()`

**Implementation:**

#### Step 1: Update DiffPresenter imports and constructor

- [x] Update `ui/presenters/diff_presenter.py`:
  ```python
  from ...application.actions.create_diff import CreateDiffAction
  from ...application.actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
  from ...application.actions.create_document_snapshot_working import CreateDocumentSnapshotForWorkingTreeAction
  from ...application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
  from ...domain.diff.models import DiffResult
  from ...ui.presenters.application_state import ApplicationState
  from .presentation_models import DiffTreePresentation, NodePresentation, PropertyPresentation
  ```

- [x] Update constructor:
  ```python
  def __init__(
      self,
      view: DiffView,
      application_state: ApplicationState,
      get_eligible_docs_action: GetOpenEligibleDocumentsAction,
      create_working_snapshot_action: CreateDocumentSnapshotForWorkingTreeAction,
      create_commit_snapshot_action: CreateDocumentSnapshotForCommitAction,
      create_diff_action: CreateDiffAction,
  ) -> None:
      self._view = view
      self._application_state = application_state
      self._get_eligible_docs = get_eligible_docs_action
      self._create_working_tree_snapshot = create_working_snapshot_action
      self._create_commit_snapshot = create_commit_snapshot_action
      self._create_diff = create_diff_action
  ```

#### Step 2: Add history item selection handler

- [x] Add to `ui/presenters/diff_presenter.py`:
  ```python
  def on_history_item_selected(self, selection: HistorySelection) -> None:
      """Handle single item selection from history list.

      Args:
          selection: HistorySelection containing item_kind and optional commit_hash
      """
      if selection.item_kind == "WORKING_TREE":
          self._on_working_tree_selected()
      elif selection.item_kind == "STAGING":
          self._on_staging_selected()
      elif selection.item_kind == "COMMIT":
          self._on_commit_selected(selection.commit_hash)
  ```

#### Step 3: Add working tree orchestration method

- [x] Add to `ui/presenters/diff_presenter.py`:
  ```python
  def _on_working_tree_selected(self) -> None:
      """Handle Working Tree item selection.

      For each eligible document:
      1. Create working tree snapshot
      2. Create diff against None (old snapshot)
      3. Collect results, logging warnings for failures
      """
      repo = self._application_state.git_repository
      if repo is None:
          Log.warning("No git repository detected")
          return

      docs_result = self._get_eligible_docs.execute(repo)
      if not docs_result.is_success or not docs_result.data:
          Log.warning(f"No eligible documents: {docs_result.message}")
          return

      eligible_docs = docs_result.data
      all_diff_results: list[DiffResult] = []

      for doc in eligible_docs:
          working_result = self._create_working_tree_snapshot.execute(repo, doc)
          if not working_result.is_success or working_result.data is None:
              Log.warning(f"Failed to create working snapshot: {working_result.message}")
              continue

          working_snapshot = working_result.data

          commit_result = self._create_commit_snapshot.execute(repo, None, working_snapshot.git_path)
          commit_snapshot = commit_result.data if commit_result.is_success else None

          diff_result = self._create_diff.execute(commit_snapshot, working_snapshot)
          if diff_result.is_success and diff_result.data is not None:
              all_diff_results.append(diff_result.data)
          else:
              Log.warning(f"Failed to compute diff: {diff_result.message}")

      if all_diff_results:
          self.present_diffs(all_diff_results)
      else:
          Log.warning("No diff results to display")
  ```

#### Step 4: Add stub methods for staging and commit

- [x] Add to `ui/presenters/diff_presenter.py`:
  ```python
  def _on_staging_selected(self) -> None:
      """Handle Staging item selection. STUB: For now, does nothing."""
      pass

  def _on_commit_selected(self, commit_hash: str | None) -> None:
      """Handle commit item selection. STUB: For now, does nothing."""
      pass
  ```

#### Step 5: Add present_diffs method

- [x] Add to `ui/presenters/diff_presenter.py`:
  ```python
  def present_diffs(self, diff_results: list[DiffResult]) -> None:
      """Transform multiple DiffResults into presentation models and display."""
      if not diff_results:
          self._view.show_diff_trees([])
          return

      presentations = []
      for diff_result in diff_results:
          nodes = [self._format_node(node) for node in diff_result.hierarchy.roots]
          git_path = diff_result.new_snapshot.git_path or diff_result.new_snapshot.document_name
          warnings = list(diff_result.warnings)

          presentations.append(DiffTreePresentation(
              nodes=nodes,
              git_path=git_path,
              warnings=warnings,
          ))

      self._view.show_diff_trees(presentations)

      # Show summary from first document (for now)
      first = diff_results[0]
      self._view.show_summary(
          added=first.added_count,
          deleted=first.deleted_count,
          modified=first.modified_count,
      )
  ```

---

### Phase 5.14: Update Container Wiring

**Implementation:**
- [x] Update `application/di/container.py`:
  - Add new actions to `ApplicationContainer` dataclass
  - Add `DiffPresenter` to `ApplicationContainer` dataclass (with new dependencies)
  - Wire all dependencies in `create_application_container()`
  - Wire `set_history_selection_callback()`: `view.set_history_selection_callback(diff_presenter.on_history_item_selected)`

---

## Test Strategy

### Unit Tests (No FreeCAD)

- Phase 5.1: `DiffResult` has `WARNING_OLD_SNAPSHOT_MISSING` constant
- Phase 5.2: `GitService.get_eligible_docs()` with fake GitPort
- Phase 5.3: `FreeCadPort.get_all_open_documents()` returns expected documents
- Phase 5.4: `GetOpenEligibleDocumentsAction` with fakes
- Phase 5.5: `CreateDocumentSnapshotForWorkingTreeAction` with fakes
- Phase 5.6: `CreateDocumentSnapshotForCommitAction` stub returns None
- Phase 5.7: `CreateDiffAction` with fake DiffEngine
- Phase 5.8: `DiffTreePresentation` model creation
- Phase 5.9: DiffView protocol includes `show_diff_trees`
- Phase 5.10: `DiffPanelView.show_diff_trees()` displays multiple documents with warnings
- Phase 5.11: `HistorySelection` dataclass creation with all item kinds
- Phase 5.12: View callback is invoked with correct `HistorySelection`
- Phase 5.13: `DiffPresenter.on_history_item_selected()` routes correctly
- Phase 5.13: `DiffPresenter._on_working_tree_selected()` orchestration with error logging
- Phase 5.13: `DiffPresenter.present_diffs()` with multiple DiffResults
- Phase 5.14: Container wiring creates all dependencies correctly

**Note:** Phase 5.11 removes multi-selection logic - no new tests for removal, but fix any existing tests that break.

## Findings & Notes

### Why DiffPresenter handles history selection?

`GitRepositoryPresenter` is responsible for git repository detection and commit loading (Phase 2-3). It has no diff logic.

`DiffPresenter` is responsible for transforming diff results and calling view methods. It naturally extends to also handle the **trigger** for diff creation - when a user selects an item in the history widget, DiffPresenter receives the notification and orchestrates the diff creation.

This maintains single responsibility:
- GitRepositoryPresenter: git repo detection + commit display
- DiffPresenter: diff creation orchestration + result presentation

### Phase Ordering for Unit Testing

The phases are ordered to ensure each phase's tests can run independently:

1. Phase 5.1: Independent constant
2. Phase 5.2: Uses ports (already exist) + GitService
3. Phase 5.3: Uses FreeCadPort protocol
4. Phase 5.4: Uses Phase 5.2 and 5.3
5. Phase 5.5: Uses Phase 5.2 and 5.3
6. Phase 5.6: Independent stub
7. Phase 5.7: Uses DiffEngine (already exists)
8. Phase 5.8: New model class
9. Phase 5.9: Uses Phase 5.8 model in protocol
10. Phase 5.10: Uses Phase 5.8 model in view
11. Phase 5.11: Add HistorySelection dataclass + remove multi-selection logic (no tests for removal)
12. Phase 5.12: Add callback wiring (uses HistorySelection from Phase 5.11)
13. Phase 5.13: DiffPresenter update (uses all previous phases)
14. Phase 5.14: Container wiring (uses all previous phases)

### Question: Where should we store DiffResults for application state?

**Answer:** DiffResults should **NOT** be stored in `ApplicationState`. Here's why:

1. **Architecture Violation**: `ApplicationState` is explicitly for UI layer only. DiffResult is a domain object.

2. **Proper Layering**:
   - DiffResults are created by domain services (DiffEngine)
   - Actions return DiffResults as `Result.data`
   - Presenters receive DiffResults and transform them for views
   - Views display DiffResults

3. **For Phase 6 and beyond**:
   - Phase 6 needs to extract Snapshots from DiffResults for staging
   - The `DiffPresenter` orchestrates this flow
   - It keeps DiffResults temporarily during the orchestration

### HistorySelection Dataclass

Using a dataclass instead of overloaded UserRole strings provides:
- **Type safety**: Clear structure with explicit fields
- **Self-documenting**: No magic strings or confusing parameter meanings
- **Extensible**: Easy to add more fields later if needed
- **Testable**: Easy to construct test cases

```python
@dataclass(frozen=True)
class HistorySelection:
    """Represents a selected item in the history list."""
    item_kind: Literal["WORKING_TREE", "STAGING", "COMMIT"]
    commit_hash: str | None  # Only set when item_kind == "COMMIT"
```

This replaces the confusing pattern where:
- `_WORKING_TREE_ROLE = "WORKING_TREE"` was stored in UserRole
- Commit hashes were stored directly in UserRole
- Callback had to figure out what type based on the value

Now it's explicit and clear.
