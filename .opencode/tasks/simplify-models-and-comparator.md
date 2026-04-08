# Task: Simplify DiffResult models and remove unused comparator methods

## Goal
Clean up the recent changes to `models.py` and `comparator.py` by:
1. Removing `node_diffs` from `DiffResult` (use `DiffHierarchy` instead)
2. Making `_add_node_and_children` non-static (or removing it entirely if not needed)
3. Adding an error in `DiffHierarchy.add_node()` when parent segments don't exist
4. Removing unused legacy methods from `comparator.py`

## Context
The recent staged changes added `DiffHierarchy` and related code to `models.py`, but:
- `DiffResult` still has `node_diffs` which is redundant since we have `DiffHierarchy`
- `_add_node_and_children` is static but only used internally
- The comment "First, ensure all parent segments have dict containers" should be an error
- `comparator.py` has many legacy path-based methods that are no longer used

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Remove `node_diffs` field entirely | We now have `DiffHierarchy` which provides `roots` property. No backwards compatibility needed. | Keep both, but that adds confusion |
| Remove `_add_node_and_children` method | Only used in `DiffResult.__post_init__` to build hierarchy from `node_diffs`. Since we're removing `node_diffs`, this method is no longer needed. | Make it non-static, but it's not used anywhere else |
| Add error in `DiffHierarchy.add_node()` | If a parent path doesn't exist, it should be an error - parents must be created first (sorted by path depth) | Silently add to roots, but that breaks hierarchy |
| Remove unused comparator methods | These are legacy path-based methods replaced by ID-based approach in new `compare_snapshots` | Keep for debugging, but clutters code |

## Architecture Impact
- **models.py**: Simplify `DiffResult` class - remove `node_diffs`, `__post_init__`, and `_add_node_and_children`
- **models.py**: Update `DiffHierarchy.add_node()` to raise error instead of silently creating dicts
- **comparator.py**: Remove ~15 unused legacy methods

## FreeCAD Dependency
- [x] No FreeCAD required (pure code changes)

## Implementation Plan

### Phase 1: Simplify DiffResult in models.py
- [x] Remove `node_diffs` field from `DiffResult` dataclass
- [x] Remove `__post_init__` method that built hierarchy from node_diffs
- [x] Remove `_add_node_and_children` static method (no longer needed)
- [x] Update `has_changes` property to use `self.hierarchy.roots` instead of `self.node_diffs`
- [x] Update `get_all_changed_paths` to use `self.hierarchy.roots`
- [x] Remove `node_diffs` from `__all__` export

### Phase 2: Add error in DiffHierarchy.add_node()
- [x] Find the comment "First, ensure all parent segments have dict containers"
- [x] Replace it with a `ValueError` that says parents must be created first
- [x] The error should be raised when a parent path doesn't exist in the hierarchy

### Phase 3: Remove unused methods from comparator.py
- [x] Remove `_build_id_index` (replaced by inline dict comprehension)
- [x] Remove `_find_added_ids`, `_find_deleted_ids`, `_find_common_ids` (replaced by set operations inline)
- [x] Remove `_build_path_index` (legacy, unused)
- [x] Remove `_find_added_paths`, `_find_deleted_paths`, `_find_common_paths` (legacy, unused)
- [x] Remove `_compare_nodes_by_path` (replaced by `_compare_nodes_by_id`)
- [x] Remove `_create_added_node_diff_by_path` (replaced by `_create_added_node_diff`)
- [x] Remove `_create_deleted_node_diff_by_path` (replaced by `_create_deleted_node_diff`)
- [x] Remove `_create_placeholder` (legacy hierarchy method)
- [x] Remove `_ensure_placeholder` (legacy hierarchy method)
- [x] Remove `_build_hierarchical_diffs` (legacy method)
- [x] Remove `_build_hierarchical_diffs_from_ids` (was added but not used in final code)
- [x] Remove `_create_node_diffs_for_ids` (not used)
- [x] Remove `_filter_excluded_descendants` (not used)

### Phase 4: Run tests
- [x] Run `task test` to verify changes don't break anything
- [x] Run `task check` for linting

## Test Strategy
- **Unit tests**: Run existing tests to ensure the simplified code works correctly
- No new tests needed - we're removing code, not adding features

## Findings & Notes
- The new `compare_snapshots` in comparator.py uses a simpler approach: sort nodes by path length, process old nodes for deleted/modified, process new nodes for added, then build hierarchy
- `DiffHierarchy.add_node()` is called after sorting NodeDiffs by path length, so parents should always exist first - the error ensures this contract is maintained