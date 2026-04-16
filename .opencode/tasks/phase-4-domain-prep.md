# Task: Phase 4 - Domain Prep for Snapshots

## Goal
Update domain models and logic to support Git paths and snapshot-based comparisons, enabling multi-document diffs and proper git integration in subsequent phases.

## Context
Phase 4 of the MVP implementation focuses on refactoring core domain entities to prepare for working tree and staging diff implementations. This phase:
- Replaces string-based snapshot identification with actual Snapshot objects
- Adds git path tracking for multi-document support
- Introduces warning system for edge cases (missing snapshots)
- Updates comparison algorithms to work with Snapshot containers
- Simplifies SnapshotExtractor interface by removing port abstraction

This is a **pure code refactoring phase** - no FreeCAD API exploration needed since we're modifying domain layer logic only.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Add `git_path: str` to Snapshot | Stores relative path from git root for multi-document diffs | Could use absolute path, but relative is more portable and matches git conventions |
| Replace `old_snapshot_name`/`new_snapshot_name` with `old_snapshot`/`new_snapshot` fields | Direct access to snapshot data, eliminates need for separate lookups | Keep strings and do lookups elsewhere, but that adds coupling and indirection |
| Add `warnings: list[str]` to DiffResult | Simple string-based warning system for edge cases | Could create Warning enum/class, but strings are sufficient for MVP |
| TreeComparator.compare_snapshots accepts Snapshots | Encapsulates node extraction logic, cleaner API | Keep accepting lists of nodes, but that leaks implementation detail |
| DiffEngine.compare accepts `None` for old_snapshot | Handles "no previous snapshot" case elegantly | Require caller to pass same snapshot twice, but that's less explicit |
| SnapshotExtractor.extract_tree() takes `DocumentLike` directly | Removes unnecessary port indirection | Keep port parameter for future flexibility, but current usage doesn't need it |
| Top-level tree item uses `git_path` | Supports multiple documents in diff view | Keep using document_name, but git_path is more specific and unique |

## Architecture Impact

### Files to Modify

```
freecad/diff_wb/
├── domain/
│   ├── snapshots/
│   │   ├── models.py                    # MODIFY: Add git_path to Snapshot
│   │   └── gui_extractor.py             # MODIFY: Change extract_tree signature
│   └── diff/
│       ├── models.py                    # MODIFY: Update DiffResult structure
│       └── comparator.py                # MODIFY: Update TreeComparator.compare_snapshots
└── ui/
    └── views/diff_panel_view.py         # MODIFY: Update tree display to show git_path
```

### Dependency Flow
- Domain layer changes are independent (pure Python)
- UI layer depends on domain changes (tree display update)
- No infrastructure changes required

## FreeCAD Dependency
- [x] No FreeCAD required (pure domain refactoring)
- Unit tests can be written and run immediately
- UI changes require FreeCAD for manual testing

## Implementation Plan

### Phase 4.1: Snapshot Model - Add git_path Field

**Test First:**
- [ ] Write test: `Snapshot` with `git_path` field creates correctly
- [ ] Write test: `git_path` is relative path from git root (e.g., "path/to/doc.FCStd")
- [ ] Write test: `git_path` used in `__str__` representation

**Implementation:**
- [ ] Update `domain/snapshots/models.py`:
  ```python
  @dataclass(frozen=True)
  class Snapshot:
      snapshot_id: str
      document_name: str
      timestamp: datetime
      nodes: list[TreeNode] = field(default_factory=list)
      git_path: str = ""  # NEW: Relative path from git root
  ```
- [ ] Update `__str__` method to include git_path if present
- [ ] **Update call sites**: Find all places creating `Snapshot` instances and add `git_path=""` parameter:
  - `domain/snapshots/gui_extractor.py` - `_extract_tree_single_pass()` and fallback returns
  - Any test files creating Snapshots directly
  - Any application actions creating Snapshots

### Phase 4.2: DiffResult Model - Replace Names with Snapshots and Add Warnings

**Test First:**
- [ ] Write test: `DiffResult` created with `old_snapshot` and `new_snapshot` parameters
- [ ] Write test: `warnings` list is initialized empty by default
- [ ] Write test: Same snapshot instance for old/new triggers warning
- [ ] Write test: `warnings` can contain multiple strings

**Implementation:**
- [ ] Update `domain/diff/models.py`:
  ```python
  @dataclass(frozen=True)
  class DiffResult:
      old_snapshot: Snapshot  # CHANGED: was old_snapshot_name: str
      new_snapshot: Snapshot  # CHANGED: was new_snapshot_name: str
      warnings: list[str] = field(default_factory=list)  # NEW
      added_count: int = 0
      deleted_count: int = 0
      modified_count: int = 0
      hierarchy: DiffHierarchy = field(default_factory=lambda: DiffHierarchy())
  ```
- [ ] Remove `old_snapshot_name` and `new_snapshot_name` fields
- [ ] Add logic in `__post_init__` to check if old_snapshot is same instance as new_snapshot and add warning
  ```python
  def __post_init__(self) -> None:
      if self.old_snapshot is self.new_snapshot:
          object.__setattr__(self, 'warnings', ['Same snapshot instance used for both old and new'])
  ```
- [ ] Update `__str__` method to use snapshot.document_name instead of snapshot_name strings
- [ ] Update `has_changes` property if needed (should still work with Snapshot objects)
- [ ] **Update call sites**: Find all places creating `DiffResult` instances (primarily in `TreeComparator`) and update to pass Snapshot objects instead of strings

### Phase 4.3: TreeComparator - Accept Snapshots Instead of Nodes

**Test First:**
- [ ] Write test: `TreeComparator.compare_snapshots()` accepts two `Snapshot` instances
- [ ] Write test: Method extracts nodes from snapshots internally
- [ ] Write test: Returns `DiffResult` with `old_snapshot` and `new_snapshot` fields populated
- [ ] Write test: Existing comparison logic works unchanged (node diffs, counts)

**Implementation:**
- [ ] Update `domain/diff/comparator.py`:
  ```python
  class TreeComparator:
      def compare_snapshots(
          self,
          old_snapshot: Snapshot,  # CHANGED: was old_nodes: list[TreeNode]
          new_snapshot: Snapshot,  # CHANGED: was new_nodes: list[TreeNode]
      ) -> DiffResult:
          """Compare two snapshots using ID-based comparison.
          
          Args:
              old_snapshot: The old snapshot to compare
              new_snapshot: The new snapshot to compare
              
          Returns:
              DiffResult containing hierarchy and counts
          """
          # Extract nodes from snapshots
          old_nodes = old_snapshot.nodes
          new_nodes = new_snapshot.nodes
          
          # ... rest of existing algorithm unchanged ...
          
          # Update DiffResult construction to pass snapshots
          return DiffResult(
              old_snapshot=old_snapshot,  # CHANGED: was old_snapshot_name="old"
              new_snapshot=new_snapshot,  # CHANGED: was new_snapshot_name="new"
              added_count=added_count,
              deleted_count=deleted_count,
              modified_count=modified_count,
              hierarchy=hierarchy,
          )
  ```
- [ ] Update method signature in `TreeComparatorProtocol` in `engine.py`
- [ ] **Update call sites**: Find all places calling `compare_snapshots()` and update to pass Snapshot objects instead of node lists. This includes:
  - `domain/diff/engine.py` - `compute_diff()` method calls
  - Any application actions that directly use TreeComparator
  - Any test files calling compare_snapshots()

### Phase 4.4: DiffEngine - Support None for Old Snapshot

**Test First:**
- [ ] Write test: `DiffEngine.compute_diff()` accepts `None` for old_snapshot
- [ ] Write test: When old_snapshot is None, same snapshot is used for both
- [ ] Write test: Warning is added when same snapshot used
- [ ] Write test: Normal operation (both snapshots provided) works unchanged

**Implementation:**
- [ ] Update `domain/diff/engine.py`:
  ```python
  def compute_diff(self, old: Snapshot | None, new: Snapshot) -> DiffResult:
      """Compute diff between two snapshots.
      
      Args:
          old: The old snapshot to compare (can be None)
          new: The new snapshot to compare
          
      Returns:
          DiffResult containing all differences
      """
      # Handle None case: use same snapshot for both
      if old is None:
          old = new
      
      # Get settings
      excluded_node_types = self._get_excluded_node_types()
      excluded_properties = self._get_excluded_properties()
      
      # Compare trees using TreeComparator
      return self._tree_comparator.compare_snapshots(old, new)
  ```
- [ ] Remove the old `compare()` method that took explicit excluded_types/properties (redundant now)
- [ ] **Update call sites**: Find all places calling `compute_diff()` and update to handle the new signature. This includes:
  - Application actions using DiffEngine
  - UI presenters orchestrating diff generation
  - Test files calling compute_diff()

### Phase 4.5: SnapshotExtractor - Simplify Interface

**Test First:**
- [ ] Write test: `SnapshotExtractor.extract_tree()` requires `DocumentLike` argument
- [ ] Write test: Existing extraction logic works unchanged

**Implementation:**
- [ ] Update `domain/snapshots/gui_extractor.py`:
  ```python
  class SnapshotExtractor:
      def __init__(self) -> None:
          """Initialize the extractor."""
          pass
      
      def extract_tree(self, doc: DocumentLike) -> Snapshot:
          """Extract the document tree structure.
          
          Args:
              doc: Required DocumentLike instance.
              
          Returns:
              A Snapshot object containing the document tree structure.
          """
          from .models import Snapshot
          
          document_name = getattr(doc, "Name", "Unnamed")
          
          try:
              # Initialize FreeCAD GUI and get GUI document for claimChildren()
              gui_doc = _init_gui_and_get_doc(doc)
              
              # Use single-pass BFS algorithm for better performance
              return _extract_tree_single_pass(doc, gui_doc, document_name)
          except Exception as e:
              Log.exception(f"Error extracting document tree: {e}")
          
          # Fallback: return empty snapshot with document name
          return Snapshot(
              snapshot_id=str(uuid.uuid4()),
              document_name=document_name,
              timestamp=datetime.now(),
              nodes=[],
              git_path=""
          )
  ```
- [ ] Update `_extract_tree_single_pass()` signature to remove port parameter
- [ ] Update all internal calls to pass doc directly instead of via port
- [ ] Update `__init__.py` exports if needed

### Phase 4.6: UI Tree Display - Show git_path as Top-Level Item

**Test First:**
- [ ] Write test: Tree widget displays git_path as top-level item
- [ ] Write test: Child nodes under top-level item match snapshot tree structure

**Implementation:**
- [ ] Update `ui/views/diff_panel_view.py` (or wherever tree widget is populated):
  - Find the code that populates the tree widget with diff results
  - Modify to use `DiffResult.new_snapshot.git_path` as the top-level item text
  - Child nodes remain the same (from the hierarchy)
  
  Example:
  ```python
  def display_diff_result(self, diff_result: DiffResult) -> None:
      """Display a DiffResult in the tree widget."""
      self._tree_widget.clear()
      
      # Get git_path for top-level item (use document_name as fallback)
      top_level_text = diff_result.new_snapshot.git_path or diff_result.new_snapshot.document_name
      
      # Create top-level item with git_path
      root_item = QTreeWidgetItem([top_level_text])
      
      # Add child nodes from hierarchy
      for node_diff in diff_result.hierarchy.roots:
          child_item = self._create_node_item(node_diff)
          root_item.addChild(child_item)
      
      self._tree_widget.addTopLevelItem(root_item)
      # ... rest of existing logic ...
  ```
- [ ] Test with multiple documents to verify each shows its git_path correctly

## Test Strategy

### Unit Tests (No FreeCAD)
- `Snapshot` model with new `git_path` field
- `DiffResult` model with Snapshot fields and warnings
- `TreeComparator.compare_snapshots()` with Snapshot inputs
- `DiffEngine.compute_diff()` with None handling
- `SnapshotExtractor.extract_tree()` with DocumentLike parameter
- All existing comparison logic unchanged (regression tests)

### Integration Tests (FreeCAD Required)
- Manual verification of UI tree display with git_path
- End-to-end: Extract snapshot → Compare → Display in UI

## Manual Test Cases

### ui/views/diff_panel_view.py
- **Git Path Display**: Open a document in a git repository, take a snapshot, compare with itself. Verify the tree widget shows the file path (e.g., "path/to/doc.FCStd") as the top-level item, not just the document name.
- **Fallback to Document Name**: Open an unsaved document or document outside git repo. Verify the tree widget falls back to showing the document name when git_path is empty.

### domain/snapshots/models.py
- **Snapshot with Git Path**: Create a Snapshot with git_path="myproject/docs/file.FCStd". Verify the string representation includes the path.
- **Snapshot without Git Path**: Create a Snapshot with empty git_path. Verify it still works correctly.

### domain/diff/models.py
- **DiffResult with Snapshots**: Create a DiffResult with two different Snapshot instances. Verify no warning is added.
- **Same Snapshot Warning**: Create a DiffResult with the same Snapshot instance for both old and new. Verify the warning list contains the appropriate message.
- **Multiple Warnings**: Add multiple warnings to a DiffResult. Verify all are preserved.

### domain/diff/comparator.py
- **Snapshot Comparison**: Compare two Snapshots using TreeComparator. Verify the result has correct counts and hierarchy.
- **Regression Test**: Compare Snapshots that previously worked. Verify results are unchanged.

### domain/diff/engine.py
- **None Old Snapshot**: Call compute_diff(None, snapshot). Verify it uses the same snapshot for both and adds a warning.
- **Normal Operation**: Call compute_diff(snapshot1, snapshot2). Verify normal operation works.

### domain/snapshots/gui_extractor.py
- **Extract with Document**: Extract tree from a DocumentLike object. Verify Snapshot is created with correct document_name.
- **Extract without Document**: Call extract_tree() with no arguments. Verify empty Snapshot is returned.

## Findings & Notes

### Architecture Rationale

**Why add git_path to Snapshot?**
- Snapshots are now tied to specific files in git repositories
- The git_path provides a stable identifier that works across commits
- Enables multi-document diffs by distinguishing snapshots from different files

**Why replace snapshot names with Snapshot objects?**
- Eliminates indirection: no need to look up snapshots by name
- Makes DiffResult self-contained with all necessary data
- Reduces coupling between layers (no external snapshot store needed)

**Why add warnings list?**
- Provides a simple mechanism for edge case reporting
- UI can display warnings (e.g., missing snapshot indicators)
- Extensible: more warning types can be added as needed

**Why change TreeComparator signature?**
- Encapsulates node extraction logic within the comparator
- Cleaner API: callers work with domain concepts (Snapshots), not implementation details (node lists)
- Consistent with DiffEngine pattern

**Why simplify SnapshotExtractor?**
- The port parameter was unnecessary abstraction for current usage
- Direct DocumentLike parameter is simpler and more Pythonic
- Can always add port injection later if needed for testing flexibility

### Migration Considerations

When implementing these changes:
1. Update models first (Snapshot, DiffResult) - lowest risk
2. Update TreeComparator - depends on model changes
3. Update DiffEngine - depends on comparator changes
4. Update SnapshotExtractor - independent of other changes
5. Update UI - depends on all domain changes
6. Update all call sites - last step, ensures everything compiles

### Backward Compatibility

This is a breaking change for any code outside the diff_wb module. However:
- This is early MVP development; breaking changes are acceptable
- All internal code will be updated together
- No external dependencies yet
