# Task: Fix Property Viewer Not Displaying on Node Click

## Goal
Fix the bug where clicking a node in the diff tree view does not display its properties in the property viewer panel.

## Context
When users click "Working Tree" or select commits, multiple documents may be displayed with their diff trees. Clicking any node in these trees should show the property differences for that node, but currently nothing happens because:

1. The presenter stores multiple `DiffResult` objects in `_diff_results_by_path` dict when displaying multiple documents
2. The `on_node_selected()` method only looks at `self._diff_result` (singular), which is never set when using `present_diffs()`
3. The tree widget callback only passes the node path, not the document identifier needed to look up the correct `DiffResult`
4. Root items don't store `git_path` in their data (currently no `UserRole` data is set for root items)

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use `git_path` and `node_path` as parameter names | Clear distinction between document identifier and node path within that document | Could use `document_id` but `git_path` already exists in the codebase and is the actual key used |
| Store `git_path` directly in root item's `UserRole` | Root items currently have no UserRole data, so we can use it directly (no need for `UserRole + 1`) | Using `UserRole + 1` would work but is unnecessary since UserRole is available |
| Move callback logic into the view | View knows its own data structure; keeps view-specific QTreeWidgetItem logic in the view layer | Putting logic in composer violates separation of concerns |
| Single-phase implementation | Changes are localized to presenter and view wiring; no API exploration needed | Could split into discovery + fix phases, but the bug is clear from code review |

## Architecture Impact
- **Modified files:**
  - `freecad/diff_wb/ui/presenters/diff_presenter.py` - Update `on_node_selected()` signature and logic
  - `freecad/diff_wb/ui/views/diff_panel_view.py` - Add `set_node_selection_callback()`, store git_path in root items
  - `freecad/diff_wb/ui/composer.py` - Wire up new callback method (minimal change)
- **No changes to:** Domain layer, actions, or FreeCAD integration

## FreeCAD Dependency
- [x] No FreeCAD required (pure code path)
- [ ] FreeCAD required (follow exploration phase)

This is a pure UI/presenter fix that can be tested with existing unit tests and fakes.

## Implementation Plan

### Phase 1: Fix Node Selection Callback Chain

**Test First** - Write tests to validate the fix before implementing:

- [ ] Add test `test_on_node_selected_with_git_path` - Verify correct DiffResult lookup when multiple documents present
- [ ] Add test `test_on_node_selected_uses_correct_document_context` - Verify node_path is looked up in correct document hierarchy
- [ ] Update existing `test_transform_property_diffs_includes_children` to pass both git_path and node_path parameters

**Implementation** - Update the callback chain to pass both parameters:

1. **Update `diff_presenter.py` - `on_node_selected()` method:**
   Change signature from `(self, path: str)` to `(self, git_path: str, node_path: str)`:
   ```python
   def on_node_selected(self, git_path: str, node_path: str) -> None:
       """Handle tree node selection to display property diffs.
       
       Args:
           git_path: The document path (key in _diff_results_by_path)
           node_path: The path of the selected node within that document
       """
       # Guard: No diff results stored
       if not self._diff_results_by_path:
           self._view.show_property_diff([])
           return
       
       # Look up the correct DiffResult for this document
       diff_result = self._diff_results_by_path.get(git_path)
       if diff_result is None:
           Log.debug(f"[PRESENTER] No DiffResult found for git_path: {git_path}")
           self._view.show_property_diff([])
           return
       
       # Find NodeDiff by path within this document's hierarchy
       node_diff = diff_result.hierarchy.find_by_path(node_path)
       
       # If not found, clear properties
       if node_diff is None:
           Log.debug(f"[PRESENTER] NodeDiff not found for path: {node_path} in document {git_path}")
           self._view.show_property_diff([])
           return
       
       # Transform and display property diffs
       properties = self._transform_property_diffs(node_diff)
       Log.debug(f"[PRESENTER] Transformed to {len(properties)} PropertyPresentation")
       self._view.show_property_diff(properties)
   ```

2. **Update `diff_panel_view.py` - Store git_path and add callback wiring:**
   
   In `show_diff_trees()` method, after creating root_item (around line 554):
   ```python
   # Create root item
   root_item = QTreeWidgetItem([top_level_text])
   # Store git_path in root item's UserRole for later retrieval when children are clicked
   root_item.setData(0, Qt.ItemDataRole.UserRole, diff.git_path)
   if warning_text:
       root_item.setToolTip(0, warning_text)
   ```
   
   Add new methods to handle node selection callback:
   ```python
   def set_node_selection_callback(self, callback: Callable[[str, str], None]) -> None:
       """Set callback for node selection with (git_path, node_path).
       
       Args:
           callback: A callable receiving (git_path, node_path) when a node is clicked.
       """
       self._on_node_selection_callback = callback
       # Connect to internal handler that extracts both values
       self.tree_widget.itemClicked.connect(self._on_tree_item_clicked)
   
   def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
       """Extract git_path from root and node_path from clicked item, then invoke callback.
       
       Args:
           item: The clicked tree item
           column: The column that was clicked
       """
       if self._on_node_selection_callback is None:
           return
       
       # Extract node_path from clicked item (set in _create_tree_item)
       node_path = item.data(0, Qt.ItemDataRole.UserRole)
       
       # Walk up to find root item and extract git_path
       root = item
       while root.parent():
           root = root.parent()
       git_path = root.data(0, Qt.ItemDataRole.UserRole)
       
       if git_path and node_path:
           self._on_node_selection_callback(git_path, node_path)
   ```

3. **Update `composer.py` - Wire up the new callback:**
   Replace the existing lambda-based wiring with the new method:
   ```python
   # Remove the old lambda connection
   # view.tree_widget.itemClicked.connect(...)
   
   # Use the new callback method
   view.set_node_selection_callback(diff_presenter.on_node_selected)
   ```

**Code Snippet - View Callback Pattern:**
```python
# In diff_panel_view.py:
def set_node_selection_callback(self, callback: Callable[[str, str], None]) -> None:
    """Set callback for node selection."""
    self._on_node_selection_callback = callback
    self.tree_widget.itemClicked.connect(self._on_tree_item_clicked)

def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
    """Extract both git_path and node_path from tree structure."""
    if self._on_node_selection_callback is None:
        return
    
    node_path = item.data(0, Qt.ItemDataRole.UserRole)
    
    # Walk up to root to get document git_path
    root = item
    while root.parent():
        root = root.parent()
    git_path = root.data(0, Qt.ItemDataRole.UserRole)
    
    if git_path and node_path:
        self._on_node_selection_callback(git_path, node_path)
```

## Test Strategy
- **Unit tests**: Use FakeDiffView to verify `show_properties()` is called with correct data
- **Existing tests**: Update `test_transform_property_diffs_includes_children` to pass both git_path and node_path parameters
- **New tests**: 
  - Test `set_node_selection_callback()` wiring in view
  - Test `_on_tree_item_clicked()` extracts both values correctly
  - Validate correct DiffResult lookup when multiple documents present
- **Manual testing**: Click nodes in multi-document diff view to verify properties display

## Findings & Notes
- The bug was introduced when support for multiple documents was added (`present_diffs()`) but `on_node_selected()` wasn't updated to handle the multi-document case
- Root items currently have NO UserRole data set, so we can use `UserRole` directly for storing `git_path` (no need for `UserRole + 1`)
- The fix maintains backward compatibility - single document case still works because `_diff_results_by_path` will have one entry
- Moving callback logic into the view keeps view-specific QTreeWidgetItem handling in the view layer, following proper separation of concerns
- Variable rename from `path` to `node_path` clarifies intent and prevents confusion with `git_path`
