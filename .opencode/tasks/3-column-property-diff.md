# Task: 3-Column Property Diff Layout

## Goal
Change the property diff tree from 2 columns (Property, Value) to 3 columns (Property, Value Left, Value Right), with proper diff display for expandable properties and correct coloring rules. Also ensure expressions are properly displayed as separate rows below their parent property.

## Context
Currently the property diff tree shows modified values as `oldval -> newval` in a single Value column. The user wants separate columns for left (old) and right (new) values, with correct expansion behavior and coloring for sub-properties.

Expressions should appear as separate rows below their parent property (not as children), with display name "-> Expression" and the 3-column layout.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Add old_value field to PropertyPresentation | Need access to both old and new values to compute sub-property diffs in the view | Parse old_display string, but that's fragile and doesn't work for all types |
| Compute child diffs in view layer | Keeps presenter changes minimal; view already has expansion logic | Move logic to presenter, but that's more invasive |
| Color unchanged children with default background | User explicitly requested this behavior | Color all children consistently, but user specified default for unchanged |
| Expression as separate sibling row | User clarified expressions should be displayed below their parent property, not as children | Making them children would require different expansion handling |

## Architecture Impact
- **Files affected**:
  - `freecad/diff_wb/ui/presenters/presentation_models.py` - Add old_value/new_value fields
  - `freecad/diff_wb/ui/presenters/diff_presenter.py` - Pass old_value/new_value to PropertyPresentation, fix expression display name
  - `freecad/diff_wb/ui/views/diff_panel_view.py` - Change column layout and child rendering

## FreeCAD Dependency
- [x] No FreeCAD required (pure Qt UI changes)

## Implementation Plan
**IMPORTANT:** For each phase, ALWAYS write test steps BEFORE implementation steps to follow TDD principles.

### Phase 1: Update PropertyPresentation model
- [x] Add `old_value: Any = None` field to PropertyPresentation dataclass
- [x] Add `new_value: Any = None` field to PropertyPresentation dataclass
- [x] Write unit tests verifying the new fields are properly set

### Phase 2: Update DiffPresenter to pass both values and fix expression display
- [x] Update `_transform_property_diffs` to pass old_value to PropertyPresentation
- [x] Pass both old and new values for expandable properties
- [x] Change expression name from "Expression" to "-> Expression"
- [x] Pass expression old_value and new_value (the actual expression strings, not display strings)
- [x] Write unit tests verifying old_value is correctly passed and expression name is correct

### Phase 3: Update DiffPanelView 3-column layout
- [x] Change column count from 2 to 3: `setColumnCount(3)`
- [x] Update header labels: `["Property", "Value Left", "Value Right"]`
- [x] Update `_create_group_header_item` to use 3 columns
- [x] Update `_create_property_tree_item`:
  - For ADDED: column 1 empty, column 2 = new_display
  - For DELETED: column 1 = old_display, column 2 empty
  - For MODIFIED: column 1 = old_display, column 2 = new_display
  - For UNCHANGED: column 1 = new_display, column 2 = new_display
- [x] Apply diff coloring to all 3 columns for the property row
- [x] Update group header creation to use 3 columns
- [x] All Phase 3 tasks completed

### Phase 4: Handle expandable properties with child diffs
- [x] Modify `_create_property_tree_item` to accept old_value for computing child diffs
- [x] For each child:
  - Get old_child_value and new_child_value
  - Compare to determine state (MODIFIED/ADDED/DELETED/UNCHANGED)
  - Create child item with 3 columns: name, old_value_str, new_value_str
  - Apply background color only if state is MODIFIED/ADDED/DELETED
- [x] If any child has MODIFIED/ADDED/DELETED state, color the parent row blue (MODIFIED color)
- [x] Write tests for expandable properties with child diffs

### Phase 5: Handle Expression rows
- [x] Expression rows should be treated as regular property rows in 3-column layout
- [x] They appear as separate rows below their parent (same as now)
- [x] The display name should be "-> Expression" with old/new in left/right columns
- [x] Write tests verifying expression display

### Phase 6: Run linters and tests
- [x] Run `task check` to verify code style
- [x] Run `task test` to verify all unit tests pass
- [x] Fix any issues found

## Test Strategy
- **Unit tests**: Test PropertyPresentation fields, presenter transformation, view column layout
- **Unit tests**: Test expandable properties with both old/new values showing
- **Unit tests**: Test coloring rules (colored for changed, default for unchanged children)
- **Unit tests**: Test expression rows display correctly with "-> Expression" name

## Findings & Notes
- The current implementation only stores `value` (new value) in PropertyPresentation
- Need to also pass old_value to enable child diff computation
- The `get_property_children` function in property_tree.py needs to be used twice: once for old value, once for new value
- Child state comparison: compare old and new child values to determine state
- Expression rows are currently added as separate PropertyPresentation items with name="Expression" - need to change to "-> Expression"