# Task: Complete Document-Level Diff Result Architecture

## Goal
Refactor diff orchestration so document/file-level status is decided in the application layer, snapshot comparison remains pure domain logic, and UI-only indicators are produced only in the presenter/view layer.

This supports distinguishing:

1. FCStd missing in old ref -> `NEW_FILE` -> UI shows `"New file"` / `"N"` badge.
2. FCStd exists but snapshot YAML missing -> `OLD_SNAPSHOT_MISSING` -> UI shows warning icon / tooltip.
3. Snapshot YAML exists but is invalid -> `INVALID_SNAPSHOT` -> document-level status can represent corrupted/unreadable snapshot state.

## Context
Work already done:

- `DiffResult.warnings` mostly removed/replaced.
- `DiffEngine` no longer inserts `"Old snapshot missing"`.
- Git file existence support added:
  - `GitPort.file_exists`
  - `GitService.file_exists`
  - `GitPortAdapter.file_exists`
  - `FakeGitPort.file_exists`
- `SnapshotLoadStatus`, `SnapshotLoadResult`, `DocumentDiffStatus`, `DocumentDiffResult` introduced.
- `DiffTreePresentation.indicators` introduced.
- View can render `DocumentStatusIndicator`.
- Tests were updated to pass before latest correction, but architecture remains incomplete.

Architectural correction needed:

- `DocumentDiffResult` must not contain UI fields.
- `DiffPresenter` should not orchestrate snapshot loading/diff classification directly.
- New application action should build `DocumentDiffResult`.
- Presenter should map `DocumentDiffResult.status` to `DiffTreePresentation.indicators`.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Keep `DiffResult` snapshot-only | Domain layer should compare snapshots only, not know git/file reasons | Keeping warnings in `DiffResult` rejected as mixing concerns |
| Put document result models in `result_models.py` for now | User requested this location | Separate module can happen later if models grow |
| Use `DocumentStatusIndicator` only in UI presentation layer | Indicators are rendering concerns | Putting indicators in app model rejected |
| Use application-level action for document diffs | Presenter should not contain git/snapshot classification logic | Presenter-side classification rejected as architecture leak |
| Add `INVALID_SNAPSHOT` status | Invalid YAML is neither missing document nor missing snapshot | Returning failure loses per-document status |

## Architecture Impact
Affected layers:

### Domain

- `domain/diff/*`
  - Keep `DiffResult` free of warnings.
  - `DiffEngine.compute_diff(None, new)` may compare snapshot against itself, but must not attach status/warnings.

### Domain Git Port

- `domain/git/ports.py`
- `domain/git/git_service.py`
- `infrastructure/git/git_port_adapter.py`
- `tests/fakes/fake_git_port.py`

Purpose: determine FCStd file existence at ref/index.

### Application

- `application/actions/result_models.py`
  - Owns `SnapshotLoadStatus`, `SnapshotLoadResult`, `DocumentDiffStatus`, `DocumentDiffResult`.
- `application/actions/create_document_snapshot_commit.py`
  - Returns typed snapshot load result.
  - Invalid YAML returns `INVALID_SNAPSHOT`.
- New action, likely:
  - `application/actions/create_document_diffs.py`

Public API proposal:

```python
class DocumentDiffMode(Enum):
    WORKING_TREE = auto()
    STAGING = auto()
    COMMIT = auto()


@dataclass(frozen=True)
class CreateDocumentDiffsRequest:
    mode: DocumentDiffMode
    repo: GitRepository
    commit_hash: str | None = None
    documents: list[DocumentLike] | None = None
```

```python
class CreateDocumentDiffsAction:
    def execute(self, request: CreateDocumentDiffsRequest) -> Result:
        ...
```

Application result:

```python
@dataclass(frozen=True)
class DocumentDiffResult:
    git_path: str
    status: DocumentDiffStatus
    snapshot_diff: DiffResult | None = None
```

No `indicators`. No `stage_button_enabled`.

### UI

- `DiffPresenter`
  - Calls application action.
  - Stores `snapshot_diff` by `git_path`.
  - Computes stage button enabled from presentation/UI state.
  - Maps app statuses to indicators.
- `DiffTreePresentation`
  - Owns `indicators: list[DocumentStatusIndicator]`.

## FreeCAD Dependency
- [x] No FreeCAD required (pure code)

Reason: pure application/domain/presenter refactor with fakes/mocks. No FreeCAD API exploration needed.

## Implementation Plan
**IMPORTANT:** For each phase, write test steps BEFORE implementation steps to follow TDD principles.

### Phase 1: Correct Current Model and Snapshot Loading
- [x] Write/update `tests/unit/application/actions/test_result_models.py`
  - `DocumentDiffResult` has only `git_path`, `status`, `snapshot_diff`.
  - `SnapshotLoadStatus.INVALID_SNAPSHOT` exists.
- [x] Write/update `tests/unit/application/actions/test_create_document_snapshot_commit.py`
  - YAML missing + FCStd missing -> `DOCUMENT_MISSING`
  - YAML missing + FCStd exists -> `SNAPSHOT_MISSING`
  - YAML invalid -> `INVALID_SNAPSHOT`
  - YAML valid -> `FOUND`
- [x] Implement model correction:
  - Remove UI fields from `DocumentDiffResult`.
  - Add `SnapshotLoadStatus.INVALID_SNAPSHOT`.
  - Change `CreateDocumentSnapshotForCommitAction` deserialization exception path:

```python
except Exception as e:
    Log.exception(...)
    return Result.success(
        SnapshotLoadResult(snapshot=None, status=SnapshotLoadStatus.INVALID_SNAPSHOT)
    )
```

- [x] Ensure no presenter/view imports application UI fields that no longer exist.

### Phase 2: Add Application-Level Document Diff Action
- [x] Write `tests/unit/application/actions/test_create_document_diffs.py`.
- [x] Cover commit mode:
  - Parent FCStd missing, commit snapshot found -> `NEW_FILE`
  - Parent FCStd exists, parent snapshot missing -> `OLD_SNAPSHOT_MISSING`
  - Parent snapshot invalid -> relevant invalid status or old snapshot missing decision
  - Both snapshots found -> `MODIFIED` / `UNCHANGED`
  - Commit snapshot missing/invalid -> document-level status with no `snapshot_diff`
- [x] Cover staging mode:
  - Index snapshot missing while staged FCStd exists -> snapshot missing status
  - HEAD FCStd missing -> `NEW_FILE`
  - HEAD FCStd exists but snapshot missing -> `OLD_SNAPSHOT_MISSING`
- [x] Cover working tree mode:
  - Current working snapshot vs index/HEAD snapshot as existing flow requires
  - Old FCStd missing -> `NEW_FILE`
  - Old snapshot missing -> `OLD_SNAPSHOT_MISSING`
- [x] Implement `application/actions/create_document_diffs.py`.
- [x] Add `DocumentDiffMode` and `CreateDocumentDiffsRequest` to `result_models.py` or the same action module.
- [x] Move orchestration out of `DiffPresenter` into this action:
  - Query paths
  - Load snapshots
  - Classify statuses
  - Call `CreateDiffAction`
  - Return `list[DocumentDiffResult]`

Public API:

```python
CreateDocumentDiffsAction.execute(...)
```

Private helpers:

```python
_compute_commit_diffs(...)
_compute_staged_diffs(...)
_compute_working_tree_diffs(...)
_classify_missing_old_snapshot(...)
```

### Phase 3: Refactor Presenter to Consume DocumentDiffResult
- [x] Update `tests/unit/ui/presenters/test_diff_presenter*.py` first.
- [x] Cover:
  - Presenter calls new action for commit/staging/working tree.
  - `DocumentDiffStatus.NEW_FILE` maps to `DocumentStatusIndicator(kind=BADGE, text="N", tooltip="New file")`.
  - `DocumentDiffStatus.OLD_SNAPSHOT_MISSING` maps to warning indicator.
  - Presenter stores only available `snapshot_diff` in `_diff_results_by_path`.
  - Stage button logic remains UI/presenter concern.
- [x] Inject `CreateDocumentDiffsAction` into `DiffPresenter`.
- [x] Remove presenter snapshot-loading classification helpers.
- [x] Keep presenter transformation responsibilities only:
  - `DocumentDiffResult` -> `DiffTreePresentation`
  - `DiffResult` -> node/property presentation models
  - UI state/stage button enablement

### Phase 4: DI, Composer, and Tests
- [x] Update container/composer tests first:
  - New action wired in `ApplicationContainer`.
  - Presenter receives new action.
- [x] Update fake protocol tests using `DiffTreePresentation.indicators`.
- [x] Add action to `ApplicationContainer`.
- [x] Pass action into `DiffPresenter` in `ui/composer.py`.
- [x] Remove obsolete dependencies from presenter constructor if no longer needed:
  - maybe `create_commit_snapshot_action`
  - maybe `create_diff_action`
  - maybe path query actions
  - depending on action boundary chosen

### Phase 5: Cleanup and Verification
- [x] Search and remove all remaining `warnings` / `WARNING_OLD_SNAPSHOT_MISSING` references.
- [x] Ensure all Python file responsibility comments remain accurate.
- [x] Run:
  - `uv run pytest tests/`
  - `uv run ruff format`
  - project-appropriate lint command if known
- [x] Report known unrelated failures separately, without changing unrelated files.

## Test Strategy
- **Unit tests**:
  - Application action tests verify classification and orchestration.
  - Presenter tests verify mapping only.
  - Domain diff tests verify no warnings/status.
  - Git service/adapter tests verify file existence.
- **Integration tests**:
  - No FreeCAD integration needed for this architecture refactor.
  - Existing integration tests can run as regression if desired.

## Findings & Notes
- Architecture now aligned with plan:
  - `CreateDocumentDiffsAction` owns document-level orchestration and status classification.
  - `DocumentDiffResult` remains application model without UI fields.
  - `DiffPresenter` maps `DocumentDiffStatus` to `DiffTreePresentation.indicators` and keeps UI state concerns.
- `INVALID_SNAPSHOT` represented as success status data so multi-document diff can continue even with one invalid snapshot.
- UI indicators remain presentational concerns in `DiffTreePresentation`/view layer.

## Final Verification
- [x] All phase checklist items completed.
- [x] Documentation reflects final architecture and layering boundaries.
- [x] Key decisions and rationale documented.
- [x] No remaining open items in this task.
