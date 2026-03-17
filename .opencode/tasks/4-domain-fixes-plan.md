# Domain Fixes Plan

## Overview

This task implements minor domain model improvements:

1. **Snapshot.timestamp**: Change from `str` to `datetime.datetime` for proper sorting
2. **PropertyValue.create()**: Consolidate multiple `from_*` methods into a single unified factory method
3. **Placement consolidation**: Move `Vector`, `Rotation`, `Placement` classes from `placement.py` into `property_value.py`

## Design Decisions

### Snapshot.timestamp

- **Type**: `datetime.datetime` (standard library)
- **Benefit**: Enables proper chronological sorting of snapshots
- **Impact**: All snapshot creation sites must pass datetime objects instead of strings

### PropertyValue.create() Method

**Signature:**
```python
@classmethod
def create(cls, type_: PropertyType, value: Any, expression: str | None = None) -> "PropertyValue":
```

**Behavior:**
- Uniform interface for all property types
- Caller passes structured data (tuples/dicts) as `value`
- Internally creates proper structured objects:
  - `VECTOR`: tuple `(x, y, z)` → `Vector(x, y, z)`
  - `PLACEMENT`: dict `{"position": ..., "rotation": ...}` → `Placement(position=..., rotation=...)`
- Basic types (BOOL, INT, FLOAT, STRING, LINK) use value directly

**Removed Methods:**
- `from_bool()`, `from_int()`, `from_float()`, `from_string()`
- `from_vector()`, `from_placement()`, `from_link()`
- No deprecated wrappers - clean break

### Placement Classes Location

- **Before**: `freecad/diff_wb/domain/placement.py`
- **After**: `freecad/diff_wb/domain/property_value.py`
- **Rationale**: All domain types related to property values should be in one file

## Implementation Steps

### Step 1: Update Snapshot.timestamp Type

**File**: `freecad/diff_wb/domain/snapshot.py`

Changes:
1. Add `from datetime import datetime` import
2. Change `timestamp: str` to `timestamp: datetime`
3. Update docstring to reflect datetime type

### Step 2: Move Placement Classes to property_value.py

**Source**: `freecad/diff_wb/domain/placement.py`
**Target**: `freecad/diff_wb/domain/property_value.py`

Classes to move:
- `Vector` (lines 11-37)
- `Rotation` (lines 40-77)
- `Placement` (lines 80-106)

### Step 3: Refactor PropertyValue.create() Method

**File**: `freecad/diff_wb/domain/property_value.py`

Changes:
1. Add `create()` classmethod that handles all types
2. Remove existing `from_*` classmethods:
   - `from_bool()` (lines 83-91)
   - `from_int()` (lines 93-101)
   - `from_float()` (lines 103-111)
   - `from_string()` (lines 113-121)
   - `from_vector()` (lines 123-126)
   - `from_placement()` (lines 128-138)
   - `from_link()` (lines 140-148)
3. Update `make_property_value()` function or remove if redundant

**create() Implementation Logic:**
```python
if type_ == PropertyType.BOOL:
    return cls(type_=type_, value=bool(value), expression=expression)
elif type_ == PropertyType.INT:
    return cls(type_=type_, value=int(value), expression=expression)
elif type_ == PropertyType.FLOAT:
    return cls(type_=type_, value=float(value), expression=expression)
elif type_ == PropertyType.STRING:
    return cls(type_=type_, value=str(value), expression=expression)
elif type_ == PropertyType.LINK:
    return cls(type_=type_, value=str(value), expression=expression)
elif type_ == PropertyType.VECTOR:
    # value is tuple (x, y, z)
    x, y, z = value
    return cls(type_=type_, value=Vector(x=x, y=y, z=z), expression=expression)
elif type_ == PropertyType.PLACEMENT:
    # value is dict {"position": (x,y,z), "rotation": (ax,ay,az,angle)}
    pos = value["position"]
    rot = value["rotation"]
    return cls(
        type_=type_,
        value=Placement(
            position=Vector(*pos),
            rotation=Rotation(axis_x=rot[0], axis_y=rot[1], axis_z=rot[2], angle_degrees=rot[3])
        ),
        expression=expression
    )
```

### Step 4: Update domain/__init__.py Exports

**File**: `freecad/diff_wb/domain/__init__.py`

Changes:
1. Keep `Vector`, `Rotation`, `Placement` exports (now from property_value.py)
2. Remove import from placement module
3. Update imports to reflect new location

### Step 5: Delete placement.py

**File**: `freecad/diff_wb/domain/placement.py`

Action: Delete after all references are updated

### Step 6: Update Tests

**File**: `tests/unit/test_domain.py`

Changes needed:
1. Update Snapshot creation to use `datetime.datetime` instead of strings
2. Update PropertyValue tests to use `PropertyValue.create()` instead of `from_*` methods
3. Verify Vector/Rotation/Placement still work correctly

### Step 7: Update docs/PLAN.md

**File**: `docs/PLAN.md`

Review sections:
- Line 252-258: Snapshot class definition (update timestamp type)
- Line 270-276: PropertyValue class definition (update to show create() method)
- Line 156: Remove reference to placement.py in directory layout if applicable

## Dependencies

- No external dependencies added (uses standard library datetime)
- All changes are internal refactoring

## Testing Strategy

1. Run existing unit tests after each step
2. Fix test failures due to API changes
3. Verify all PropertyValue types work correctly with new create() method
4. Verify Snapshot sorting works with datetime objects

## Success Criteria

- [ ] Snapshot.timestamp is datetime.datetime type
- [ ] PropertyValue has single create() method
- [ ] All from_* methods removed
- [ ] Vector, Rotation, Placement in property_value.py
- [ ] placement.py deleted
- [ ] All tests pass
- [ ] docs/PLAN.md updated
