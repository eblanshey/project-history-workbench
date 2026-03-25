# Task: Phase 10 - Lazy Initialization & Container Refactoring

## Goal

Refactor the Diff workbench initialization to use lazy initialization: create container and register commands only when the workbench is first activated, not at FreeCAD startup. This aligns with FreeCAD's workbench lifecycle and ensures minimal work during FreeCAD startup.

## Status

Completed - all phases implemented successfully.

## Context

### Current Problem

**Bug**: Snapshot creation works but doesn't display in the UI.

**Root Cause**: Two separate `SnapshotPresenter` instances exist:
1. `container.snapshot_presenter` (created in `init_gui.py` with `NullSnapshotView`) - used by commands
2. `workbench._snapshot_presenter` (created in `workbench.py` with real `DiffPanelView`) - never used

When user clicks "Take Snapshot", the command uses presenter #1 (null view), so nothing displays even though the snapshot is created successfully.

**Additional Issues**:
- Heavy initialization happens at FreeCAD startup (`init_gui.py`)
- Commands registered at module load time with stub container
- Outdated "Phase X" comments throughout codebase (X ≤ 9)
- Missing `show_success()` implementation (Phase 9 intended feature)

### FreeCAD Workbench Lifecycle

**`Initialize()`** - Called **once** when workbench is **first activated**:
- Perfect for one-time setup: create container, register commands, setup menus/toolbars
- Never called again after first activation

**`Activated()`** - Called **every time** user switches to this workbench:
- Should be lightweight - just show UI, restore state
- Can be called many times during a session

**`Deactivated()`** - Called when switching away from workbench:
- Clean up state if needed

### Architecture Principles

Following FreeCAD best practices and the project's Architecture.md:
1. **Lazy Initialization**: Do minimal work at startup; initialize on first use
2. **Single Source of Truth**: Container should be the composition root
3. **Separation of Concerns**: `init_gui.py` registers workbench; `workbench.py` handles lifecycle
4. **No Duplicate Presenters**: Commands and workbench should use the same presenter instance

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Register commands in `Initialize()` | FreeCAD calls this once on first activation; perfect for one-time setup | Register in `init_gui.py` (runs at FreeCAD startup - too early) |
| Create container in `Initialize()` | One-time setup matches lifecycle; lazy enough vs. startup | Delay until first action (overly complex) |
| Commands access container via `get_container()` | Stateless commands; always use current container instance | Store references in command constructors (causes duplicate presenter bug) |
| No stub container in `init_gui.py` | Cleaner - container only exists when actually needed | Set `_container = None` explicitly (unnecessary, already None by default) |
| Keep `show_success()` with logging | Provides feedback consistency; minimal overhead | Remove entirely (loses UI layer responsibility) |
| Remove outdated Phase comments | Reduces noise; completed phases shouldn't clutter code | Keep all comments (historical reference) |
| Move DiffPanelView creation to `Activated()` | Lightweight UI display; preserves state | Create in `Initialize()` (too early - UI not needed yet) |

## Architecture Impact

### Files Modified

1. **`init_gui.py`** - Stripped down to ultra-thin registration
   - Removed container creation logic
   - Removed command registration  
   - Removed workbench import (defer to workbench.py)
   - Kept: translation setup, version check, runtime context, workbench registration
   - **No stub container needed** - `_container` is None by default

2. **`entrypoints/workbench.py`** - Now handles full lifecycle
   - Added `Initialize()` method: create container, register commands, setup toolbar/menu
   - Call `set_container(container)` to make it globally available
   - Modified `Activated()` to only show/create panel (no DI logic)
   - Removed duplicate `SnapshotPresenter` creation
   - Uses `get_container().snapshot_presenter` directly

3. **`entrypoints/commands.py`** - Simplified command structure
   - Removed `__init__` methods from command classes
   - Use `get_container()` in `Activated()` methods (raises error if not initialized)
   - Removed stored action/presenter references
   - Commands are stateless - no constructor parameters

4. **`_container.py`** - Added runtime safety check
   - Updated `get_container()` to raise `RuntimeError` if called before initialization
   - Error message: "Container not initialized. Workbench must be activated first."
   - Clear error helps debugging if something goes wrong

5. **`application/di/container.py`** - Updated constructor signature
   - Removed `snapshot_view` parameter (not used in lazy init)
   - Kept `diff_view` parameter for future use
   - Updated docstrings to remove Phase references

6. **`ui/views/diff_panel_view.py`** - Completed Phase 9 work
   - Implemented `show_success()` to log success message
   - Removed outdated "Phase X" comments
   - Cleaned up stub implementation comments

7. **`ui/protocols/snapshot_view.py`** - Updated docstrings
   - Removed Phase references
   - Clarified translation responsibility

### Dependency Flow (New)

```
FreeCAD Startup:
  init_gui.py
    ├─ Setup translation paths
    ├─ Get runtime context
    └─ Register DiffWorkbench class
    (_container is None by default - no stub needed)

First Activation (Initialize called once):
  workbench.Initialize()
    ├─ Create snapshot_repo
    ├─ Create container (wires all actions/presenters)
    ├─ Call set_container(container) ← Now globally available
    ├─ Register commands (they'll use get_container() at execution)
    └─ Setup toolbar/menu

Subsequent Activations (Activated called each time):
  workbench.Activated()
    ├─ Check if panel exists
    ├─ If not: _create_diff_panel() → shows existing view
    └─ If yes: show subwindow, raise to front

User Clicks "Take Snapshot":
  _TakeSnapshotCommand.Activated()
    ├─ container = get_container() ← Returns real container
    ├─ container.take_snapshot_action.execute()
    └─ container.snapshot_presenter.present_result(result)
        ├─ view.show_success() → logs message
        └─ load_snapshots() → updates UI list
```

## FreeCAD Dependency

- [x] FreeCAD required (workbench lifecycle integration)
- [x] Qt/PySide6 required (UI widgets)
- [x] No new FreeCAD APIs needed (existing patterns only)

## Implementation Plan

### Phase 1: Strip Down init_gui.py

**Goal**: Make `init_gui.py` ultra-thin, only registering the workbench class.

**Changes**:
- [x] Remove container creation logic
- [x] Remove command registration
- [x] Remove workbench import
- [x] Keep: translation setup, version check, runtime context, workbench registration
- [x] **No stub container needed** - `_container` is None by default in `_container.py`

**Expected Result**: `init_gui.py` is ~20 lines, just sets up FreeCAD to know about the workbench. No global state manipulation.

### Phase 2: Move Initialization to workbench.Initialize()

**Goal**: Create container and register commands on first activation.

**Changes**:
- [x] Add `Initialize()` method to `DiffWorkbench` class
- [x] Create `snapshot_repo` and `container` in `Initialize()`
- [x] Call `set_container(container)` to wire it globally
- [x] Register commands via `register_commands(container)`
- [x] Setup toolbar and menu in `Initialize()` (previously in wrong place)

**Expected Result**: Container created once on first activation; commands registered with real presenter.

### Phase 3: Simplify Commands to Use get_container()

**Goal**: Remove stored references from commands; call `get_container()` at execution time.

**Changes**:
- [x] Remove `__init__` from `_TakeSnapshotCommand`, `_CompareCommand`, `_SwapColumnsCommand`
- [x] In `Activated()` methods, call `container = get_container()` then use `container.*`
- [x] `get_container()` raises `RuntimeError` if called before `Initialize()` (won't happen in normal flow)
- [x] Remove constructor parameters from command classes
- [x] Update `register_commands()` to not pass action/presenter arguments

**Expected Result**: Commands are stateless; always use current container instance. Clear error if something goes wrong.

### Phase 4: Clean Up Duplicate Presenter in workbench.py

**Goal**: Remove the duplicate `SnapshotPresenter` creation; use container's instance.

**Changes**:
- [x] Remove `from ..ui.presenters.snapshot_presenter import SnapshotPresenter` import
- [x] Remove `self._snapshot_presenter = SnapshotPresenter(...)` line
- [x] Change `self._snapshot_presenter.load_snapshots()` to `get_container().snapshot_presenter.load_snapshots()`
- [x] Update `_on_subwindow_closed()` to not reset presenter reference

**Expected Result**: Single `SnapshotPresenter` instance used everywhere. No duplicate instances.

### Phase 5: Implement show_success() Method

**Goal**: Complete Phase 9's intended feature - provide feedback when snapshot created.

**Changes**:
- [x] In `diff_panel_view.py`, implement `show_success(snapshot_name)`:
  ```python
  from ..._container import get_container
  
  def show_success(self, snapshot_name: str) -> None:
      """Log success message for consistency with action layer."""
      get_container().log(f"Snapshot '{snapshot_name}' created successfully\n")
  ```
- [x] Update docstring to explain logging responsibility

**Expected Result**: User sees success message in FreeCAD console when taking snapshot.

### Phase 6: Remove Outdated Phase Comments

**Goal**: Clean up codebase by removing completed phase references.

**Files and Lines**:
- [x] `diff_panel_view.py`: Removed lines 31, 141, 146, 155, 158, 161, 166
- [x] `container.py`: Removed lines 116, 117, 153
- [x] `init_gui.py`: Removed line 42
- [x] `commands.py`: Kept lines 81-82, 97-99, 108-110, 131-133 (future phases NOT completed)
- [x] `snapshot_view.py`: Updated docstrings to remove "Phase X" references

**Expected Result**: Cleaner code without historical noise.

### Phase 7: Integration Testing

**Goal**: Verify full flow works correctly in FreeCAD.

**Test Cases**:
- [x] Start FreeCAD - verify minimal workbench loading (no errors)
- [x] Switch to Diff workbench (first time) - verify:
  - [x] Container created
  - [x] Commands registered
  - [x] Panel appears with "Snapshots" placeholder
- [x] Take snapshot - verify:
  - [x] Success message logged to FreeCAD console
  - [x] Snapshot list refreshes automatically
  - [x] New snapshot appears in list
- [x] Take another snapshot - verify both appear, newest first
- [x] Switch to another workbench and back - verify:
  - [x] Panel persists (not recreated)
  - [x] Snapshots still visible
- [x] Close panel and switch back - verify new panel created

## Test Strategy

### Unit Tests (No FreeCAD)

- [x] **Commands test**: Import commands module, verify no runtime errors
- [x] **Container test**: Create container manually, verify all components wired
- [x] **Presenter test**: Call `present_result()` with mock view, verify `show_success()` called

### Integration Tests (FreeCAD Required)

- [x] **Workbench lifecycle test**: Simulate Initialize/Activated/Deactivated calls
- [x] **Command execution test**: Call command `Activated()` methods directly
- [x] **Full UI flow test**: Manual testing in FreeCAD GUI (see Phase 7 above)

## Findings & Notes

1. **`Initialize()` vs `Activated()` timing**: `Initialize()` is perfect for one-time setup; `Activated()` should be lightweight

2. **Command registration**: FreeCAD allows `addCommand()` in `Initialize()`; this is actually the recommended approach for Python workbenches

3. **Container lifecycle**: `set_container()` called in `Initialize()` makes container globally available via `get_container()`

4. **No stub container needed**: `_container` is `None` by default in `_container.py`; no need to explicitly set it in `init_gui.py`

5. **`get_container()` safety**: Raises `RuntimeError` if called before `Initialize()` - clear error helps debugging (won't happen in normal flow since commands aren't registered until then)

6. **Duplicate presenter bug**: Root cause was creating presenter twice - once in `init_gui.py` (with null view) and once in `workbench.py` (with real view). Commands used the wrong one.

7. **Lazy initialization benefit**: FreeCAD startup is faster; workbench only initializes when user actually uses it

8. **show_success() logging**: Keeping it simple - just log to FreeCAD console for consistency with action layer. No UI popups or status bar messages needed at this stage.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Commands not registering in Initialize() | Low | High | Tested immediately; FreeCAD documentation confirms this pattern works |
| `get_container()` called before initialization | Very Low | Medium | RuntimeError provides clear error message; won't happen in normal flow |
| Panel recreation on each activation | Medium | Medium | Check `if self._subwindow is None` before creating |
| Translation strings not loaded | Low | High | Kept translation setup in init_gui.py |
| Breaking existing tests | Medium | Low | Updated tests to call `set_container()` explicitly before importing commands |

## Success Criteria

- [x] FreeCAD starts without errors
- [x] Diff workbench loads on first activation (no errors)
- [x] Commands registered and functional
- [x] Take Snapshot creates snapshot AND displays in UI list
- [x] Success message logged to FreeCAD console
- [x] Panel persists across workbench switches
- [x] No "Phase X" comments for completed phases (X ≤ 9)
- [x] Single SnapshotPresenter instance used everywhere

## Rollback Plan

If issues arise:
1. Revert `init_gui.py` to previous version (container creation restored)
2. Revert `workbench.py` to previous version (duplicate presenter restored)
3. Revert `commands.py` to previous version (stored references restored)
4. Keep `show_success()` implementation (harmless addition)
5. Keep comment cleanup (non-functional changes)

## Dependencies

- Phase 9 (populate snapshots) must be complete before refactoring
- All existing unit tests should pass after refactoring
- Integration tests verify full flow in FreeCAD

## Related Tasks

- Phase 9: Populate Snapshots Column (completed, provides context)
- Phase 8: 3-Column Panel (completed, provides UI foundation)
- Future: Phase 10+ (snapshot selection, comparison, diff display)
