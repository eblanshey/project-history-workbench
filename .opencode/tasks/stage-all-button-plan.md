# Task: Stage All Button in Working Tree View

## Goal
Add a "Stage All" button to the Working Tree history view that stages all dirty FCStd documents and their snapshot YAML files at once, using the existing `StageDocumentsAction`.

## Context
When Working Tree is selected in the history list, the diff panel shows each eligible document with a "+ Stage" button. Users currently have to click each button individually. A "Stage All" button above the tree widget consolidates this into one action.

No new action, toolbar command, or icon is needed — the `DiffPresenter` already has `StageDocumentsAction` injected. This is purely a UI addition.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use existing `StageDocumentsAction` | Already wired into `DiffPresenter`, handles saving docs, persisting YAML, and staging | Created a new `StageAllDirtyAction` — rejected as unnecessary duplication |
| Button in summary bar (above tree) | Natural placement next to Added/Deleted/Modified labels; visible only during Working Tree selection | Toolbar command — rejected as overkill for a UI-only feature |
| No new SVG icon | Uses plain text button matching the style of individual "+ Stage" buttons | New icon — rejected as unnecessary |
| Feedback via `Log` | Consistent with existing single-stage flow; no toast/notification system exists | QMessageBox — rejected as too intrusive for a common operation |

## Architecture Impact

**Modified files:**
- `freecad/diff_wb/ui/views/diff_panel_view.py` — add stage-all button to summary container
- `freecad/diff_wb/ui/presenters/diff_presenter.py` — wire button visibility and click handler
- `freecad/diff_wb/ui/translation_strings.py` — add `STAGE_ALL_LABEL`

**No changes to:**
- `application/` layer (actions, container) — no new action needed
- `entrypoints/` layer (commands, workbench) — no toolbar command
- `domain/` layer — no domain model changes
- `infrastructure/` layer — no git adapter changes

## FreeCAD Dependency
- [x] No FreeCAD required (pure code)

## Implementation Plan

### Phase 1: View — Add Stage All Button

**File: `freecad/diff_wb/ui/views/diff_panel_view.py`**

1. In `_setup_ui()`, the summary container is a `QHBoxLayout` above the tree widget. Add a "Stage All" QPushButton to it.

```python
# In _setup_ui(), after creating summary_container and adding labels:
self._stage_all_button = QPushButton()
self._stage_all_button.setText("Stage All")
self._stage_all_button.setFixedWidth(70)
self._stage_all_button.hide()  # Hidden by default
summary_layout.addWidget(self._stage_all_button)
self._stage_all_button.clicked.connect(self._on_stage_all_clicked)
```

2. Add public API methods for the presenter to control the button:

```python
def set_stage_all_button_visible(self, visible: bool) -> None:
    """Show or hide the Stage All button."""
    self._stage_all_button.setVisible(visible)

def set_stage_all_button_enabled(self, enabled: bool) -> None:
    """Enable or disable the Stage All button."""
    self._stage_all_button.setEnabled(enabled)

def _on_stage_all_clicked(self) -> None:
    """Handle Stage All button click by invoking the callback."""
    if self._on_stage_all_callback:
        self._on_stage_all_callback()

def set_stage_all_callback(self, callback: Callable[[], None]) -> None:
    """Set the callback for Stage All button.

    Args:
        callback: A no-argument callable to invoke on click.
    """
    self._on_stage_all_callback = callback
```

### Phase 2: Presenter — Wire Visibility and Click Handler

**File: `freecad/diff_wb/ui/presenters/diff_presenter.py`**

1. In `present_diffs()`, after building presentations, control the button:

```python
def present_diffs(self, diff_results, dirty_paths=None, missing_snapshot_paths=None):
    # ... existing logic ...

    self._view.show_doc_diffs(presentations)

    # Stage All button: only visible during Working Tree selection
    is_working_tree = (
            self._view._current_selection is not None
            and self._view._current_selection.item_kind == "WORKING_TREE"
    )
    if is_working_tree:
        # Enable if any presentation has stage_button_enabled
        any_staggable = any(p.stage_button_enabled for p in presentations)
        self._view.set_stage_all_button_visible(True)
        self._view.set_stage_all_button_enabled(any_staggable)
    else:
        self._view.set_stage_all_button_visible(False)
```

2. Wire the callback in `__init__`:

```python
# In __init__, after self._view.set_history_selection_callback(...):
self._view.set_stage_all_callback(self.on_stage_all_clicked)
```

3. Implement `on_stage_all_clicked()`:

```python
def on_stage_all_clicked(self) -> None:
    """Handle 'Stage All' button click.

    Collects all working tree snapshots from _diff_results_by_path,
    stages them via StageDocumentsAction, then refreshes the view.
    """
    repo = self._ui_state.git_repository
    if repo is None:
        Log.warning("No git repository detected")
        return

    # Collect all snapshots from current diff results
    snapshots = [
        result.new_snapshot
        for result in self._diff_results_by_path.values()
        if result.new_snapshot is not None
    ]

    if not snapshots:
        Log.warning("No documents to stage")
        return

    # Stage all documents
    result = self._stage_documents.execute(repo, snapshots)
    if not result.is_success:
        Log.warning(f"Failed to stage documents: {result.message}")
        return

    Log.info(f"Successfully staged {len(snapshots)} documents")

    # Refresh the working tree view to reflect staged state
    self._on_working_tree_selected()
```

### Phase 3: Translation String

**File: `freecad/diff_wb/ui/translation_strings.py`**

Add to the COMMON STRINGS section:

```python
STAGE_ALL_LABEL = "Stage All"
"""Label for the Stage All button in the Working Tree view.

No placeholders. This is a static label displayed above the diff tree.
"""
```

Update `__all__` to include `"STAGE_ALL_LABEL"`.

### Phase 4: View — Use Translation String

**File: `freecad/diff_wb/ui/views/diff_panel_view.py`**

In `_setup_ui()`, use the translation string instead of hardcoded text:

```python
from ..translation_strings import STAGE_ALL_LABEL

# In _setup_ui():
stage_all_text = QCoreApplication.translate("DiffView", STAGE_ALL_LABEL)
self._stage_all_button.setText(stage_all_text)
```

## Test Strategy

- **Unit tests**: Test `DiffPresenter.on_stage_all_clicked()` with mocked repo, diff_results_by_path, and stage_documents_action — verify `execute()` is called with all collected snapshots
- **Unit tests**: Test `present_diffs()` button visibility logic — visible/enabled only during WORKING_TREE selection with staggable docs
- **No integration tests needed** — this is a UI-only change that exercises existing, well-tested domain logic

## Findings & Notes

- The `DiffPresenter` already has `self._stage_documents` (StageDocumentsAction) injected — no container changes needed
- `self._diff_results_by_path` is already populated during `_on_working_tree_selected()` — no additional queries needed
- The existing `on_add_button_clicked()` flow calls `self._stage_documents.execute(repo, [working_snapshot])` for a single doc — the Stage All flow is the same but with a list of all snapshots
- After "Stage All" succeeds, calling `self._on_working_tree_selected()` re-queries dirty state and refreshes the view, which will disable individual "+ Stage" buttons for staged documents
