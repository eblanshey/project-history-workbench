# Refactor Presentation Models - Remove Redundant Fields and Use DiffState Enum

## Goal

Remove redundant display fields from PropertyPresentation, remove deprecated value field, and use DiffState enum throughout instead of string literals for type safety.

## Context

- PropertyPresentation currently has old_display/new_display fields that are just str() of old_value/new_value (redundant)
- PropertyPresentation has a deprecated 'value' field that should be removed
- State fields use string literals ("ADDED", "DELETED", etc.) instead of the domain DiffState enum
- This violates Architecture.md principles about using enums for type safety

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Remove old_display/new_display fields | They're just str(value), no expression info actually included | Keep them but rename for clarity |
| Remove deprecated value field | old_value/new_value already provide the same functionality | Keep for backward compatibility |
| Use DiffState enum throughout | Type safety, no magic strings, follows Architecture.md | Keep strings in UI layer only |
| Format values in view layer | View is responsible for presentation, simpler model | Keep formatting in presenter |

## Architecture Impact

**Files affected**:

- `freecad/diff_wb/ui/presenters/presentation_models.py` - Remove fields, add DiffState import
- `freecad/diff_wb/ui/presenters/diff_presenter.py` - Remove display formatting, use enum
- `freecad/diff_wb/ui/views/diff_panel_view.py` - Add formatting, use enum
- Test files need updates

## FreeCAD Dependency

- [ ] No FreeCAD required (pure code refactoring)

## Implementation Plan

### Phase 1: Update presentation_models.py

- [x] Import DiffState from domain.diff.models
- [x] Change NodePresentation.state from str to DiffState
- [x] Remove old_display and new_display fields from PropertyPresentation
- [x] Remove deprecated value field from PropertyPresentation
- [x] Change PropertyPresentation.state from str to DiffState
- [x] Update docstring to reflect changes
- [x] Write unit tests verifying the new structure

### Phase 2: Update diff_presenter.py

- [x] Import DiffState from domain.diff.models
- [x] Remove _format_property_value method (no longer needed)
- [x] Update _transform_node_diffs to pass DiffState directly (not .name)
- [x] Update _transform_property_diffs to not compute display strings
- [x] Update _transform_property_diffs to pass DiffState directly
- [x] Update expression state logic to use DiffState enum
- [x] Write unit tests verifying presenter changes

### Phase 3: Update diff_panel_view.py

- [x] Import DiffState from domain.diff.models
- [x] Update _get_property_display_values to format values on-demand with str()
- [x] Update _get_property_display_values to use DiffState enum comparisons
- [x] Update _determine_child_state to return DiffState instead of str
- [x] Update all string state comparisons to DiffState enum comparisons
- [x] Write unit tests verifying view formatting and enum usage

### Phase 4: Update all test files

- [x] Update test_presentation_models.py - remove display field tests, add enum tests
- [x] Update test_diff_presenter_properties.py - use DiffState in assertions
- [x] Update test_show_properties.py - use DiffState, verify formatting
- [x] Run task check to verify code style
- [x] Run task test to verify all unit tests pass
- [x] Fix any issues found

## Test Strategy

- **Unit tests**: Verify PropertyPresentation no longer has display fields
- **Unit tests**: Verify DiffState enum is used throughout
- **Unit tests**: Verify view formats values correctly with str()
- **Unit tests**: Verify None values display as empty string

## Expected Outcomes

- Cleaner, simpler PropertyPresentation model
- Type-safe state handling throughout
- No functional change to UI display
- All 460+ tests passing
