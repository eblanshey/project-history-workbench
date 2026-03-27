# Task: Refactor Tree Comparator to Single-Pass Hierarchical Construction

## Goal
Replace the current 6-pass tree reconstruction algorithm with a clean single-pass approach that builds the hierarchy incrementally while creating NodeDiff objects, eliminating redundant work and fixing path format bugs.

## Context
The current implementation has several issues:

1. **Inefficient Multi-Pass Design**: The algorithm performs 6+ passes over the data:
   - Pass 1: Build parent-child relationships for existing diffs
   - Pass 2: Collect root nodes
   - Pass 3: Collect all paths recursively
   - Pass 4: Create missing ancestors
   - Pass 5: Re-sort all diffs including new placeholders
   - **Pass 6: Clear ALL children and rebuild relationships** ← Major inefficiency!

2. **Path Format Bug**: When creating ancestor paths from `/Body/Pad`, the code strips leading slashes, creating `Body` instead of `/Body`. This causes lookup failures against indices containing `/Body`, resulting in `type_id="Unknown"`.

3. **Code Complexity**: Two separate methods (`_reconstruct_hierarchy` and `_insert_missing_ancestors`) with overlapping responsibilities make the code harder to understand and maintain.

**Key Insight**: Sorting paths once ensures parents are processed before children. During iteration, we can ensure parent placeholders exist and link children immediately—no post-processing needed.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Single-pass hierarchical construction during diff creation | Eliminates 5 redundant passes, simpler code, better performance | Keep multi-pass design (current), separate hierarchy building phase |
| Preserve original path format (with or without leading slash) | Robust to both legacy data and new data, no normalization needed | Normalize all paths to one format at entry point |
| Recursive `_ensure_placeholder` approach | Python's recursion limit (1000) far exceeds FreeCAD tree depth (<100 levels) | Iterative stack-based approach (more complex, unnecessary for FreeCAD) |
| Standardize integration tests on no-leading-slash format | Matches real FreeCAD output from `extractor.py`, reduces confusion | Keep leading slashes in test data |
| Do not change public API | Maintain backward compatibility with existing callers | Change method signatures |

## Architecture Impact
**Modified Files:**
- `freecad/diff_wb/domain/diff/comparator.py`
  - Replace `_reconstruct_hierarchy` with integrated single-pass approach
  - Remove `_insert_missing_ancestors` method entirely
  - Add `_get_parent_path` helper method (preserves path format)
  - Add `_ensure_placeholder` helper method (recursive placeholder creation)
  - Update `compare_snapshots` to use new approach

**Unchanged Files:**
- `freecad/diff_wb/domain/diff/models.py` (NodeDiff interface unchanged)
- All consumers of TreeComparator (public API unchanged)

## FreeCAD Dependency
- [x] No FreeCAD required (pure code)

The refactoring is purely algorithmic—no FreeCAD API calls involved. The path format already matches what FreeCAD extraction produces (no leading slashes).

## Implementation Plan

### Phase 1: Add Helper Methods
- [x] Write tests for `_get_parent_path()` with various path formats:
  - `/Body/Pad` → `/Body`
  - `Body/Pad` → `Body`
  - `/Part` → `` (root node, no parent)
  - `Part` → `` (root node, no parent)
- [x] Implement `_get_parent_path()` that preserves leading slash format
- [x] Write tests for `_ensure_placeholder()` recursive behavior
- [x] Implement `_ensure_placeholder()` that creates ancestor placeholders with correct type_id

### Phase 2: Refactor compare_snapshots to Single-Pass
- [x] Write tests for new single-pass hierarchy construction:
  - Simple case: one changed child, missing parent becomes placeholder
  - Deep nesting: multiple missing ancestors all created
  - Mixed states: added, deleted, modified nodes properly linked
  - Path format preservation: leading slashes maintained throughout
- [x] Refactor `compare_snapshots()` to build hierarchy during iteration:
  - Sort paths once at the start
  - For each path: create diff, ensure parent exists, link child to parent
  - Remove call to `_reconstruct_hierarchy`
- [x] Remove `_reconstruct_hierarchy` and `_insert_missing_ancestors` methods
- [x] Verify all existing unit tests still pass

### Phase 3: Standardize Test Data
- [x] Update integration test data in `test_compare_snapshots_integration.py`:
  - Remove leading slashes from all path values
  - Match format used by real FreeCAD extraction
- [x] Update test expectations to match corrected path format
- [x] Run full test suite to verify nothing broken

## Test Strategy
**Unit Tests** (`tests/unit/domain/diff/test_comparator.py`):
- Test `_get_parent_path()` with various inputs
- Test single-pass hierarchy construction edge cases
- Test placeholder creation with correct type_id resolution
- Test path format preservation (leading slash or not)

**Integration Tests** (`tests/unit/application/actions/test_compare_snapshots_integration.py`):
- Update test data to use no-leading-slash format
- Verify correct hierarchy with placeholder parents
- Verify type_id correctly resolved from indices
- All 10 existing tests should pass with updated expectations

**Performance Verification**:
- Benchmark with large trees (1000+ nodes) to confirm O(n log n) performance
- Verify no regression in comparison time

## Findings & Notes

### Current Algorithm Analysis
| Pass | Work Done | Problem |
|------|-----------|---------|
| 1 | Build parent-child links | **Discarded later** |
| 2 | Collect root nodes | Necessary |
| 3 | Collect all paths | Necessary |
| 4 | Create missing ancestors | Necessary |
| 5 | Re-sort all diffs | Necessary after adding placeholders |
| 6 | **Clear ALL children + rebuild** | **Major inefficiency—undoes Pass 1!** |

**Total: 6 passes with ~5× redundant work**

### Proposed Algorithm Complexity
- Sort: O(k log k) where k = number of changed paths
- Single pass iteration: O(k × avg_depth)
- **Total: O(k log k + k × avg_depth)** with no wasted passes

### Path Format Issue Details
```python
# Current buggy code (line 324-330):
path_parts = [p for p in path.split("/") if p]  # ['', 'Body', 'Pad'] → ['Body', 'Pad']
ancestor_path = "/".join(path_parts[:i])         # Creates 'Body' instead of '/Body'
# Lookup fails: old_index.get('Body') returns None when index has '/Body'

# Fixed code:
has_leading_slash = child_path.startswith("/")
parts = [p for p in child_path.split("/") if p]
parent_path = "/".join(parts[:-1])
return "/" + parent_path if has_leading_slash else parent_path
```

### Why Sorting Is Needed
Sorting ensures parents are processed before children. Without sorting:
- Processing `/Body/Pad` before `/Body` would create a placeholder for Body
- Later processing the real Body diff would require reconciliation
- Children might already be linked to wrong placeholder

With sorting (`/Body` before `/Body/Pad`), parents always exist when children are processed.

### Recursion Depth Safety
- Python default recursion limit: 1000 frames
- FreeCAD typical tree depth: <20 levels
- Worst-case FreeCAD tree: ~50-100 levels
- **Conclusion**: Recursive approach is safe for all FreeCAD use cases

### New Single-Pass Algorithm

The new algorithm builds the hierarchy incrementally as each NodeDiff is created, eliminating all redundant passes.

#### Core Idea
Instead of creating all NodeDiff objects first, then making multiple passes to reconstruct the hierarchy, the new algorithm processes paths in sorted order and builds parent-child relationships **as it goes**. Since paths are sorted before processing, parents are guaranteed to exist when children are processed.

#### Step-by-Step Algorithm

```
Input: old_index, new_index, added_paths, deleted_paths, common_paths
Output: hierarchical list of NodeDiff objects

1. COLLECT ALL CHANGED PATHS
   all_paths = added_paths ∪ deleted_paths ∪ common_paths_with_changes

2. SORT PATHS (ensures parents before children)
   sorted_paths = sorted(all_paths, key=lambda p: p.split("/"))
   Example: ["Body", "Body/Pad", "Body/Pocket", "Body/Pad/Sketch"]

3. INITIALIZE
   diff_by_path = {}    # dict[str, NodeDiff] for O(1) lookups
   has_parent = set()   # Track which nodes have been linked to a parent

4. ITERATE THROUGH SORTED PATHS (single pass)
   for path in sorted_paths:
       a. CREATE NodeDiff for this path
          - if path in added_paths: create ADDED diff from new_index
          - if path in deleted_paths: create DELETED diff from old_index
          - if path in common_paths: compare properties, create MODIFIED diff

       b. ENSURE PARENT EXISTS
          parent_path = get_parent_path(path)
          if parent_path and parent_path not in diff_by_path:
              ensure_placeholder(parent_path, old_index, new_index, diff_by_path, has_parent)

       c. LINK CHILD TO PARENT
          if parent_path and parent_path in diff_by_path:
              parent = diff_by_path[parent_path]
              parent.children.append(node_diff)
              has_parent.add(path)

       d. REGISTER IN INDEX
          diff_by_path[path] = node_diff

5. RETURN ROOT NODES
   roots = [diff for diff in diff_by_path.values() if diff.path not in has_parent]
   return roots
```

#### Helper: get_parent_path(path)
```
Input: path string (e.g., "Body/Pad" or "/Body/Pad")
Output: parent path (e.g., "Body" or "/Body")

has_leading_slash = path.startswith("/")
parts = [p for p in path.split("/") if p]  # Remove empty segments
if len(parts) <= 1:
    return ""  # Root node, no parent
parent_parts = parts[:-1]
parent_path = "/".join(parent_parts)
return "/" + parent_path if has_leading_slash else parent_path
```

#### Helper: ensure_placeholder(path, old_index, new_index, diff_by_path, has_parent)
```
Input: path to ensure exists, indices, diff registry, has_parent tracker
Output: None (creates placeholder in-place)

if path in diff_by_path:
    return  # Already exists

# Recursively ensure parent exists first
parent_path = get_parent_path(path)
if parent_path:
    ensure_placeholder(parent_path, old_index, new_index, diff_by_path, has_parent)

# Look up type_id from indices
old_node = old_index.get(path)
new_node = new_index.get(path)
type_id = old_node.type_id if old_node else (new_node.type_id if new_node else "Unknown")

# Create placeholder with UNCHANGED state
placeholder = NodeDiff(path=path, type_id=type_id, property_diffs=[], children=[])
diff_by_path[path] = placeholder

# Link to parent if exists
if parent_path and parent_path in diff_by_path:
    parent = diff_by_path[parent_path]
    parent.children.append(placeholder)
    has_parent.add(path)
```

#### Visual Example

Given changes at paths: `Body/Pocket`, `Body/Pad/Sketch`

```
Processing "Body/Pocket":
  - Create NodeDiff(path="Body/Pocket", state=ADDED)
  - Parent = "Body" → not in diff_by_path
  - ensure_placeholder("Body") creates UNCHANGED placeholder
  - Link Body/Pocket → Body.children
  - diff_by_path = {Body: placeholder, Body/Pocket: diff}

Processing "Body/Pad/Sketch":
  - Create NodeDiff(path="Body/Pad/Sketch", state=ADDED)
  - Parent = "Body/Pad" → not in diff_by_path
  - ensure_placeholder("Body/Pad") creates UNCHANGED placeholder
  - ensure_placeholder("Body") → already exists, skip
  - Link Body/Pad/Sketch → Body/Pad → Body
  - diff_by_path = {Body, Body/Pocket, Body/Pad, Body/Pad/Sketch}

Final result: Body (root) with children [Body/Pocket, Body/Pad[Body/Pad/Sketch]]
```

#### Complexity Analysis

| Operation | Complexity |
|-----------|------------|
| Collect paths | O(k) |
| Sort paths | O(k log k) |
| Single-pass iteration | O(k × d) where d = tree depth |
| Parent lookups | O(1) each (dict) |
| **Total** | **O(k log k + k × d)** |

- k = number of changed paths (typically << total nodes)
- d = tree depth (typically < 20 for FreeCAD)
- **No redundant passes** - each node processed exactly once

#### Key Differences from Old Algorithm

| Aspect | Old Algorithm | New Algorithm |
|--------|---------------|---------------|
| Passes | 6+ passes | 1 pass |
| Parent lookup | Re-scans all nodes | O(1) dict lookup |
| Placeholder creation | Separate phase after diff creation | Incremental during iteration |
| Redundant rebuild | Clears and rebuilds ALL children | No rebuild needed |
| Code complexity | 2 methods with overlapping logic | Single clear flow |
