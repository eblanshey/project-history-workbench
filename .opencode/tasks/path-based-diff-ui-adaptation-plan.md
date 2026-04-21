# Task: Path-Based Diff + Nested Subpath UI Adaptation

## Goal

Adapt diff-domain and UI property rendering to the new `DataPath`-based `Property` model so that:

1. all property sub-path rows are shown (including unchanged),
2. expressions are nested under their corresponding path row,
3. sub-paths are rendered hierarchically (e.g. `Placement -> Base -> x -> Expression`),
4. parent nodes are marked changed when any descendant path changes,
5. changed branches auto-expand and unchanged branches remain collapsed,
6. added properties mark all sub-path rows as ADDED (green).

## Context

The previous plan (`path-based-data-classes-plan-revised.md`) introduces `DataPath` value objects and removes legacy APIs (`PropertyType`, `Property.create`, `Property.expression`, `Property.get_children`).

The current diff/presenter/view stack still depends heavily on those removed APIs. This plan updates only downstream diff + UI property-display behavior.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Introduce explicit `PropertyPathDiff` domain model | Makes path-level value + expression diffs deterministic and testable | Keep ad-hoc diff logic in presenter |
| Flatten `DataPath` into `path -> PropertyPathValue` before compare | Uniform comparison for Primitive/Vector/Placement/List/Unknown | Type-specific compare branches |
| Keep property-level row + nested path rows | Preserves top-level property identity while exposing full path detail | Show only paths without parent property row |
| Nest expression rows under each path row (`Expression`) | Matches requested UX and keeps expression scope explicit | Flat sibling expression rows (`-> Expression`) |
| Keep expression text on `PropertyPathValue`; do not duplicate on `PropertyPathDiff` | Avoids redundant state and keeps diff model minimal | Store `old_expression`/`new_expression` as extra fields |
| Build nested sub-path tree in presenter, keep view as renderer | Respects boundaries (UI -> presenter transforms, view renders) | Build nesting in view |
| Synthetic parent path state is aggregated from descendants | Enables `Base` / `Rotation` rows to reflect descendant changes | Keep synthetic parents always UNCHANGED |
| Path tokenization splits mixed named/indexed segments (`Constraints[0].Value` -> `Constraints` / `[0]` / `Value`) | Produces correct hierarchical nesting for list-like children under named parents | Treat `Constraints[0]` as a single token |
| Container rows show own `"."` value when present; otherwise show bracketed summary derived from children | Matches FreeCAD-like UX (`Position -> [x y z]`) while preserving drill-down into children | Leave container value empty or show row name in value columns |
| End-to-end ordering uses one canonical sort key for path diffs and presenter tree children | Prevents UI jitter and non-deterministic row ordering across runs | Independent per-layer sorting rules |
| Expansion driven by change presence | Meets requested UX: changed expanded, unchanged collapsed | Expand everything by default |
| Treat `"."` as the only canonical root path key | Aligns with updated DataPath/YAML contract and removes empty-root ambiguity | Support both `"."` and `""` |
| No manual testing instructions in this plan | Explicit user requirement for this planning task | Add manual test phase |

## Architecture Impact

### Modules Affected

1. `freecad/diff_wb/domain/diff/models.py`
2. `freecad/diff_wb/domain/diff/comparator.py`
3. `freecad/diff_wb/domain/diff/__init__.py`
4. `freecad/diff_wb/ui/presenters/diff_presenter.py`
5. `freecad/diff_wb/ui/presenters/presentation_models.py` (minor/no shape change expected)
6. `freecad/diff_wb/ui/views/diff_panel_view.py`

### Public vs Private Interfaces

- **Public (domain diff):**
  - `PropertyPathDiff` (exported in `domain/diff/__init__.py`)
  - `PropertyDiff.path_diffs` (public contract for presenter)
- **Private (domain diff internals):**
  - path flatten helpers (`_flatten_data_path`, `_merge_path_maps`, `_path_sort_key`)
- **Public (presenter/view boundary):**
  - existing `PropertyPresentation` remains the exchange type
- **Private (presenter internals):**
  - `_split_rel_path`, `_insert_path_diff`, `_aggregate_state`, `_path_tree_to_presentations`, `_derive_container_summary`

### Dependency Boundaries

- Domain diff depends only on domain tree (`DataPath`, `PropertyPathValue`) and remains FreeCAD-independent.
- Presenter consumes domain diffs and maps them into UI presentation trees.
- View does not compute business diff logic; it only renders provided tree + expansion/color rules.

## FreeCAD Dependency

- [x] No FreeCAD required (pure code path)
- [ ] FreeCAD required (follow exploration phase)

## Implementation Plan

**Rule:** Every phase lists tests before implementation (TDD order).

### Phase 1: Path-level diff primitives in domain

#### Tests first

- [x] Add `tests/unit/domain/diff/test_property_path_diffs.py`:
  - [x] path flattening for `PrimitiveData`, `QuantityData`, `VectorData`, `RotationData`, `PlacementData`, `ListData`, `UnknownData`
  - [x] flattening preserves root path `"."` (no empty-root fallback)
  - [x] list flattening emits keys like `.`, `[0]`, `[0].Value`, `[1].Type`
  - [x] all paths included (unchanged included)
  - [x] float tolerance for path value equality
  - [x] expression state computed independently of value state

#### Implement

- [x] Add/extend path-flatten helpers in `domain/diff/models.py` (or private helper module under `domain/diff/` if preferred for SRP).
- [x] Introduce `PropertyPathDiff` and use it inside `PropertyDiff`.

Code snippet:

```python
# freecad/diff_wb/domain/diff/models.py
# File responsibility: Domain diff models and path-level comparison state.

from dataclasses import dataclass, field
import math

from ..tree import Property
from ..tree.data_path import (
    DataPath,
    ListData,
    PropertyPathType,
    PropertyPathValue,
)


@dataclass(frozen=True)
class PropertyPathDiff:
    path: str
    old_value: PropertyPathValue | None
    new_value: PropertyPathValue | None
    value_state: DiffState = field(init=False)
    expression_state: DiffState = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "value_state", _calc_value_state(self.old_value, self.new_value))
        old_expr = _path_expression(self.old_value)
        new_expr = _path_expression(self.new_value)
        object.__setattr__(self, "expression_state", _calc_expression_state(old_expr, new_expr))


def _path_expression(value: PropertyPathValue | None) -> str | None:
    return value.expression if value is not None else None


def _calc_value_state(old: PropertyPathValue | None, new: PropertyPathValue | None) -> DiffState:
    if old is None:
        return DiffState.ADDED if new is not None else DiffState.UNCHANGED
    if new is None:
        return DiffState.DELETED
    return DiffState.UNCHANGED if _path_values_equal(old, new) else DiffState.MODIFIED


def _calc_expression_state(old_expr: str | None, new_expr: str | None) -> DiffState:
    if old_expr is None:
        return DiffState.ADDED if new_expr is not None else DiffState.UNCHANGED
    if new_expr is None:
        return DiffState.DELETED
    return DiffState.UNCHANGED if old_expr == new_expr else DiffState.MODIFIED


def _path_values_equal(old: PropertyPathValue, new: PropertyPathValue) -> bool:
    if old.type_ != new.type_:
        return False
    if old.type_ == PropertyPathType.FLOAT:
        return math.isclose(float(old.value), float(new.value), rel_tol=1e-9, abs_tol=1e-9)
    return old.value == new.value


def _flatten_data_path(value: DataPath, prefix: str = "") -> dict[str, PropertyPathValue]:
    # ListData has both list-level paths and indexed items.
    if isinstance(value, ListData):
        out: dict[str, PropertyPathValue] = {}
        for rel, pv in value.paths.items():
            out[_join_path(prefix, rel)] = pv
        for i, item in enumerate(value.items):
            item_prefix = _join_path(prefix, f"[{i}]")
            out.update(_flatten_data_path(item, item_prefix))
        return out

    # Any non-list DataPath with `paths` dict
    if hasattr(value, "paths"):
        out: dict[str, PropertyPathValue] = {}
        for rel, pv in value.paths.items():
            full = _join_path(prefix, rel)
            out[full] = pv
        return out

    return {}


def _join_path(prefix: str, rel: str) -> str:
    # Joins a relative DataPath key into a full flattened path.
    #
    # Examples:
    # - _join_path("", ".") -> "."            (property root)
    # - _join_path("[0]", ".") -> "[0]"        (item root)
    # - _join_path("", "Base.x") -> "Base.x"   (top-level dotted path)
    # - _join_path("[0]", "Value") -> "[0].Value"
    # - _join_path("Constraints", "[2]") -> "Constraints[2]"
    if rel == ".":
        return prefix or "."
    if not prefix:
        return rel
    if rel.startswith("["):
        return f"{prefix}{rel}"
    return f"{prefix}.{rel}"
```

---

### Phase 2: PropertyDiff/NodeDiff semantics switched to path diffs

#### Tests first

- [x] Update/add tests in `tests/unit/domain/diff/test_models.py`:
  - [x] `PropertyDiff.path_diffs` contains all paths (unchanged included)
  - [x] parent `PropertyDiff.state` becomes MODIFIED when any descendant path value changes
  - [x] parent `PropertyDiff.state` becomes MODIFIED when only expression changes
  - [x] ADDED property => all path diffs ADDED
  - [x] DELETED property => all path diffs DELETED
  - [x] remove legacy expectations tied to `get_children()`

#### Implement

- [x] Refactor `PropertyDiff` to compute `path_diffs` from flattened path maps.
- [x] Remove legacy child-generation and unknown-object reflection logic.
- [x] Keep `NodeDiff` state calculation based on property state and child node state.

Code snippet:

```python
@dataclass(frozen=True)
class PropertyDiff:
    property_name: str
    old_value: Property | None
    new_value: Property | None
    state: DiffState = field(init=False)
    path_diffs: list[PropertyPathDiff] = field(init=False)

    def __post_init__(self) -> None:
        old_paths = _flatten_data_path(self.old_value.value) if self.old_value else {}
        new_paths = _flatten_data_path(self.new_value.value) if self.new_value else {}

        all_paths = sorted(set(old_paths) | set(new_paths), key=_path_sort_key)
        diffs = [PropertyPathDiff(path=p, old_value=old_paths.get(p), new_value=new_paths.get(p)) for p in all_paths]
        object.__setattr__(self, "path_diffs", diffs)

        if self.old_value is None:
            object.__setattr__(self, "state", DiffState.ADDED if self.new_value is not None else DiffState.UNCHANGED)
            return
        if self.new_value is None:
            object.__setattr__(self, "state", DiffState.DELETED)
            return

        has_value_change = any(d.value_state != DiffState.UNCHANGED for d in diffs)
        has_expr_change = any(d.expression_state != DiffState.UNCHANGED for d in diffs)
        object.__setattr__(self, "state", DiffState.MODIFIED if (has_value_change or has_expr_change) else DiffState.UNCHANGED)


def _path_sort_key(path: str) -> tuple:
    # Keep root first, then natural segment order.
    if path == ".":
        return (-1,)
    segments = _split_path_for_sort(path)
    return tuple(segments)


def _split_path_for_sort(path: str) -> list[tuple[int, str | int]]:
    """Split `Base.x`, `[10].Value`, `[2]` into sortable typed segments."""
    out: list[tuple[int, str | int]] = []
    token: list[str] = []
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if token:
                out.append((0, "".join(token)))
                token = []
            i += 1
            continue
        if ch == "[":
            if token:
                out.append((0, "".join(token)))
                token = []
            j = path.find("]", i)
            idx = int(path[i + 1 : j])
            out.append((1, idx))
            i = j + 1
            continue
        token.append(ch)
        i += 1
    if token:
        out.append((0, "".join(token)))
    return out
```

---

### Phase 3: Comparator wiring and deterministic ordering

#### Tests first

- [x] Update `tests/unit/domain/diff/test_comparator.py`:
  - [x] migrate fixtures from `Property.create(...)` to DataPath-backed `Property(...)`
  - [x] verify unchanged paths are still emitted in `path_diffs`
  - [x] verify property exclusion still works
  - [x] verify ordering stability for path keys with indices (`[2]` before `[10]`)

#### Implement

- [x] Keep `PropertyComparator.compare_properties()` contract stable, but now relies on `PropertyDiff.path_diffs` for semantics.
- [x] Remove dead comparator branches that depended on `PropertyType`.

Code snippet:

```python
class PropertyComparator:
    def compare_properties(
        self,
        old_props: dict[str, Property],
        new_props: dict[str, Property],
        excluded_properties: list[str],
    ) -> list[PropertyDiff]:
        property_diffs: list[PropertyDiff] = []
        all_prop_names = sorted(set(old_props.keys()) | set(new_props.keys()))

        for prop_name in all_prop_names:
            if prop_name in excluded_properties:
                continue
            property_diffs.append(
                PropertyDiff(
                    property_name=prop_name,
                    old_value=old_props.get(prop_name),
                    new_value=new_props.get(prop_name),
                )
            )

        return property_diffs
```

---

### Phase 4: Presenter builds nested sub-path tree (including unchanged)

#### Tests first

- [x] Update/add tests in `tests/unit/ui/presenters/test_diff_presenter_properties.py`:
  - [x] all path rows present, including unchanged
  - [x] expression row nested under path row (`Expression`)
  - [x] nested structure for dotted paths (`Base.x` -> `Base`/`x`)
  - [x] nested structure for indexed paths (`[0].Value` -> `[0]`/`Value`)
  - [x] nested structure for mixed named/indexed paths (`Constraints[0].Value` -> `Constraints`/`[0]`/`Value`)
  - [x] if any descendant changes, parent segment state becomes MODIFIED
  - [x] added property marks all descendants ADDED
  - [x] root `"."` row values are shown on the property top row when present
  - [x] when root `"."` value is missing and descendants exist, top row value is derived from descendant values in bracketed form
  - [x] presenter output ordering is deterministic (same path sort for all levels)

#### Implement

- [x] Refactor `_transform_property_diffs()` to consume `prop_diff.path_diffs`.
- [x] Create private presenter helpers to build path tree and aggregate synthetic node state.
- [x] Expression rows use `name="Expression"` and are nested under the path row they belong to.
- [x] Update presenter flow so `build_tree_from_path_diffs(...)` is called from `_transform_property_diffs()` and then converted via existing `PropertyPresentation` constructors.
- [x] Ensure top-level property row maps to path `"."` value when present; otherwise derive old/new summary values from children using FreeCAD-style bracketed string.
- [x] Ensure mixed-segment paths are tokenized into separate name/index segments (e.g. `Constraints[12].Value` -> `Constraints`, `[12]`, `Value`).
- [x] Convert path tree to `PropertyPresentation` with canonical ordering at every level via a single sort key helper.
- [x] Remove/replace legacy presenter branches that depended on `get_children()`-derived property child nodes; presenter input is now `prop_diff.path_diffs`.

Code snippet:

```python
# freecad/diff_wb/ui/presenters/diff_presenter.py
from dataclasses import dataclass, field


@dataclass
class _PathTreeNode:
    name: str
    state: DiffState = DiffState.UNCHANGED
    old_value: Any = None
    new_value: Any = None
    children: dict[str, "_PathTreeNode"] = field(default_factory=dict)


def _split_rel_path(path: str) -> list[str]:
    # Convert flattened path strings into hierarchical segments used by the presenter tree.
    #
    # Rules:
    # - "." means property-root (no extra segments).
    # - Dot separators split named segments ("Base.x" -> ["Base", "x"]).
    # - Bracket indices are standalone segments and preserve numeric identity
    #   ("Constraints[10].Value" -> ["Constraints", "[10]", "Value"]).
    #
    # Why this parser exists:
    # - A naive split('.') loses index structure.
    # - Treating "Constraints[0]" as one segment prevents desired nesting.
    if path == ".":
        return []
    if not path:
        return []
    tokens: list[str] = []
    segment_buf: list[str] = []
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if segment_buf:
                tokens.append("".join(segment_buf))
                segment_buf = []
            i += 1
            continue
        if ch == "[":
            if segment_buf:
                tokens.append("".join(segment_buf))
                segment_buf = []
            j = path.find("]", i)
            tokens.append(path[i : j + 1])
            i = j + 1
            continue
        segment_buf.append(ch)
        i += 1
    if segment_buf:
        tokens.append("".join(segment_buf))
    return tokens


def _aggregate_states(states: list[DiffState]) -> DiffState:
    changed = [s for s in states if s != DiffState.UNCHANGED]
    if not changed:
        return DiffState.UNCHANGED
    if all(s == DiffState.ADDED for s in changed):
        return DiffState.ADDED
    if all(s == DiffState.DELETED for s in changed):
        return DiffState.DELETED
    return DiffState.MODIFIED


def _insert_path_diff(root: _PathTreeNode, pd: PropertyPathDiff) -> None:
    segments = _split_rel_path(pd.path)
    node = root
    for seg in segments:
        node = node.children.setdefault(seg, _PathTreeNode(name=seg))

    # Leaf value row (show all rows, including unchanged)
    node.old_value = pd.old_value.value if pd.old_value is not None else None
    node.new_value = pd.new_value.value if pd.new_value is not None else None
    old_expr = pd.old_value.expression if pd.old_value is not None else None
    new_expr = pd.new_value.expression if pd.new_value is not None else None
    leaf_states = [pd.value_state]

    # Nested expression row under leaf, if expression exists on either side
    if old_expr is not None or new_expr is not None:
        expr_node = _PathTreeNode(
            name="Expression",
            state=pd.expression_state,
            old_value=old_expr,
            new_value=new_expr,
        )
        node.children["__expr__"] = expr_node
        leaf_states.append(pd.expression_state)

    node.state = _aggregate_states(leaf_states)


def _rollup_states(node: _PathTreeNode) -> DiffState:
    child_states = [_rollup_states(c) for c in node.children.values()]
    combined = _aggregate_states([node.state, *child_states])
    node.state = combined
    return combined


def _derive_container_summary(values: list[Any]) -> str | None:
    non_null = [str(v) for v in values if v is not None]
    if not non_null:
        return None
    return "[" + " ".join(non_null) + "]"


def _child_sort_key(name: str) -> tuple:
    # Reuse path segment ordering semantics: names first, then indices numerically.
    # This keeps [2] before [10] and prevents lexicographic jitter in UI ordering.
    if name.startswith("[") and name.endswith("]"):
        return (1, int(name[1:-1]))
    return (0, name)


def _path_tree_to_presentations(node: _PathTreeNode) -> list[PropertyPresentation]:
    # Deterministically convert internal tree nodes into UI presentation rows.
    #
    # Value policy:
    # - If a node has direct old/new values, show them.
    # - If it has no direct value but has children, derive FreeCAD-style bracket summary
    #   from child values for collapsed display (e.g. "[0.00 mm 0.00 mm 0.00 mm]").
    #
    # Child rows still carry full per-path detail when expanded.
    out: list[PropertyPresentation] = []
    for key in sorted(node.children.keys(), key=_child_sort_key):
        child = node.children[key]
        grandchildren = _path_tree_to_presentations(child)

        old_value = child.old_value
        new_value = child.new_value
        if old_value is None and new_value is None and grandchildren:
            # FreeCAD-like container summary when there is no direct value row for this segment.
            old_value = _derive_container_summary([gc.old_value for gc in grandchildren])
            new_value = _derive_container_summary([gc.new_value for gc in grandchildren])

        out.append(
            PropertyPresentation(
                name=child.name,
                state=child.state,
                old_value=old_value,
                new_value=new_value,
                children=grandchildren,
            )
        )
    return out
```

Presenter output shape for the requested example:

```python
PropertyPresentation(
    name="Placement",
    state=DiffState.MODIFIED,
    children=[
        PropertyPresentation(
            name="Base",
            state=DiffState.MODIFIED,
            children=[
                PropertyPresentation(
                    name="x",
                    state=DiffState.MODIFIED,
                    old_value=0.0,
                    new_value=5.0,
                    children=[
                        PropertyPresentation(
                            name="Expression",
                            state=DiffState.ADDED,
                            old_value=None,
                            new_value="Sketch.Constraints[0]",
                        )
                    ],
                )
            ],
        )
    ],
)
```

---

### Phase 5: View behavior for nested sub-paths and expansion rules

#### Tests first

- [x] Update/add `tests/unit/ui/views/test_show_properties.py`:
  - [x] nested rendering for `Placement -> Base -> x -> Expression`
  - [x] changed branches auto-expanded
  - [x] unchanged branches collapsed
  - [x] added property: all nested rows green
  - [x] parent rows reflect derived changed state from presenter
  - [x] container rows render bracketed summary values when presenter provides derived summary
  - [x] value columns never fall back to property name for container rows without scalar values
  - [x] branch/item ordering is stable for indexed segments (`[2]` before `[10]`)

#### Implement

- [x] Keep recursive rendering path in `_add_child_items()`.
- [x] Stop forcing every row expanded.
- [x] Update `_show_properties(...)` / property-tree population call sites to rely on presenter-provided nested `PropertyPresentation.children` (no ad-hoc child synthesis in view).
- [x] Expansion logic:
  - expanded if node or any descendant has non-UNCHANGED state
  - collapsed otherwise
- [x] Keep row color derived from `PropertyPresentation.state` (do not override to blue only due child existence).
- [x] Confirm `_create_property_tree_item()` and `_add_child_items()` both use the same expansion predicate to avoid inconsistent branch state.
- [x] Remove child-value fallback that injects `child.name` into value columns for ADDED/DELETED rows without scalar values.
- [x] Render presenter-provided container summary values exactly (including bracketed format), with expansion revealing per-child values.

Code snippet:

```python
# freecad/diff_wb/ui/views/diff_panel_view.py

def _presentation_has_changes(self, prop: PropertyPresentation) -> bool:
    if prop.state != DiffState.UNCHANGED:
        return True
    return any(self._presentation_has_changes(c) for c in prop.children)


def _create_property_tree_item(self, prop: PropertyPresentation) -> QTreeWidgetItem:
    bg_color, left_value, right_value = self._get_property_display_values(prop.state, prop)
    item = QTreeWidgetItem([_camelcase_to_spaces(prop.name), left_value, right_value])
    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

    self._add_child_items(item, prop.children)
    self._apply_background_to_all_columns(item, bg_color)

    # Expand changed branches; keep unchanged collapsed
    item.setExpanded(self._presentation_has_changes(prop))
    return item


def _add_child_items(self, parent_item: QTreeWidgetItem, children: list[PropertyPresentation]) -> None:
    for child in children:
        left_value, right_value = self._get_child_display_values(child)
        child_item = QTreeWidgetItem([_camelcase_to_spaces(child.name), left_value, right_value])
        child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsEditable)

        self._apply_child_background_by_state(child_item, child.state)
        self._add_child_items(child_item, child.children)

        # Expand changed branches; keep unchanged collapsed
        child_item.setExpanded(self._presentation_has_changes(child))
        parent_item.addChild(child_item)


def _get_child_display_values(self, child: PropertyPresentation) -> tuple[str, str]:
    # Intentionally show the same value in both columns for UNCHANGED rows.
    # This matches existing 3-column diff behavior where unchanged values are mirrored
    # left/right for quick comparison consistency.
    old_val = str(child.old_value) if child.old_value is not None else ""
    new_val = str(child.new_value) if child.new_value is not None else ""
    if child.state == DiffState.ADDED:
        return "", new_val
    if child.state == DiffState.DELETED:
        return old_val, ""
    if child.state == DiffState.MODIFIED:
        return old_val, new_val
    return new_val, new_val
```

---

### Phase 6: Test migration + legacy cleanup (no noise)

#### Tests first

- [x] Update focused tests only (avoid duplicating equivalent coverage):
  - `tests/unit/domain/diff/test_models.py`
  - `tests/unit/domain/diff/test_comparator.py`
  - `tests/unit/ui/presenters/test_diff_presenter_properties.py`
  - `tests/unit/ui/presenters/test_diff_presenter.py` (legacy child/ordering/expression expectations)
  - `tests/unit/ui/views/test_show_properties.py`
- [x] Convert repetitive state variants to `pytest.mark.parametrize` where possible.

#### Implement

- [x] Remove tests and helpers that validate deleted legacy behavior:
  - direct `PropertyType` branching
  - `get_children()`-driven property child diffs
  - flat `-> Expression` rows
  - path tokenization assumptions that keep `Constraints[0]` as a single non-hierarchical segment
  - value-column fallback to child/property name when no scalar value exists
- [x] Keep only long-term behavioral tests for:
  - nested paths,
  - deterministic path/segment ordering,
  - expression nesting,
  - root `"."` top-row mapping and container summary derivation,
  - parent-state rollup,
  - expansion behavior,
  - added/deleted subtree coloring.

Representative tests:

```python
def test_added_property_marks_all_nested_paths_added(presenter):
    # old missing, new has Placement.Base.x/y/z
    # assert Placement, Base, x/y/z rows are ADDED
    # assert all rows use green color in view tests
    ...


def test_expression_nested_under_path_row(presenter):
    # path Base.x has expression change
    # assert tree: Placement -> Base -> x -> Expression
    ...


def test_unchanged_path_rows_are_present_but_collapsed(panel):
    # include unchanged x and changed y under Base
    # assert x row exists but isCollapsed, y branch isExpanded
    ...
```

## Test Strategy

- **Unit tests:** primary verification for diff semantics and UI mapping.
- **Integration tests:** not required for this phase (pure code path; no FreeCAD runtime dependency).
- **Manual testing:** intentionally excluded from this plan per explicit user requirement.

## Findings & Notes

1. This plan intentionally treats path diffs as the canonical truth for value and expression changes.
2. Parent segment rollup state uses deterministic rules:
   - all changed descendants ADDED -> parent ADDED,
   - all changed descendants DELETED -> parent DELETED,
   - mixed changes -> parent MODIFIED,
   - no changed descendants -> parent UNCHANGED.
3. Added property semantics naturally satisfy "all sub-paths added" by computing all path diffs as ADDED when old property is missing.
4. Root-path handling in diff/presenter uses `"."` only; no empty-root fallback is planned.
5. Top-row display rule: use `"."` value when present; otherwise derive bracketed summary from child values to match FreeCAD-style collapsed container display.
6. Ordering is deterministic end-to-end: canonical path ordering in domain + canonical child ordering in presenter tree conversion.
7. Keep Python file/module responsibility headers up to date in any new or modified files.
