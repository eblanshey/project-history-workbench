# Task: Centralize FreeCAD Context Creation

## Goal
Eliminate redundant FreeCAD context creation across multiple port factories by centralizing context creation in a single location and enforcing explicit dependency injection.

## Context
Currently, the codebase has three separate port factories (`get_port()`, `get_app_port()`, `get_gui_port()`) that each independently create a `FreeCadContext` when no context is provided. This leads to:
- Redundant FreeCAD imports happening multiple times
- Inconsistent usage patterns (some code passes `ctx`, some doesn't)
- Harder testing (multiple entry points to mock)

**User requirement:** Domain layer should only receive ports as parameters, never import infrastructure directly.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Single module-level `CTX` in `init_gui.py` | Simplest approach - one composition root, no parameter threading through call chains | Pass `ctx` through all entry points (more typing, more churn) |
| Port factories require mandatory `ctx` parameter | Enforces explicit dependency injection, prevents accidental auto-creation | Keep optional parameter with auto-creation (defeats purpose) |
| Keep existing port structure | Minimal churn, maintains separation of concerns | Consolidate into single `FreeCadServices` object (more invasive) |
| Remove legacy `extract_document_tree()` function | Eliminates domain importing infrastructure | Keep but deprecate (adds maintenance burden) |

## Architecture Impact

**Files Modified:**
- `infrastructure/freecad/context.py` - Remove auto-creation from `get_port()`
- `infrastructure/freecad/app_port.py` - Remove auto-creation from `get_app_port()`
- `infrastructure/gui/qt_adapter.py` - Remove auto-creation from `get_gui_port()`
- `infrastructure/freecad/settings_repo.py` - Make `ctx` mandatory parameter
- `init_gui.py` - Add module-level `CTX` export
- `entrypoints/commands.py` - Import `CTX` from `init_gui`
- `entrypoints/workbench.py` - Import `CTX` from `init_gui`
- `freecad_version_check.py` - Import `CTX` from `init_gui`
- `domain/snapshots/extractor.py` - Remove legacy `extract_document_tree()` function

**No files added or deleted.**

## FreeCAD Dependency
- **No API exploration needed** - Pure refactoring of existing code
- All changes are internal to Python modules
- No FreeCAD API behavior changes

## Implementation Plan

### Phase 1: Update Port Factories
Remove auto-creation logic from all port factories.

#### Step 1.1: Update `infrastructure/freecad/context.py`
- [ ] Change `get_port(ctx: FreeCadContext | None = None)` → `get_port(ctx: FreeCadContext)`
- [ ] Remove `if ctx is None: ctx = get_freecad_runtime_context()` block
- [ ] Update docstring to reflect mandatory parameter
- [ ] Run tests to verify no regressions

#### Step 1.2: Update `infrastructure/freecad/app_port.py`
- [ ] Change `get_app_port(ctx: FreeCadContext | None = None)` → `get_app_port(ctx: FreeCadContext)`
- [ ] Remove `if ctx is None: ctx = get_freecad_runtime_context()` block
- [ ] Remove unused import of `get_freecad_runtime_context`
- [ ] Update docstring to reflect mandatory parameter
- [ ] Run tests to verify no regressions

#### Step 1.3: Update `infrastructure/gui/qt_adapter.py`
- [ ] Change `get_gui_port(ctx: FreeCadContext | None = None)` → `get_gui_port(ctx: FreeCadContext)`
- [ ] Remove `if ctx is None: ctx = get_freecad_runtime_context()` block
- [ ] Update docstring to reflect mandatory parameter
- [ ] Run tests to verify no regressions

#### Step 1.4: Update `infrastructure/freecad/settings_repo.py`
- [ ] Change `__init__(self, ctx: FreeCadContext | None = None)` → `__init__(self, ctx: FreeCadContext)`
- [ ] Remove `self._ctx = ctx if ctx is not None else get_freecad_runtime_context()`
- [ ] Remove unused import of `get_freecad_runtime_context`
- [ ] Update docstring to reflect mandatory parameter
- [ ] Run tests to verify no regressions

### Phase 2: Create Composition Root Export
Add module-level context export in `init_gui.py`.

#### Step 2.1: Update `init_gui.py`
- [ ] Add `CTX = get_freecad_runtime_context()` after existing context creation line
- [ ] Export `CTX` at module level (already visible by virtue of being in module)
- [ ] Add comment explaining `CTX` is the single composition root for FreeCAD dependencies
- [ ] Run tests to verify no regressions

### Phase 3: Update Entry Points
Update all entry points to use the shared `CTX`.

#### Step 3.1: Update `entrypoints/commands.py`
- [ ] Add import: `from ..init_gui import CTX`
- [ ] Update `_translate()` function to use `get_app_port(CTX)` instead of `get_app_port()`
- [ ] Run tests to verify no regressions

#### Step 3.2: Update `entrypoints/workbench.py`
- [ ] Add import: `from ..init_gui import CTX`
- [ ] Update `_translate()` function to use `get_port(CTX)` instead of `get_port()`
- [ ] Update `Activated()` and `Deactivated()` methods to use `get_port(CTX)`
- [ ] Run tests to verify no regressions

#### Step 3.3: Update `freecad_version_check.py`
- [ ] Add import: `from .init_gui import CTX`
- [ ] Update all `get_port()` calls to `get_port(CTX)`
- [ ] Run tests to verify no regressions

### Phase 4: Remove Legacy Domain Import
Eliminate domain layer importing infrastructure.

#### Step 4.1: Update `domain/snapshots/extractor.py`
- [ ] Identify and remove the legacy `extract_document_tree()` function (lines ~295-311)
- [ ] This function currently imports `get_port` from infrastructure - violates architecture
- [ ] Verify no external code depends on this function
- [ ] Run tests to verify no regressions

#### Step 4.2: Update public API exports
- [ ] Check `domain/snapshots/__init__.py` for exports of removed function
- [ ] Remove any exports of legacy functions
- [ ] Run tests to verify no regressions

### Phase 5: Verification
Run full test suite and linting.

#### Step 5.1: Run unit tests
- [ ] Execute: `pytest tests/unit/ -v`
- [ ] Verify all tests pass
- [ ] Fix any failures

#### Step 5.2: Run linter
- [ ] Execute: `ruff check freecad/diff_wb/`
- [ ] Fix any linting errors
- [ ] Execute: `ruff format freecad/diff_wb/ --check`
- [ ] Fix any formatting issues

#### Step 5.3: Verify imports
- [ ] Check for any remaining `get_port()`, `get_app_port()`, `get_gui_port()` calls without arguments
- [ ] Check for any remaining `get_freecad_runtime_context()` calls outside `init_gui.py`
- [ ] Verify no domain layer imports infrastructure

## Test Strategy
- **Unit tests**: Existing tests should pass unchanged (they already pass `ctx` explicitly)
- **Integration tests**: Verify entry points work with real FreeCAD using `run_with_freecad.sh`

## Findings & Notes

**Current usage patterns identified:**
- `init_gui.py`: Already creates context once, passes to container ✓
- `container.py`: Already receives `ctx` and passes to factories ✓
- `commands.py`: Calls `get_app_port()` with no args ✗
- `workbench.py`: Calls `get_port()` with no args ✗
- `freecad_version_check.py`: Calls `get_port()` with no args ✗
- `extractor.py`: Has legacy function calling `get_port()` with no args ✗

**Files with auto-creation logic to remove:**
1. `context.py:153` - `get_port()` has `if ctx is None` block
2. `app_port.py:44` - `get_app_port()` has `if ctx is None` block
3. `qt_adapter.py:95` - `get_gui_port()` has `if ctx is None` block
4. `settings_repo.py:23` - `__init__` has `if ctx is not None else` block

**Legacy function to remove:**
- `domain/snapshots/extractor.py:295-311` - `extract_document_tree()` violates architecture by importing infrastructure in domain layer
