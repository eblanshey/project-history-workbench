# Task: Edit Diff Settings in FreeCAD Preferences Window

## Goal
Add a real Diff Workbench Preferences page in FreeCAD so users can edit settings currently hardcoded in `config.py`: `EXCLUDED_TYPES`, `EXCLUDED_PROPERTIES`, `EXCLUDED_PROPERTIES_BY_TYPE`, and `FLOAT_PRECISION`.

## Context
- User wants settings editable in FreeCAD settings window.
- Existing `FreeCADSettingsRepository` already reads some settings from `ParamGet`, but currently:
  - `ExcludedTypes` and `ExcludedProperties` are comma-separated only.
  - `ExcludedPropertiesByType` always falls back to config defaults.
  - `float_precision` is always hardcoded from `config.py`.
- Required UX for each exclusion setting:
  - Radio: **Use default exclusion list** vs **Use custom exclusion list**.
  - When switching Default ➜ Custom: if custom list is still uninitialized/empty, prefill textarea with defaults.
  - After user edits once, never auto-refill again, even if user later saves an empty textarea.
- FreeCAD reference patterns confirm using `FreeCADGui.addPreferencePage(MyPageClass, "Group")` with page class methods `loadSettings()` / `saveSettings()` and optional `.form` widget.
- `docs/PLAN.md` does not exist in repository; planning context taken from `docs/ProjectState.md` and `docs/Architecture.md`.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use class-based preference page (`addPreferencePage(page_class, group)`) instead of plain `.ui` only | Need custom toggle/prefill behavior and parsing logic | Pure `.ui` with only `Gui::Pref*` widgets (rejected: insufficient for one-time prefill semantics) |
| Persist explicit mode flags per exclusion list (`UseDefault...`) and explicit custom text values | Distinguish “missing value” from “intentionally empty custom list” | Infer mode from empty/non-empty string (rejected: cannot preserve intentional empties) |
| Persist one-time initialization flags per custom list (`Custom...Initialized`) | Enforces “prefill only first switch to custom” | Refill whenever custom empty (rejected: violates requirement) |
| Store list content as newline text in preferences (not CSV) | Matches textarea UX (“one line per value”), avoids comma parsing edge cases | Keep CSV storage (rejected: fragile and mismatched UX) |
| Define type-specific custom list line format as `TypeId -> PropertyName` per line | Human-editable, deterministic, and avoids collision with `::` inside FreeCAD type IDs | JSON blob in textarea (rejected for now: less user-friendly), tab/CSV delimiters (rejected: lower discoverability) |
| Make float precision actually effective in compare + display paths | Setting must matter, not just persist | Persist-only now (rejected: surprising/no visible effect) |
| No backward-compat migration for old comma keys in MVP | Project rule says no backward-compat needed for unused MVP | Dual-read old+new keys (rejected: extra complexity) |

## Architecture Impact
### Where code will live
- **UI layer**: new preferences page class + optional UI resource file under `freecad/diff_wb/ui/views/` and `freecad/diff_wb/resources/ui/`.
- **Entry points**: register preference page in `entrypoints/workbench.py` during `Initialize()`.
- **Application layer**: add settings read/save actions so UI does not call infrastructure directly.
- **Domain layer**: extend `SettingsRepository` port with save operation and precision retrieval contract.
- **Infrastructure layer**: implement save/read mode flags, custom text, by-type parsing, and float precision persistence in `FreeCADSettingsRepository`.

### Modules/files affected
1. `freecad/diff_wb/entrypoints/workbench.py`
2. `freecad/diff_wb/ui/views/` (new preferences page module)
3. `freecad/diff_wb/resources/ui/` (new `.ui` file if used)
4. `freecad/diff_wb/application/actions/` (new get/save settings actions)
5. `freecad/diff_wb/application/di/container.py` (wire new actions)
6. `freecad/diff_wb/domain/settings/repository.py` (add save API)
7. `freecad/diff_wb/infrastructure/freecad/settings_repo.py` (full read/write implementation)
8. Float precision consumers:
   - `freecad/diff_wb/domain/diff/models.py`
   - `freecad/diff_wb/domain/tree/data_path.py`
   - `freecad/diff_wb/ui/presenters/diff_presenter.py`
   - `freecad/diff_wb/ui/views/diff_panel_view.py`
9. Tests under `tests/unit/...` for new actions/page/repo behavior.
10. `README.md` configuration section (align docs with actual behavior and new fields).

### SRP / interfaces / boundaries
- Keep parsing/serialization logic in infrastructure repository (single place for persistence format).
- Keep preference page focused on widget interaction and calling application actions.
- Public API changes:
  - `SettingsRepository.save_settings(settings: Settings, modes: ...)` (exact signature finalized in implementation)
  - New application actions exported via application package.
- Internal helpers (private):
  - `_parse_lines`, `_parse_by_type_lines`, `_serialize_by_type_lines`, `_apply_custom_toggle_prefill`.
- Dependency direction remains: UI ➜ Application ➜ Domain port; Infrastructure implements port.

## FreeCAD Dependency
- [ ] No FreeCAD required (pure code)
- [x] FreeCAD required (follow exploration phase)

Reason: this task adds FreeCAD Preferences UI registration and behavior tied to FreeCADGui lifecycle.

## Implementation Plan
**IMPORTANT:** Each phase lists tests before implementation (TDD order).

### Phase 1: FreeCAD Preferences API exploration and contract lock
- [x] Write exploration checks/spec first (expected signatures and lifecycle):
  - [x] `addPreferencePage(class, group)` usage contract
  - [x] `loadSettings()` and `saveSettings()` callback timing contract
  - [x] `Gui::PrefRadioButton` / `Gui::PrefTextEdit` persistence behavior assumptions
- [x] Exploration checks artifact (spec-first evidence):
  - [x] Check A: `addPreferencePage(class, group)` contract documented at `docs/api-exploration/freecad-preferences-page-api.md#check-addpreferencepage-contract`
  - [x] Check B: callback lifecycle documented at `docs/api-exploration/freecad-preferences-page-api.md#check-callback-lifecycle`
  - [x] Check C: pref widget persistence assumptions documented at `docs/api-exploration/freecad-preferences-page-api.md#check-pref-widgets-persistence`
- [x] Implement exploration artifacts:
  - [x] Add short exploration notes doc under `docs/api-exploration/` with verified signatures and examples.
  - [x] Confirm registration location (`DiffWorkbench.Initialize`) and non-duplication strategy.
- [x] Refactor plan details with confirmed API findings before coding phases.

Code sketch:
```python
# workbench.py (registration shape)
import FreeCADGui as Gui
from ..ui.views.settings_preferences_page import DiffSettingsPreferencesPage

Gui.addPreferencePage(DiffSettingsPreferencesPage, "Diff")
```

### Phase 2: Settings persistence model and repository behavior
- [x] Write tests first (repository unit tests with fake ParamGet):
  - [x] default mode returns hardcoded config defaults
  - [x] custom mode returns parsed line-based values
  - [x] custom empty list is preserved as empty (no fallback)
  - [x] first switch default➜custom prefill marker behavior (initialized flag)
  - [x] by-type parse (`TypeId -> Property`) and serialization round-trip
  - [x] float precision read/write + bounds handling
- [x] Implement repository changes:
  - [x] Add explicit keys per setting mode/value/initialized flag.
  - [x] Implement read/write for all four settings.
  - [x] Keep defaults sourced from `config.py` when mode=default.
  - [x] Add robust parse/normalize helpers (trim, ignore blank lines).
- [x] Refactor:
  - [x] isolate private parser helpers for SRP
  - [x] ensure method names clearly separate public contract vs internal parsing.

Code sketch:
```python
def _parse_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]

def _parse_by_type_lines(raw: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        type_id, prop = [p.strip() for p in s.split("->", 1)]
        out.setdefault(type_id, []).append(prop)
    return out
```

### Phase 3: Preferences page UI + application wiring
- [x] Write tests first:
  - [x] preference page loads current mode/value into controls
  - [x] toggle default/custom shows/hides textarea correctly
  - [x] first default➜custom prefill happens only when custom not initialized
  - [x] after edit/save, later empty custom remains empty (no repopulation)
  - [x] save triggers application action with normalized payload
  - [x] workbench initializes and registers preference page once
- [x] Implement:
  - [x] Create `DiffSettingsPreferencesPage` class with `.form`, `loadSettings`, `saveSettings`.
  - [x] Build UI controls for:
    - [x] Excluded types (radio + textarea)
    - [x] Excluded properties (radio + textarea)
    - [x] Excluded properties by type (radio + textarea)
    - [x] Float precision (spinbox)
  - [x] Add application actions (`GetDiffSettingsAction`, `SaveDiffSettingsAction`) and wire in container.
  - [x] Register page in workbench `Initialize()`.
  - [x] Add class-level one-time registration guard to prevent duplicate `addPreferencePage(...)` calls in reload/test scenarios.
- [x] Refactor:
  - [x] private UI helper methods (`_bind_signals`, `_sync_visibility`, `_maybe_prefill_from_defaults`).
  - [x] keep FreeCAD-specific calls inside UI/entrypoint modules only.

Code sketch:
```python
def _on_custom_toggled(self, checked: bool, field: str) -> None:
    if not checked:
        return
    if not self._state[field].initialized and not self._state[field].custom_text:
        self._set_textarea(field, "\n".join(self._state[field].default_values))
    self._show_textarea(field, True)
```

### Phase 4: Make float precision effective + integration validation
- [x] Write tests first:
  - [x] precision from settings affects float equality logic where diff state is computed
  - [x] precision affects presenter/view formatting consistently
  - [x] regression tests for existing default precision behavior
- [x] Implement:
  - [x] propagate runtime precision from settings to compare/display call paths (remove hardwired `config.FLOAT_PRECISION` dependency in active paths).
  - [x] ensure fallback still uses config default when no custom precision set.
- [x] Manual FreeCAD integration validation (required):
  - [x] open Preferences ➜ Diff page appears
  - [x] switch default/custom modes and verify one-time prefill behavior
  - [x] save, reopen preferences, verify persistence including intentional empty custom lists
  - [x] change float precision and verify visible diff/format behavior updates

Code sketch:
```python
settings = settings_repo.get_settings()
precision = settings.float_precision
# pass precision into compare/format paths instead of importing config constant
```

## Test Strategy
- **Unit tests**
  - Repository parsing/persistence semantics (mode flags, initialized flags, empty custom persistence)
  - Application actions for get/save settings orchestration
  - Preference page UI behavior (toggle, prefill, serialization of textareas)
  - Precision propagation and float comparison/formatting behavior
- **Integration tests**
  - Application-level action wiring tests with fakes (non-FreeCAD runtime)
  - **Manual FreeCAD verification only** for Preferences dialog and FreeCADGui registration behavior

## Findings & Notes
- FreeCAD source confirms both signatures:
  - `FreeCADGui.addPreferencePage(path, group)`
  - `FreeCADGui.addPreferencePage(page_class, group)`
- Python preference page supports `.form` attribute and optional `loadSettings()/saveSettings()` methods.
- Callback timing confirmed from source:
  - `loadSettings()` called when preference pages are created/reloaded.
  - `saveSettings()` called when Preferences dialog applies/accepts changes.
- `Gui::PrefRadioButton` and `Gui::PrefTextEdit` persist bool/string via `prefEntry` + `prefPath` when `onRestore()/onSave()` is called.
- Encoding assumption note: `PrefTextEdit` persistence path uses ASCII-oriented storage calls; non-ASCII behavior must be validated in a later implementation phase (or explicitly constrained/documented).
- Phase 1 exploration notes added at `docs/api-exploration/freecad-preferences-page-api.md` with source-backed examples.
- Registration location confirmed as `DiffWorkbench.Initialize`; non-dup strategy is a class-level guard flag around `Gui.addPreferencePage(...)`.
- `docs/PLAN.md` is missing in this repository; used `docs/ProjectState.md` as project-state source.
- README currently claims preferences panel exists; documentation should be updated as part of implementation completion.
