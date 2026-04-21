# Task: Type-Specific Property Exclusions in Diff Filtering

## Goal
Allow property exclusions to be scoped by FreeCAD object `type_id` so a property can be excluded for one type (for example, `Template` on `TechDraw::DrawSVGTemplate`) while remaining visible for other types.

## Context
- Current behavior supports:
  - Excluding whole node types (`EXCLUDED_TYPES`)
  - Excluding property names globally (`EXCLUDED_PROPERTIES`)
- Current limitation: a global property exclusion hides that property name for all object types.
- Requested behavior: support type-scoped property exclusion defaults in config now.
- Constraint for this task: **config-only implementation now**, but architecture must cleanly support future FreeCAD Preferences UI/persistence.
- Relevant files and flow:
  - `freecad/diff_wb/config.py` currently defines hard-coded exclusion defaults.
  - `domain/settings/models.py` and `domain/settings/repository.py` define settings contract.
  - `infrastructure/freecad/settings_repo.py` adapts FreeCAD preferences and fallback defaults.
  - `domain/diff/engine.py` fetches exclusions and delegates to `TreeComparator`.
  - `domain/diff/comparator.py` applies property exclusions during node/property diff.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Add `EXCLUDED_PROPERTIES_BY_TYPE: dict[str, list[str]]` in `config.py` | Minimal scope for immediate need; explicit and readable defaults | Encode rules as custom strings in one list (rejected: weaker typing and harder validation) |
| Extend `Settings` and `SettingsRepository` with `excluded_properties_by_type` now | Future-proofs domain contract so Preferences support can be added without comparator/engine refactor | Keep this data outside settings for now (rejected: creates second config path and later migration churn) |
| Compute effective exclusions as `global ∪ per-type(old) ∪ per-type(new)` when comparing matched nodes | Correct when node type changes across snapshots; prevents false positives | Use only new type or only old type (rejected: asymmetric and can leak/over-filter on type changes) |

## Architecture Impact

### Modules affected now
1. `freecad/diff_wb/config.py`
   - Add `EXCLUDED_PROPERTIES_BY_TYPE` defaults.
2. `freecad/diff_wb/domain/settings/models.py`
   - Add `excluded_properties_by_type` field to `Settings` dataclass.
3. `freecad/diff_wb/domain/settings/repository.py`
   - Add `get_excluded_properties_by_type()` to `SettingsRepository` protocol.
4. `freecad/diff_wb/infrastructure/freecad/settings_repo.py`
   - Implement `get_excluded_properties_by_type()` using config fallback for now.
   - Include new field in `get_settings()`.
5. `freecad/diff_wb/domain/diff/engine.py`
   - Fetch type-specific exclusions and pass to comparator.
6. `freecad/diff_wb/domain/diff/comparator.py`
   - Add type-aware property exclusion logic.

### Test modules affected now
1. `tests/unit/domain/diff/test_comparator.py`
   - Add behavior tests for type-specific property filtering.
2. `tests/unit/domain/diff/test_engine.py`
   - Add/adjust settings-repo-based tests for type-scoped filtering through engine.
3. `tests/fakes/fake_repositories.py`
   - Extend fake settings repository support for `excluded_properties_by_type`.

### Public vs private interfaces
- **Public contract changes**:
  - `Settings.excluded_properties_by_type`
  - `SettingsRepository.get_excluded_properties_by_type()`
  - `TreeComparator.compare_snapshots(..., excluded_properties_by_type)`
- **Internal/private changes**:
  - Comparator helper(s) for effective exclusion set computation.

### Dependency boundaries
- Domain remains pure and does not depend on FreeCAD APIs.
- Infrastructure remains responsible for adapting persisted settings (now fallback-only).
- No UI coupling introduced in domain/comparator.

## FreeCAD Dependency
- [x] No FreeCAD required (pure code)
- [ ] FreeCAD required (follow exploration phase)

Rationale: This task modifies domain/config/infrastructure contracts and comparison logic with unit-testable behavior. No FreeCAD runtime API exploration is required for implementation.

## Implementation Plan
**IMPORTANT:** For each phase, tests are written before implementation.

### Phase 1: Extend settings contract for type-specific exclusions
- [ ] Write tests for updated settings contract and fake repository behavior
  - [ ] `FakeSettingsRepository` returns configured `excluded_properties_by_type`
  - [ ] `get_settings()` includes `excluded_properties_by_type`
- [ ] Implement settings contract changes
  - [ ] Add `EXCLUDED_PROPERTIES_BY_TYPE` to `config.py`
  - [ ] Add `excluded_properties_by_type` to `Settings` dataclass
  - [ ] Add `get_excluded_properties_by_type()` to `SettingsRepository`
  - [ ] Implement fallback method in `FreeCADSettingsRepository`
  - [ ] Include field in `FreeCADSettingsRepository.get_settings()`
- [ ] Refactor for clarity
  - [ ] Keep naming consistent: `excluded_properties_by_type`
  - [ ] Ensure return values are copied/immutable-safe where applicable

Code sketch:

```python
# config.py
EXCLUDED_PROPERTIES_BY_TYPE = {
    "TechDraw::DrawSVGTemplate": ["Template"],
}

# domain/settings/models.py
@dataclass(frozen=True)
class Settings:
    excluded_types: list[str]
    excluded_properties: list[str]
    excluded_properties_by_type: dict[str, list[str]]
```

### Phase 2: Add type-aware filtering in comparator and engine
- [ ] Write tests first (comparator)
  - [ ] Excludes `Template` for `TechDraw::DrawSVGTemplate`
  - [ ] Does not exclude `Template` for unrelated types
  - [ ] For type change old→new, uses union of per-type rules from both sides
  - [ ] Global exclusions remain applied for all types
- [ ] Write tests first (engine)
  - [ ] Engine passes per-type map from settings repo into comparator flow
- [ ] Implement
  - [ ] Extend `DiffEngine` to fetch `excluded_properties_by_type`
  - [ ] Extend `TreeComparator.compare_snapshots()` and internal calls
  - [ ] Compute effective excluded properties per node compare:
    - [ ] `global`
    - [ ] plus `by_type[old_node.type_id]`
    - [ ] plus `by_type[new_node.type_id]`
  - [ ] For added/deleted nodes, combine global with that node’s type-specific entries
- [ ] Refactor
  - [ ] Extract helper for effective exclusion set assembly
  - [ ] Keep deterministic property ordering behavior unchanged

Code sketch:

```python
def _effective_exclusions(
    global_excluded: list[str],
    by_type: dict[str, list[str]],
    old_type: str | None,
    new_type: str | None,
) -> set[str]:
    effective = set(global_excluded)
    if old_type is not None:
        effective.update(by_type.get(old_type, []))
    if new_type is not None:
        effective.update(by_type.get(new_type, []))
    return effective
```

## Test Strategy
- **Unit tests**:
  - Comparator logic for type-aware filtering
  - Engine orchestration with mocked settings repo
  - Settings/fakes contract updates
- **Integration tests**:
  - Application-level comparison flow with fake settings repository wiring (no FreeCAD runtime dependency)

## Findings & Notes
- `docs/PLAN.md` is not present in repository; `docs/ProjectState.md` was used for project-state context.
- Existing architecture cleanly supports this change in the pure-code path.
- This plan intentionally avoids implementing FreeCAD preference UI now, while locking in a stable canonical settings shape to avoid future domain/comparator changes.
