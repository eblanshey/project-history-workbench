# Task: Core Domain Implementation

## Goal
Implement pure Python domain models for the Diff Workbench that can be tested without FreeCAD runtime.

## Context
Phase 2 of the implementation plan requires creating core domain objects (Snapshot, TreeNode, PropertyValue, DiffResult types) that form the foundation of the diff workbench. These models must have zero FreeCAD dependencies to enable comprehensive unit testing.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| **Merged Tree Diff Approach** (DiffState enum) | Simplifies UI rendering - one tree with color coding instead of separate lists for added/deleted/modified | Separate lists would require more complex UI merging logic |
| **Tiered Filtering Strategy** | Auto-excluded properties prevent immediate frustration; user-configurable provides flexibility without complexity upfront | Single tier would either miss common noise sources or add premature complexity |
| **Pure Python Domain Models** | Enables unit testing without FreeCAD runtime; clear boundaries between domain and infrastructure | Tightly coupled models would make testing harder and obscure domain logic |
| **ExpressionEngine Parsing** | ExpressionEngine provides complete expression data in one call; more efficient than querying each property | getExpression() method would require iterating all properties individually |
| **Approximate Float Equality** (1e-6 tolerance) | Prevents false positives from floating point rounding errors; matches user expectations | Exact equality would cause spurious diff results |
| **Frozen Dataclasses** | Prevents accidental mutations; makes models hashable; signals intent as value objects | Mutable classes could lead to state corruption bugs |

## Architecture Impact
- **New files**: `freecad/diff_wb/domain/placement.py`, `freecad/diff_wb/domain/property_value.py`, `freecad/diff_wb/domain/snapshot.py`, `freecad/diff_wb/domain/diff_result.py`
- **Modified files**: `freecad/diff_wb/config.py` (added auto-excluded properties), `freecad/__init__.py` (namespace package marker for testing)
- **Test files**: `tests/unit/test_domain.py`

## FreeCAD Dependency
- [x] No FreeCAD required (pure code)

## Implementation Plan
### Phase 1: Configuration
- [x] Add AUTO_EXCLUDED_PROPERTIES constant to config.py
- [x] Add EXCLUDED_TYPES constant to config.py

### Phase 2: Core Models
- [x] Create Vector, Rotation, Placement classes with approximate equality
- [x] Create PropertyType enum and PropertyValue class
- [x] Create TreeNode dataclass
- [x] Create Snapshot dataclass
- [x] Create DiffState enum
- [x] Create PropertyDiff, NodeDiff, DiffSummary, DiffResult classes

### Phase 3: Testing
- [x] Write unit tests for placement comparisons
- [x] Write unit tests for property value equality
- [x] Write unit tests for diff result computation
- [x] Fix package import issues for tests
- [x] Verify all 48 tests pass

### Phase 4: Documentation
- [x] Document architectural decisions in task plan
- [ ] Move ADRs to PLAN.md after task completion

## Test Strategy
- Unit tests: All domain models tested with pytest using only stdlib types
- No integration tests needed - pure Python with no FreeCAD dependencies

## Findings & Notes

### Bug Fix: Frozen Dataclass Mutation
When implementing DiffSummary.compute(), initially tried to mutate the frozen dataclass directly. Fixed by using local accumulators and constructing final instance at end:
```python
@classmethod
def compute(cls, diff_result: "DiffResult") -> "DiffSummary":
    total_nodes = 0
    added_nodes = 0
    deleted_nodes = 0
    modified_nodes = 0
    unchanged_nodes = 0
    total_property_changes = 0
    
    # ... accumulate values ...
    
    return cls(
        total_nodes=total_nodes,
        added_nodes=added_nodes,
        # ... etc
    )
```

### Bug Fix: has_changes Logic
Original implementation only checked added/deleted paths. Fixed to include modified_nodes:
```python
@property
def has_changes(self) -> bool:
    return (
        len(self.added_paths) > 0 
        or len(self.deleted_paths) > 0 
        or self.summary.modified_nodes > 0  # Added this check
    )
```

### Package Import Issue
Tests couldn't import freecad.diff_wb because freecad namespace package lacked __init__.py. Fixed by:
1. Creating `freecad/__init__.py` (empty, namespace marker)
2. Changing pyproject.toml packages from "freecad/diff_wb" to "freecad"