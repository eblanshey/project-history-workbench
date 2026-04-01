# Task: Refactor Diff Architecture - Move Child Property Diffing to Domain

## Goal
Eliminate duplicated diffing logic by moving all comparison and expansion logic to the domain layer. The UI layer should only render pre-computed data. Also simplify unnecessary complexity in the UI.

## Context
The domain layer computes high-level property diffs (PropertyDiff), but when a property has expandable children (Placement → Position/Rotation, Constraints list), the UI re-computes the children's states. This violates Single Responsibility Principle and creates maintenance burden.

## Architecture Overview

### Current Problem
```
Domain (comparator.py)
  └─ PropertyDiff(name="Placement", old_value=..., new_value=...)
       └─ UI MUST recompute: Placement.Base.x, Placement.Base.y, etc.
```

### Target State
```
Domain (comparator.py + property.py)
  └─ PropertyDiff(name="Placement", old_value=..., new_value=..., children=[
        PropertyDiff(name="Position", ...),
        PropertyDiff(name="Rotation", ...)
     ])
       └─ UI just renders: for child in children: render(child)
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Keep `_camelcase_to_spaces` in UI | Display/formatting concern, not domain logic |
| Delete `property_tree.py` entirely | All logic moved to domain, no UI helpers needed |
| Remove print() statements | Production code should not have debug prints |
| Keep Log.debug() calls | Useful for diagnosing production issues |
| Keep old_value/new_value in PropertyPresentation | Always needed for parent row display |
| Simplify circular reference logic | Not needed for property children (tree is shallow) |

## Architecture Impact

### Files Modified
| File | Change |
|------|--------|
| `freecad/diff_wb/domain/tree/property.py` | Add `get_children()` method |
| `freecad/diff_wb/domain/diff/models.py` | Add `children` field to PropertyDiff |
| `freecad/diff_wb/domain/diff/comparator.py` | Populate children when comparing |
| `freecad/diff_wb/ui/presenters/presentation_models.py` | Simplify PropertyPresentation |
| `freecad/diff_wb/ui/presenters/diff_presenter.py` | Transform children to presentation |
| `freecad/diff_wb/ui/views/diff_panel_view.py` | Remove diffing logic, only render |
| `freecad/diff_wb/ui/views/property_tree.py` | DELETE ENTIRE FILE |

### Files Deleted
- `freecad/diff_wb/ui/views/property_tree.py`

## FreeCAD Dependency
- [x] No FreeCAD required (pure code refactoring)

## Implementation Plan

### Phase 1: Add Property Expansion Logic to Domain

**Task**: Add `Property.get_children()` method that returns sub-properties.

**Implementation Details**:

Add to `domain/tree/property.py` (find the Property class and add this method):

```python
def get_children(self) -> list[tuple[str, Any]]:
    """Get child properties for expandable property types.
    
    Returns list of (child_name, child_value) tuples for:
    - Placement: [("Position", position), ("Rotation", rotation)]
    - Rotation (inside Placement): [("Angle", angle), ("Axis", axis)]
    - Vector-like (x,y,z): [("x", x), ("y", y), ("z", z)]
    - List/tuple: [("0", item0), ("1", item1), ...]
    - Dict: [("key1", value1), ("key2", value2), ...]
    
    Returns empty list for primitive types and non-expandable objects.
    
    Note: Rotation is not a separate PropertyType - it's a value object inside
    Placement. We detect it by checking if the value has angle/axis attributes.
    """
    # Skip if no value
    if self.value is None:
        return []
    
    # Placement expansion - extract Position and Rotation from Placement value
    if self.type_ == PropertyType.PLACEMENT:
        result = []
        # Try lowercase first, then uppercase (different FreeCAD APIs)
        if hasattr(self.value, "position") and self.value.position is not None:
            result.append(("Position", self.value.position))
        elif hasattr(self.value, "Base") and self.value.Base is not None:
            result.append(("Base", self.value.Base))
        if hasattr(self.value, "rotation") and self.value.rotation is not None:
            result.append(("Rotation", self.value.rotation))
        elif hasattr(self.value, "Rotation") and self.value.Rotation is not None:
            result.append(("Rotation", self.value.Rotation))
        return result
    
    # Check for Rotation value object (has angle/axis attributes)
    # This handles Rotation inside Placement - not a separate PropertyType
    if hasattr(self.value, "angle") or hasattr(self.value, "Angle"):
        if hasattr(self.value, "axis") or hasattr(self.value, "Axis"):
            result = []
            if hasattr(self.value, "angle") and self.value.angle is not None:
                result.append(("Angle", self.value.angle))
            elif hasattr(self.value, "Angle") and self.value.Angle is not None:
                result.append(("Angle", self.value.Angle))
            if hasattr(self.value, "axis") and self.value.axis is not None:
                result.append(("Axis", self.value.axis))
            elif hasattr(self.value, "Axis") and self.value.Axis is not None:
                result.append(("Axis", self.value.Axis))
            return result
    
    # Vector-like objects (x, y, z) - also handles Rotation's Axis (which has x,y,z)
    if hasattr(self.value, "x") and hasattr(self.value, "y") and hasattr(self.value, "z"):
        return [("x", self.value.x), ("y", self.value.y), ("z", self.value.z)]
    
    # List/tuple expansion
    if isinstance(self.value, (list, tuple)) and len(self.value) > 0:
        return [(str(i), v) for i, v in enumerate(self.value)]
    
    # Dict expansion
    if isinstance(self.value, dict) and len(self.value) > 0:
        return [(str(k), v) for k, v in self.value.items()]
    
    return []
```

**Tests to write** (`tests/unit/domain/tree/test_property.py`):
- `test_get_children_placement` - Placement returns Position + Rotation
- `test_get_children_rotation` - Rotation returns Angle + Axis
- `test_get_children_vector` - Vector returns x, y, z
- `test_get_children_list` - List returns indexed items
- `test_get_children_primitive` - Primitive returns empty list
- `test_get_children_none` - None value returns empty list

---

### Phase 2: Add Children to PropertyDiff

**Task**: Extend PropertyDiff to hold child property diffs.

**Implementation Details**:

In `domain/diff/models.py`:

1. Add `children` field to PropertyDiff dataclass:
```python
@dataclass(frozen=True)
class PropertyDiff:
    property_name: str
    old_value: Property | None
    new_value: Property | None
    state: DiffState = field(init=False)
    children: list["PropertyDiff"] = field(default_factory=list)  # NEW
```

2. Update imports to handle forward reference:
```python
from __future__ import annotations  # Already at top, verify present
```

3. Modify `_calculate_property_diff_state` - NO CHANGES NEEDED, logic stays the same

4. Add a function to compute children diffs (new function):
```python
def _compute_property_children(
    old_value: Property | None, 
    new_value: Property | None
) -> list["PropertyDiff"]:
    """Compute child property diffs for expandable properties."""
    children: list[PropertyDiff] = []
    
    old_children = old_value.get_children() if old_value else []
    new_children = new_value.get_children() if new_value else []
    
    old_child_map = dict(old_children)
    new_child_map = dict(new_children)
    
    all_child_names = set(old_child_map.keys()) | set(new_child_map.keys())
    
    for child_name in sorted(all_child_names):
        old_child_prop = old_child_map.get(child_name)
        new_child_prop = new_child_map.get(child_name)
        
        child_diff = PropertyDiff(
            property_name=child_name,
            old_value=old_child_prop,
            new_value=new_child_prop,
        )
        children.append(child_diff)
    
    return children
```

5. Update PropertyDiff `__post_init__` to compute children:
```python
def __post_init__(self) -> None:
    object.__setattr__(self, "state", _calculate_property_diff_state(self.old_value, self.new_value))
    # NEW: compute children for expandable properties
    object.__setattr__(self, "children", _compute_property_children(self.old_value, self.new_value))
```

**Tests to write**:
- `test_property_diff_computes_children` - PropertyDiff has children after creation
- `test_property_diff_no_children_for_primitives` - Primitive properties have empty children
- `test_property_diff_children_states` - Children have correct states (ADDED/DELETED/MODIFIED/UNCHANGED)

---

### Phase 3: Update Comparator (No Changes Needed)

**Task**: Verify comparator works with new PropertyDiff children.

**Implementation Details**:

The existing comparator in `comparator.py` creates PropertyDiff like this:
```python
prop_diff = PropertyDiff(
    property_name=prop_name,
    old_value=old_value,
    new_value=new_value,
)
```

Since PropertyDiff now auto-computes children in `__post_init__`, NO CHANGES are needed to the comparator. The children will be automatically populated.

**Verification tests**:
- Write test that shows when comparator creates PropertyDiff for Placement, the result has children populated

---

### Phase 4: Add Children to PropertyPresentation

**Task**: Add children field to PropertyPresentation while keeping existing fields.

**Implementation Details**:

In `ui/presenters/presentation_models.py`:

Update PropertyPresentation to ADD the children field (keep existing fields):
```python
@dataclass(frozen=True)
class PropertyPresentation:
    name: str
    state: DiffState
    # Keep these - needed for parent row display
    old_value: Any = None
    new_value: Any = None
    # NEW: children computed by domain (not re-diffed in UI)
    children: list["PropertyPresentation"] = field(default_factory=list)
    group: str | None = None
```

**Rationale**: We must keep old_value and new_value because:
1. Non-expandable properties (e.g., `Length`) only show parent row values
2. Expandable properties (e.g., `Placement`) show parent summary AND children details
3. Without these, users can't see what changed at the top level

**Tests to write**:
- `test_property_presentation_has_children`
- `test_property_presentation_empty_children_for_leaf`
- `test_property_presentation_children_with_parent_values` - verify both exist

---

### Phase 5: Update Presenter to Transform Children

**Task**: Update presenter to transform domain PropertyDiff children to PropertyPresentation children.

**Implementation Details**:

In `ui/presenters/diff_presenter.py`, update `_transform_property_diffs` method:

```python
def _transform_property_diffs(self, node_diff: NodeDiff) -> list[PropertyPresentation]:
    presentations = []

    for prop_diff in node_diff.property_diffs:
        # Extract group from property value
        group = self._extract_property_group(
            prop_diff.new_value if prop_diff.new_value is not None else prop_diff.old_value
        )

        # Extract old_value and new_value for parent display (keep existing)
        old_value = self._extract_property_value(prop_diff.old_value)
        new_value = self._extract_property_value(prop_diff.new_value)

        # Transform children recursively from domain PropertyDiff
        children = self._transform_children(prop_diff.children)

        presentations.append(
            PropertyPresentation(
                name=prop_diff.property_name,
                state=prop_diff.state,
                old_value=old_value,
                new_value=new_value,
                children=children,
                group=group,
            )
        )

        # Handle expression as separate row (keep existing logic)
        # ... (existing expression handling code)

    return presentations


def _transform_children(self, child_diffs: list[PropertyDiff]) -> list[PropertyPresentation]:
    """Recursively transform child property diffs to presentation format."""
    return [
        PropertyPresentation(
            name=child_diff.property_name,
            state=child_diff.state,
            old_value=self._extract_property_value(child_diff.old_value),
            new_value=self._extract_property_value(child_diff.new_value),
            children=self._transform_children(child_diff.children),
            # No group for children
        )
        for child_diff in child_diffs
    ]
```

**Note**: We keep `_extract_property_value()` calls because parent rows still need to display values.

**Tests to write**:
- `test_transform_property_diffs_includes_children`
- `test_transform_children_recursive`
- `test_transform_children_preserves_parent_values`

---

### Phase 6: Simplify UI View - Use Pre-computed Children

**Task**: Replace diffing logic with pre-computed children from domain, keep parent value display.

**Implementation Details**:

In `ui/views/diff_panel_view.py`:

1. **REMOVE** the `_determine_child_state()` method (lines ~682-720)
   - No longer needed: domain provides state

2. **REMOVE** the `_add_child_items_with_diffs()` method (lines ~537-651)
   - Replace with simpler `_add_child_items()` that uses pre-computed children

3. **ADD** new simplified method:
```python
def _add_child_items(
    self,
    parent_item: QTreeWidgetItem,
    children: list[PropertyPresentation],
) -> bool:
    """Add pre-computed child items to the tree.
    
    Args:
        parent_item: The parent QTreeWidgetItem to add children to.
        children: Pre-computed PropertyPresentation children from domain.
    
    Returns:
        True if any child has MODIFIED/ADDED/DELETED state, False otherwise.
    """
    has_changed_children = False
    
    for child in children:
        # Determine if this child has changes
        if child.state in (DiffState.MODIFIED, DiffState.ADDED, DiffState.DELETED):
            has_changed_children = True
        
        # Get values from pre-computed PropertyPresentation
        # Note: child.old_value and child.new_value may be None for children
        # that exist on only one side (ADDED/DELETED)
        old_val = child.old_value
        new_val = child.new_value
        
        # Format display values
        if child.state == DiffState.ADDED:
            left_value = ""
            right_value = str(new_val) if new_val is not None else child.name
        elif child.state == DiffState.DELETED:
            left_value = str(old_val) if old_val is not None else child.name
            right_value = ""
        elif child.state == DiffState.MODIFIED:
            left_value = str(old_val) if old_val is not None else ""
            right_value = str(new_val) if new_val is not None else ""
        else:  # UNCHANGED
            left_value = str(new_val) if new_val is not None else ""
            right_value = left_value
        
        # Use CamelCase conversion for display
        display_name = _camelcase_to_spaces(child.name)
        child_item = QTreeWidgetItem([display_name, left_value, right_value])
        
        # Apply background color based on state
        if child.state == DiffState.ADDED:
            self._apply_background_to_all_columns(child_item, self.ADDED_COLOR)
        elif child.state == DiffState.DELETED:
            self._apply_background_to_all_columns(child_item, self.DELETED_COLOR)
        elif child.state == DiffState.MODIFIED:
            self._apply_background_to_all_columns(child_item, self.MODIFIED_COLOR)
        # UNCHANGED: no background
        
        # Recursively add grandchildren (pre-computed, no diffing needed)
        if child.children:
            grandchild_has_changes = self._add_child_items(child_item, child.children)
            if grandchild_has_changes:
                has_changed_children = True
        
        parent_item.addChild(child_item)
    
    return has_changed_children
```

4. **UPDATE** `_create_property_tree_item()` to use pre-computed children:
```python
def _create_property_tree_item(self, prop: PropertyPresentation) -> QTreeWidgetItem:
    # ... existing code for display name and parent values ...
    
    # Use pre-computed children instead of computing diffs
    has_changed_children = self._add_child_items(item, prop.children)
    
    # ... rest of existing code ...
```

5. **REMOVE print() statements** - keep Log.debug() for production debugging

**Key Point**: We keep showing parent values (old_value/new_value) because:
- Parent row shows the overall property value (e.g., `Placement` summary)
- Children show detailed breakdown (Position.x, Position.y, etc.)
- Both are needed for user understanding

**Simplification Note**: The circular reference prevention (`visited` set, `depth` counter, `MAX_DEPTH`) is NOT NEEDED because:
- Property children form a shallow tree (Placement → Position/Rotation → x/y/z)
- There's no circular reference possibility in FreeCAD property structures
- If we ever need it, add it back - but for now, simplify

**Tests to verify**:
- UI receives PropertyPresentation with children populated
- View renders children correctly without computing diffs
- Parent still shows old_value/new_value
- All states (ADDED/DELETED/MODIFIED/UNCHANGED) render properly

---

### Phase 7: Delete property_tree.py

**Task**: Remove the file entirely.

**Implementation Details**:

```bash
rm freecad/diff_wb/ui/views/property_tree.py
```

**Verification**:
- Ensure no imports of `property_tree` anywhere in the codebase
- Run tests to verify nothing breaks

---

### Phase 8: Final Verification

**Task**: Run all tests and verify nothing is broken.

**Commands**:
```bash
# Run unit tests
task test

# Run linter
task check

# Verify no import errors
python -c "from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView"
```

---

## Expected Code Reduction

| File | Lines Changed | Notes |
|------|---------------|-------|
| `property_tree.py` | -243 lines | Entire file deleted (moved to domain) |
| `diff_panel_view.py` | ~-80 lines | Remove _determine_child_state, _add_child_items_with_diffs, simplify |
| `diff_presenter.py` | +~30 lines | Add _transform_children() method |
| `presentation_models.py` | +~5 lines | Add children field (keep existing fields) |
| `property.py` | +~70 lines | Add get_children() method |
| `models.py` | +~45 lines | Add children field and _compute_property_children() |
| **Net** | ~-170 lines | Cleaner architecture, domain owns diffing |

## Test Commands

```bash
# Run unit tests
task test

# Run specific test file
pytest tests/unit/domain/diff/test_models.py -v

# Run specific test file
pytest tests/unit/ui/presenters/test_diff_presenter.py -v
```