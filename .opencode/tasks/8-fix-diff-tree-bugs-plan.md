# Task: Fix Diff Tree Hierarchy and State Calculation Bugs

## Goal
Investigate and fix bugs causing incorrect tree hierarchy (too many roots, wrong parent-child relationships) and incorrect modification states (all nodes showing as modified when only VarSet changed).

## Context
User reports testing against `BasicFile.FCStd` file after implementing the comparator refactor. Issues observed:
1. Every node appearing as root level instead of proper hierarchy under Part
2. Wrong parent-child relationships (e.g., Pad appearing as child of Sketch001)
3. All nodes except Part showing as MODIFIED despite only VarSet being updated

## Architecture Impact
**Likely Affected Files:**
- `freecad/diff_wb/domain/diff/comparator.py` - Hierarchy reconstruction logic
- `freecad/diff_wb/domain/snapshots/extractor.py` - Tree extraction from FreeCAD
- `freecad/diff_wb/domain/tree/node.py` - TreeNode path construction
- Integration with FreeCAD runtime

## Investigation Plan

### Phase 1: Reproduce the Issue with Debug Logs
- [ ] Add debug logging to `_build_hierarchical_diffs()` to trace:
  - Sorted paths being processed
  - Parent path calculations for each node
  - Whether parent lookup succeeds/fails
  - Child-to-parent linking results
- [ ] Add debug logging to `compare_snapshots()` to show:
  - Old index paths vs New index paths
  - Added/deleted/common path sets
  - Root nodes returned
- [ ] Add debug logging to extractor to show:
  - Paths being constructed for each TreeNode
  - OutList and getSubObjects results
- [ ] Run comparison on BasicFile.FCStd and capture logs

### Phase 2: Analyze Log Output
- [ ] Check if old/new snapshot paths match in format
- [ ] Verify parent_path calculations are correct
- [ ] Confirm parent lookups succeed in diff_by_path dict
- [ ] Check if NodeDiff state calculation is working correctly
- [ ] Identify where hierarchy breaks down

### Phase 3: Fix Identified Bugs
Based on findings, fix issues such as:
- Path format inconsistencies
- Parent lookup failures
- Incorrect state calculation logic
- Tree extraction hierarchy errors

### Phase 4: Verification
- [ ] Write unit tests for identified bug scenarios
- [ ] Verify fix with BasicFile.FCStd
- [ ] Run full test suite

## Questions for User
Before adding logs, can you confirm:
1. Are you using the same settings/exclusions for both snapshots?
2. Did you create both snapshots from the same document, or different documents?
3. What does the actual output look like? Can you share a snippet of the diff tree structure?

## Findings & Notes
[To be filled after investigation]
