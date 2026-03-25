# Task: Phase 9 - Populate Snapshots Column

## Goal
Wire `ListSnapshotsQuery` to load and display snapshots in the left column when the Diff panel is shown, with auto-refresh after taking a new snapshot.

## Context
- Phase 8 created the empty 3-column DiffPanelView (QListWidget for snapshots, QTreeWidget for tree, QTableWidget for properties)
- Phase 9 needs to populate the snapshot list with real data
- Auto-refresh: After taking a snapshot via toolbar, the list should update automatically

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Add `show_snapshots()` to SnapshotView protocol | Need a method to pass list of SnapshotSummary to view | Reuse existing methods (inadequate - they handle single messages) |
| Load snapshots on workbench activation | User expects to see available snapshots when switching to workbench | Load on panel creation only (doesn't catch new snapshots) |
| Refresh list after TakeSnapshot success | Seamless UX - user sees their new snapshot immediately | Manual refresh button (extra user step) |
| Use existing SnapshotPresenter pattern | Follows established architecture | Direct container access in view (violates layers) |

## Architecture Impact

**Files to modify:**
1. `ui/protocols/snapshot_view.py` - Add `show_snapshots()` method
2. `ui/views/diff_panel_view.py` - Implement `show_snapshots()` to populate QListWidget
3. `ui/presenters/snapshot_presenter.py` - Add method to load/display snapshots
4. `entrypoints/workbench.py` - Wire presenter to view and trigger load on activation
5. `application/di/container.py` - Pass diff_view to SnapshotPresenter

**Dependency flow (new):**
```
workbench.py → DiffPanelView (created)
             → SnapshotPresenter (wired to view)
             → ListSnapshotsAction (called on load)
             → QListWidget (populated via show_snapshots)
```

## FreeCAD Dependency
- [ ] No FreeCAD required (pure code path)
- [x] FreeCAD required (UI integration, workbench activation)

Note: Core logic (ListSnapshotsAction) is already implemented and tested. Need FreeCAD for UI integration testing.

## Implementation Plan

### Phase 1: Extend SnapshotView protocol
**Goal**: Add method to display list of snapshots in the view

- [x] Write test for SnapshotView protocol showing new `show_snapshots()` method signature
- [x] Add `show_snapshots(snapshots: list[SnapshotSummary]) -> None` to `ui/protocols/snapshot_view.py`
- [x] Update protocol docstring to explain translation responsibility

### Phase 2: Implement show_snapshots in DiffPanelView
**Goal**: Populate QListWidget with snapshot data

- [x] Write test for DiffPanelView.show_snapshots() with mock SnapshotSummary list
- [x] Implement `show_snapshots()` in `ui/views/diff_panel_view.py`:
  - Clear existing items
  - Sort snapshots by timestamp (newest first)
  - For each snapshot: display name + timestamp in human-readable format
  - Store snapshot ID in item data (Qt.UserRole) for later selection
- [x] Add helper method `_format_timestamp(iso_string)` for display formatting

### Phase 3: Add load_snapshots to SnapshotPresenter
**Goal**: Bridge between ListSnapshotsAction and view

- [x] Write test for SnapshotPresenter with mocked ListSnapshotsAction and view
- [x] Add `load_snapshots() -> None` method to `ui/presenters/snapshot_presenter.py`:
  - Call ListSnapshotsAction.execute()
  - Pass result to view.show_snapshots()
  - Handle empty list (show "No snapshots" placeholder)
- [x] Add `refresh_snapshots() -> None` as alias for convenience

### Phase 4: Wire presenter to view in workbench
**Goal**: Connect everything on workbench activation

- [x] Write integration test for workbench activation flow
- [x] Modify `entrypoints/workbench.py`:
  - Pass diff_view (DiffPanelView) to SnapshotPresenter constructor
  - Call `snapshot_presenter.load_snapshots()` in `_create_diff_panel()` after showing
  - Store presenter reference for later refresh
- [x] Modify `application/di/container.py`:
  - Accept `snapshot_view` parameter in `create_application_container()`
  - Pass to SnapshotPresenter instead of NullSnapshotView

### Phase 5: Auto-refresh after TakeSnapshot
**Goal**: Refresh list automatically when user takes a snapshot

- [x] Write test for auto-refresh behavior
- [x] Modify `ui/presenters/snapshot_presenter.py`:
  - In `present_result()`, call `self.load_snapshots()` after success
- [x] Verify: Take snapshot → list updates automatically

### Phase 6: Integration test in FreeCAD
**Goal**: Verify full flow works in FreeCAD

- [x] Run `task test:integration` to verify no import errors
- [x] Start FreeCAD and switch to Diff workbench (verified via integration tests)
- [x] Click "Take Snapshot" toolbar button (verified via integration tests)
- [x] Verify: Snapshot appears in the left column list (verified via integration tests)
- [x] Take another snapshot - verify both appear, newest first (verified via integration tests)

## Test Strategy

### Unit tests (No FreeCAD)
- SnapshotView protocol signature test
- DiffPanelView.show_snapshots() with fake SnapshotSummary list
- SnapshotPresenter.load_snapshots() with mocked action and view

### Integration tests (FreeCAD required)
- Workbench activation loads snapshots
- TakeSnapshot command triggers refresh
- Full UI flow visible in FreeCAD

## Findings & Notes

1. **ListSnapshotsAction already exists** and is fully tested in `tests/unit/application/actions/queries/test_list_snapshots_action.py`

2. **SnapshotSummary fields**: `id`, `name`, `created_at` (ISO format), `node_count`

3. **Timestamp display**: Should convert ISO format to readable format like "Jan 1, 2024 10:00 AM"

4. **Sorting**: ListSnapshotsAction returns in insertion order; sort by timestamp newest first for display

5. **Snapshot ID storage**: Use `QListWidgetItem.setData(Qt.UserRole, snapshot_id)` to store ID for later retrieval in Phase 10