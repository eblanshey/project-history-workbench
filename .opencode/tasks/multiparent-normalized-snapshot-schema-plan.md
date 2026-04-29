# Task: Support Multi-Parent Tree Occurrences with Normalized Snapshot Schema

## Goal
Support FreeCAD objects claimed by multiple parents (same object shown in multiple tree locations) while preserving correctness, deterministic YAML text diffs, and efficient extraction/diff algorithms.

## Context
Current snapshot extraction and diff logic assume one parent per object occurrence and one node identity per object ID. This fails for valid FreeCAD cases where one object is claimed under multiple parents (example: one sketch reused by both Pad and Hole).

Observed current failure:
- Extractor keeps first parent only and logs duplicate parent claim ignored.
- Traversal uses global object-name `visited`, so second occurrence path never appears.
- Comparator indexes by object ID only, so duplicate occurrences with same ID collide and overwrite.

### FreeCAD source research findings (meaningful evidence)
Multi-parent support is native in FreeCAD tree layer and is not sketch-specific.

1. **Core tree supports multiple parents/instances explicitly**
   - Parent map stores **set** of parents per child:
     - `freecad-source/src/Gui/Tree.h:427`
   - Parent insert/remove handling:
     - `freecad-source/src/Gui/Tree.cpp:340-352`, `360-370`
   - Multiple instances of same object in tree explicitly handled:
     - `freecad-source/src/Gui/Tree.cpp:4737-4758`, `5607-5614`

2. **Not only sketches; many view providers claim reusable children**
   - PartDesign sketch/profile based:
     - `src/Mod/PartDesign/Gui/ViewProviderSketchBased.cpp:75-83`
     - `src/Mod/PartDesign/Gui/ViewProviderHole.cpp:49-59`
   - Part features:
     - `src/Mod/Part/Gui/ViewProviderExtrusion.cpp:41-46`
     - `src/Mod/Part/Gui/ViewProviderBoolean.cpp:109-116`
   - Link wrappers can also forward/claim children:
     - `src/Gui/ViewProviderLink.cpp:2579-2614`

3. **Child object can have its own children**
   - Claim mechanism is generic:
     - `src/Gui/ViewProvider.cpp:962-973`
   - Recursive claiming available:
     - `src/Gui/ViewProvider.cpp:975-989`

4. **Tree child sets are effectively object-level shared**
   - `DocumentObjectData` shared per object and reused by instances:
     - `src/Gui/Tree.cpp:311-315`, `375-377`, `4405-4411`
   - Practical implication: if an object appears in multiple locations, its own child set is generally the same across those locations in tree logic.

Planning note:
- `docs/PLAN.md` requested by process not present at expected path.
- Architecture basis used: `docs/Architecture.md`.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use **normalized snapshot schema** with separate `objects[]` and `occurrences[]` | Avoid duplicating full property payload for multiply-placed objects while preserving per-occurrence topology/order | Keep flat duplicated nodes (rejected: payload duplication, less explicit model) |
| Object identity key is `name` (FreeCAD object name) | Stable document-unique key in practice and human-readable | Object `id` as identity (rejected: collides across occurrences and not semantic key for topology) |
| Occurrence identity key is `path` | Deterministic, no random IDs, directly useful for UI selection and lookups | Random UUID per occurrence (rejected: snapshot churn), synthetic hash IDs (deferred) |
| `after` stores **sibling occurrence path** | Unambiguous under reused object names across branches | Name-based `after` (rejected: ambiguous with multi-parent reuse) |
| Drop `parent` field from occurrence rows | Parent derivable from `path`, reduces redundancy/drift | Keep explicit parent (rejected for MVP simplicity) |
| Keep numeric object `id` only for YAML ordering/readability | Preserves stable object list sorting and diff-friendly output | Use `id` as semantic identity (rejected) |
| YAML arrays (not dict maps) for objects/occurrences | Simpler YAML editing/readability while keeping runtime indexes possible | Dict-based sections (rejected by product decision) |

## Architecture Impact
- **Domain snapshot model:**
  - `freecad/diff_wb/domain/snapshots/models.py`
  - Add normalized classes (`SnapshotObject`, `SnapshotOccurrence`) and evolve `Snapshot` structure.
- **Snapshot extraction (FreeCAD-dependent):**
  - `freecad/diff_wb/domain/snapshots/gui_extractor.py`
  - Build object table + occurrence table with multi-parent-safe traversal.
- **Persistence schema:**
  - `freecad/diff_wb/infrastructure/persistence/snapshot_yaml.py`
  - Replace v1 flat `objects` node-list format with v2 normalized arrays.
- **Diff engine/comparator:**
  - `freecad/diff_wb/domain/diff/comparator.py`
  - Shift from ID-centric node compare to normalized object+occurrence compare.
- **Tests:**
  - Snapshot extractor unit tests
  - YAML serialization/deserialization tests
  - Comparator tests for multi-parent occurrence behavior

Dependency boundaries remain compliant:
- Domain model/diff logic remains pure.
- FreeCAD-specific behavior isolated to extractor (domain snapshot query adapter boundary unchanged in practice).

## FreeCAD Dependency
- [ ] No FreeCAD required (pure code)
- [x] FreeCAD required (follow exploration phase)

Reason:
- FreeCAD source/API behavior drove the model decisions and must be validated against real claimChildren semantics.

## Implementation Plan
**IMPORTANT:** Tests first for each phase, then implementation.

### Phase 1: Define normalized snapshot domain model and contracts
- [ ] Write tests first for model invariants:
  - [ ] Object names are unique keys.
  - [ ] Occurrence paths are unique keys.
  - [ ] Parent derivation from `path` behaves correctly for roots/non-roots.
  - [ ] `after` path, when present, must reference a sibling under same derived parent.
- [ ] Implement model refactor in `domain/snapshots/models.py`:
  - [ ] Add `SnapshotObject` dataclass.
  - [ ] Add `SnapshotOccurrence` dataclass.
  - [ ] Update `Snapshot` to hold normalized collections and helper indexes/lookups.
  - [ ] Maintain clear public API via `__all__`.

Detailed code sketch:
```python
@dataclass(frozen=True)
class SnapshotObject:
    name: str                  # identity key
    id: int                    # sorting only in YAML
    type_id: str
    properties: dict[str, Property]


@dataclass(frozen=True)
class SnapshotOccurrence:
    path: str                  # identity key
    object_name: str           # FK to SnapshotObject.name
    after: str | None = None   # sibling occurrence path

    @property
    def parent_path(self) -> str | None:
        if "/" not in self.path:
            return None
        return self.path.rsplit("/", 1)[0]
```

### Phase 2: Extractor refactor for multi-parent occurrences
- [ ] Write tests first:
  - [ ] One sketch claimed by Pad and Hole emits two occurrences with different paths.
  - [ ] No duplicate-parent warning for valid multi-claim.
  - [ ] Cycle-safe traversal terminates.
  - [ ] Root detection uses “has no parents,” not “first-claim winner.”
- [ ] Implement extractor changes:
  - [ ] Build `parent_to_children` as today.
  - [ ] Build `child_to_parents: dict[str, set[str]]` (accumulate all parents).
  - [ ] Remove global name-visited suppression; traverse by occurrence path context.
  - [ ] Add ancestry-based cycle guard per traversal branch.
  - [ ] Emit:
    - one `SnapshotObject` per object name
    - one `SnapshotOccurrence` per traversed path

Detailed traversal sketch:
```python
queue: deque[tuple[str, str, str | None, tuple[str, ...]]] = deque()
# (obj_name, path, after_occ_path, ancestors)

while queue:
    obj_name, occ_path, after, ancestors = queue.popleft()
    occurrences.append(SnapshotOccurrence(path=occ_path, object_name=obj_name, after=after))

    child_names = parent_to_children.get(obj_name, [])
    prev_child_occ: str | None = None
    for child_name in child_names:
        if child_name in ancestors:
            continue  # cycle guard
        child_occ = f"{occ_path}/{child_name}"
        queue.append((child_name, child_occ, prev_child_occ, (*ancestors, child_name)))
        prev_child_occ = child_occ
```

### Phase 3: YAML v2 schema implementation
- [ ] Write tests first:
  - [ ] Serialize normalized snapshot to expected v2 structure.
  - [ ] Deserialize back to equivalent normalized snapshot.
  - [ ] Deterministic ordering:
    - objects sorted by numeric `id`
    - occurrences sorted by `path`
  - [ ] Repeated object usage across occurrences round-trips correctly.
- [ ] Implement v2 schema in serializer/deserializer (`snapshot_yaml.py`).
- [ ] No backward compatibility loader required (MVP decision).

YAML v2 target:
```yaml
v: 2
timestamp: 2026-04-29T12:34:56Z
uid: 8b9f...

objects:
  - name: Body
    id: 12
    type_id: PartDesign::Body
    properties: {}
  - name: Sketch006
    id: 47
    type_id: Sketcher::SketchObject
    properties: {}

occurrences:
  - path: Body
    object: Body
    after: null
  - path: Body/Pad001
    object: Pad001
    after: null
  - path: Body/Hole001
    object: Hole001
    after: Body/Pad001
  - path: Body/Pad001/Sketch006
    object: Sketch006
    after: null
  - path: Body/Hole001/Sketch006
    object: Sketch006
    after: null
```

### Phase 4: Comparator redesign for normalized model
- [ ] Write tests first:
  - [ ] No false collisions when same object appears in multiple occurrences.
  - [ ] Property change on shared object appears on each occurrence path.
  - [ ] Add/remove of one occurrence path changes only that occurrence.
  - [ ] Ordering changes detected via occurrence `after` paths.
- [ ] Implement two-pass comparison:
  1. object-state comparison by object `name`.
  2. topology comparison by occurrence `path` + `after`.
- [ ] Compose `NodeDiff` hierarchy for UI using occurrence paths.

Detailed comparison sketch:
```python
old_obj = {o.name: o for o in old.objects}
new_obj = {o.name: o for o in new.objects}
old_occ = {o.path: o for o in old.occurrences}
new_occ = {o.path: o for o in new.occurrences}

# object property changes
changed_objects = compare_objects(old_obj, new_obj)

# occurrence add/delete/move/order
occ_diffs = compare_occurrences(old_occ, new_occ)

# project to node diffs by occurrence path
for path, occ in new_occ.items():
    object_changed = occ.object_name in changed_objects
    # build NodeDiff at this path
```

### Phase 5: UI/presenter adaptation and invariants hardening
- [ ] Write tests first:
  - [ ] Node selection by path still resolves property panel.
  - [ ] Duplicate object usage across branches displays both branches correctly.
- [ ] Ensure presenter/view contracts remain path-based (minimal UI churn).
- [ ] Ensure `find_by_path` and changed-path collection still deterministic.

### Phase 6: Final cleanup, documentation, and validation
- [ ] Write/extend tests for schema invariants and edge cases.
- [ ] Update module comments and public API docs to reflect normalized snapshot semantics.
- [ ] Add explicit note in serializer/comparator docs:
  - `id` is **ordering/readability only**, not identity.

## Test Strategy
- **Unit tests (primary):**
  - `tests/unit/domain/snapshots/test_extractor.py`
  - `tests/unit/domain/snapshots/test_models.py` (or new normalized model tests)
  - `tests/unit/infrastructure/persistence/test_snapshot_yaml.py`
  - `tests/unit/domain/diff/test_comparator.py`
- **Integration tests:**
  - Update/add where current snapshot flat assumptions exist.
  - Validate end-to-end diff tree rendering remains path-correct.
- **Manual FreeCAD validation (targeted):**
  - One sketch reused by multiple features in same body.
  - Link-heavy doc to ensure no regression on claimChildren behavior.

## Findings & Notes
1. Flat single-parent map and global object visited set are root causes of missing occurrences.
2. ID-centric compare is invalid when one object appears at multiple paths.
3. FreeCAD tree natively tracks multiple parents with set semantics; model should mirror this behavior.
4. Normalized schema removes repeated property payload while preserving per-occurrence ordering (`after`).
5. Using `path` as occurrence identity avoids random IDs and keeps deterministic YAML.
6. `after` must reference sibling occurrence path for unambiguous ordering.
7. Arrays in YAML are acceptable for readability; runtime should build transient indexes for O(1) lookups.
8. Keep model and YAML closely aligned to avoid conceptual divergence.
