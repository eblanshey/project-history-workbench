# Task: Simplify Comparator Algorithm & Consolidate Diff Results

## Goal
Replace the existing TreeComparator algorithm with the user's optimized algorithm and consolidate DiffResult/TreeDiffResult into a single class while removing DiffSummary.

## Context
The current implementation has:
- `TreeComparator` with O(n*m) filtering for excluded types (string prefix checks in `_filter_excluded_descendants`)
- Separate `TreeDiffResult` (from comparator) and `DiffResult` (from engine)
- `DiffSummary` class that computes counts by traversing the tree

The new algorithm:
1. Index both snapshots by ID and path (O(n+m))
2. Track `old_node_ids` set for O(1) added/deleted detection
3. Inline exclusion filtering with O(1) set lookups
4. Track counts during iteration (replaces DiffSummary)
5. Sort by path depth and build hierarchy

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Keep ID index for matching | Matches new algorithm, enables ID tracking for debugging | Path-only matching (loses ID tracking) |
| Remove DiffSummary | Counts are tracked during iteration - no need for tree traversal | Keep DiffSummary as deprecated |
| Consolidate TreeDiffResult into DiffResult | Single source of truth, simpler API | Keep separate (more refactoring) |

## Architecture Impact
- **Files modified**: `comparator.py`, `models.py`, `engine.py`
- **Models removed**: `DiffSummary`, `TreeDiffResult`
- **Models modified**: `DiffResult` (add counts fields)
- **Engine simplified**: No longer needs to wrap TreeDiffResult in DiffResult

## FreeCAD Dependency
- [x] No FreeCAD required (pure code path)

## Implementation Plan

### Phase 1: Create DiffHierarchy class and update DiffResult
- [x] Create DiffHierarchy class in models.py:
  - Holds hierarchical node diffs as nested dict
  - Method find_by_path(path: str) -> NodeDiff | None
  - Method add_node(node_diff: NodeDiff) -> None (handles parent linking)
  - Property roots: list of top-level NodeDiffs
- [x] Add `added_count`, `deleted_count`, `modified_count` fields to DiffResult
- [x] Add DiffHierarchy field to DiffResult
- [x] Remove DiffSummary dependency from DiffResult

### Phase 2: Write tests for new TreeComparator algorithm
- [x] Write tests for added nodes
- [x] Write tests for deleted nodes
- [x] Write tests for modified nodes (property changes)
- [x] Write tests for move detection (old_path vs new_path)
- [x] Write tests for reorder detection (old_after vs new_after)
- [x] Write tests for excluded types filtering
- [x] Write tests for excluded parent path filtering
- [x] Write tests for empty snapshots

### Phase 3: Implement new TreeComparator algorithm
- [x] Implement new `compare_snapshots` method:
  1. Sort both snapshots by path length (parents first)
  2. Build id_index_new (by ID)
  3. Iterate old nodes → create diffs, track counts, handle exclusions
  4. Iterate new nodes NOT in old_node_ids → added nodes
  5. Sort NodeDiffs by path length
  6. Build hierarchy using DiffHierarchy.add_node()
- [x] Return DiffResult with DiffHierarchy and counts

### Phase 4: Update engine and remove TreeDiffResult
- [x] Update DiffEngine to use new return type
- [x] Remove TreeDiffResult class from comparator.py
- [x] Update __all__ exports

### Phase 5: Update production code to use new DiffResult format
- [x] Update DiffPresenter.present_diff():
  - Use `diff_result.hierarchy.roots` instead of `diff_result.node_diffs`
  - Use `diff_result.added_count` etc. instead of `diff_result.summary.*`
- [x] Update DiffPresenter._find_node_diff_by_path():
  - Use `diff_result.hierarchy.find_by_path(path)` instead of recursive search
- [x] Update DiffResult.has_changes to use new count fields

### Phase 6: Cleanup DiffSummary references
- [x] Remove DiffSummary class from models.py
- [x] Remove DiffSummary imports from tests
- [x] Update any remaining code using diff_result.summary

## Test Strategy
- **Unit tests**: Test new TreeComparator algorithm with various scenarios:
  - Added nodes
  - Deleted nodes
  - Modified nodes (property changes)
  - Move detection (path changes)
  - Reorder detection (after changes)
  - Excluded types filtering
  - Excluded parent path filtering
  - Empty snapshots
- **Unit tests**: Test DiffResult counts are correct

## Algorithm Complexity Comparison

| Step | Existing | New |
|------|----------|-----|
| Index by ID | O(n+m) | O(n+m) |
| Filter excluded types | O(n*m) prefix checks | O(n+m) inline set |
| Sort | O(n log n) | O(n log n) |
| Hierarchy building | O(n) | O(n) |
| **Total** | O(n log n + n*m) | O((n+m) log (n+m)) |

## New Algorithm Details

```
Given two snapshots with flat hierarchy, with "path" and "after" nodes, ordered by node id

Steps:

1. Sort both snapshots by path length (shortest first: "Body" before "Body/Pad" before "Body/Pad/Sketch")
   - This ensures parents are processed before children for exclusion logic

2. Build ID index:
   - id_index_new: dict[int, TreeNode] (by ID, for matching old nodes to new)

3. Create node diffs:
   added_count = 0
   deleted_count = 0
   modified_count = 0
   old_node_ids = set()
   paths_excluded = set()

   For each OLD node (in sorted order - parents first):
     - add node.id to old_node_ids set
     - if node type in EXCLUDED_TYPES, add path to paths_excluded, continue
     - if parent path in paths_excluded, add path to paths_excluded, continue
     - get matching new node by id
     - create node diff (records old_path, new_path, old_after, new_after)
     - if no matching new node: deleted_count += 1
     - else: modified_count += 1

   For each NEW node NOT in old_node_ids (in sorted order - parents first):
     - if node type in EXCLUDED_TYPES, add path to paths_excluded, continue
     - if parent path in paths_excluded, add path to paths_excluded, continue
     - create node diff with null old node
     - added_count += 1

   Result: flat list of NodeDiff objects

4. Create DiffHierarchy class:
   - Holds hierarchical node diffs as nested dict
   - Method find_by_path(path: str) -> NodeDiff | None:
     - Split path by "/" → segments
     - Traverse the hierarchy dict by segments
     - Return NodeDiff at end, or None if not found
   - Method add_node(node_diff: NodeDiff) -> None:
     - Split path by "/" to get segments
     - Find parent by traversing all but last segment
     - If parent exists, add node_diff to parent's children
     - If no parent (root), add to roots list
     - Store node_diff at its path in hierarchy dict

5. Build hierarchy:
   - Create DiffHierarchy instance
   - For each NodeDiff (in sorted order, parents first):
     - hierarchy.add_node(node_diff)  # handles parent linking automatically

6. Return DiffResult with DiffHierarchy (contains roots + find_by_path), counts
```

## Findings & Notes
- New algorithm eliminates O(n*m) prefix checks in filtering
- Move detection works via old_path vs new_path comparison
- Reorder detection works via old_after vs new_after comparison
- Counts are computed in single pass, no tree traversal needed