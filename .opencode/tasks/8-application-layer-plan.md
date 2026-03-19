# Task: Phase 7 - Application Layer (Actions and UI Presenters)

## Goal
Implement the application layer actions and UI presenters to connect the domain layer with FreeCAD commands, enabling snapshot creation and comparison workflows through toolbar buttons. This phase follows a clean MVP architecture with Actions in the application layer and Presenters in the UI layer.

## Context
Phase 7 implements the missing link between the existing domain layer (diff engine, snapshot extractor, repositories) and FreeCAD command entrypoints. The architecture follows:

- **FreeCAD Commands**: Entry point for user actions (toolbar/menu clicks)
- **Actions**: Orchestrate domain services for single use cases (command or query)
- **Presenters** (UI layer): Transform domain data into presentation models AND call view protocol methods
- **Views** (UI layer): Qt widgets that implement view protocols (Phase 8)

Current state:
- Domain layer is complete (snapshots, diff engine, tree models)
- Infrastructure adapters exist (FreeCadPort, GuiPort, SettingsRepository)
- Commands in `commands.py` are stubs with empty `Activated()` methods
- No UI components exist yet (Phase 8 will create these)

This phase focuses on **application logic** without implementing actual Qt widgets.

## Architecture Changes (From Previous Plan)

### Key Decisions
1. **Removed Controllers**: Simplified by using Actions instead (no MVC confusion)
2. **Moved Presenters to UI Layer**: Presenters are interface adapters, not core application logic
3. **Action Pattern**: All use cases (commands and queries) use `.execute()` method
4. **View Protocols in UI Layer**: Interface definitions live with presenters

### Architecture Flow

```
FreeCAD Command → Action → Presenter → View (Protocol)
       │              ↓         ↓           ↓
       │         Domain    Transforms   Renders UI
       │         Layer     Data +       (Qt widgets)
       │                   Calls View
       │                   Methods
       └── User clicks toolbar button
```

**Key Principle:** 
- **Actions** orchestrate domain logic and return results (or None for queries that update via presenter)
- **Presenters** transform domain data into presentation models, then call view protocol methods (e.g., `show_diff_tree()`) which trigger actual UI rendering
- **Actions are testable entry points** for both unit tests and domain integration tests

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| **Actions instead of Controllers** | Clearer naming (no MVC confusion), follows established action pattern | Keep "Controller" name (confusing with MVC) |
| **Action.execute() as entry point** | Consistent API across all actions, clear execution boundary | Different method names per action (inconsistent) |
| **Presenters in UI layer** | Presenters are interface adapters, not core application logic; follows Clean Architecture | Keep in application layer (violates dependency boundaries) |
| **View Protocols in UI layer** | Protocols belong with their implementations; UI owns its interfaces | Define in application layer (unusual, unnecessary indirection) |
| **Actions for both commands and queries** | Consistent pattern, CLI reuse for reads, testing consistency | Separate Query objects (more boilerplate, less consistent) |
| **Commands import from both layers** | Commands bridge FreeCAD entrypoints with app/UI logic | Put command wiring in DI container (too complex) |
| **Result objects for commands** | Explicit success/failure handling, CLI-friendly | Raise exceptions (less user-friendly) |
| **None return for query actions with presenter** | Presenter handles UI update, no need for result | Return result AND call presenter (redundant) |

## Architecture Impact

### New Directory Structure

```
freecad/diff_wb/
├── application/                    # Application layer (business logic)
│   ├── __init__.py                 # Module responsibility: Core business logic
│   └── actions/                    # Use case orchestration
│       ├── __init__.py             # Module responsibility: Action use cases
│       ├── commands/               # State-changing operations
│       │   ├── __init__.py
│       │   ├── take_snapshot.py    # TakeSnapshotAction
│       │   └── compare_snapshots.py # CompareSnapshotsAction
│       └── queries/                # Read-only operations
│           ├── __init__.py
│           ├── list_snapshots.py   # ListSnapshotsAction
│           └── get_snapshot.py     # GetSnapshotAction
├── ui/                             # UI layer (interface adapters + widgets)
│   ├── __init__.py                 # Module responsibility: User interface
│   ├── protocols/                  # View interfaces (Protocols)
│   │   ├── __init__.py             # Module responsibility: View protocols
│   │   ├── snapshot_view.py        # SnapshotView protocol
│   │   └── diff_view.py            # DiffView protocol
│   ├── presenters/                 # Interface adapters
│   │   ├── __init__.py             # Module responsibility: Data presentation
│   │   ├── snapshot_presenter.py   # Transform snapshot results
│   │   └── diff_presenter.py       # Transform diff results
│   └── views/                      # Qt widget implementations (Phase 8)
│       ├── __init__.py
│       └── qt_snapshot_view.py     # Qt implementation of SnapshotView
├── entrypoints/
│   ├── __init__.py
│   ├── commands.py                 # FreeCAD command wrappers
│   └── workbench.py                # Workbench definition
├── domain/                         # Domain layer (already complete)
│   ├── snapshots/                  # Snapshot models and repository
│   ├── diff/                       # Diff engine and models
│   ├── logging/                    # Logger protocol
│   └── settings/                   # Settings protocol
└── infrastructure/                 # Infrastructure adapters (already complete)
    ├── freecad/                    # FreeCAD port implementations
    └── gui/                        # GUI port implementations
```

### Modified Files
- `entrypoints/commands.py` - Implement `Activated()` methods to call actions and presenters
- `init_gui.py` - Call DI container registration function (thin wrapper)

### No Changes To
- Domain layer (already complete)
- Infrastructure adapters (already complete)

## FreeCAD Dependency
- [x] No FreeCAD required for actions/presenters (pure Python with dependency injection)
- [ ] FreeCAD required only for integration testing with real FreeCadPort/GuiPort

**Testing approach:**
- Unit tests with fakes/mocks for all action/presenter logic
- Domain integration tests with real domain services but fake ports
- Integration tests (Phase 10) verify end-to-end with real FreeCAD

## Implementation Plan

### Phase 1: View Protocols and Result Models

**Goal:** Define view interfaces and result models that actions/presenters will use

#### Step 1.1: Write Tests for Result Models
Test file: `tests/unit/application/actions/test_result_models.py`

**Test cases:**
1. `test_snapshot_result_success_fields` - Verify success result has all fields
2. `test_snapshot_result_error_fields` - Verify error result has all fields
3. `test_compare_result_success_fields` - Verify success result has all fields
4. `test_compare_result_error_fields` - Verify error result has all fields

*Note: These are dataclass tests, implementation is trivial but tests document expected structure*

#### Step 1.2: Implement Result Models
File: `application/actions/result_models.py`

**Create result dataclasses:**
```python
"""File responsibility: Action result models for commands and queries."""

from dataclasses import dataclass

from ...domain.diff.engine import DiffResult


@dataclass
class SnapshotResult:
    """Result of snapshot creation operation."""
    success: bool
    snapshot_id: str | None
    snapshot_name: str | None
    error_message: str | None


@dataclass
class CompareResult:
    """Result of comparison operation."""
    success: bool
    diff_result: DiffResult | None
    error_message: str | None


@dataclass
class SnapshotSummary:
    """Summary information for a snapshot (for listing)."""
    id: str
    name: str
    created_at: str
    node_count: int
```

#### Step 1.3: Write Tests for View Protocols
Test file: `tests/unit/ui/protocols/test_view_protocols.py`

**Test cases:**
1. `test_snapshot_view_protocol_methods` - Verify protocol defines required methods
2. `test_diff_view_protocol_methods` - Verify protocol defines required methods
3. `test_protocol_is_abstract` - Verify Protocol cannot be instantiated

*Note: Protocol tests verify interface contract exists*

#### Step 1.4: Define View Protocols
File: `ui/protocols/snapshot_view.py` and `ui/protocols/diff_view.py`

**Create SnapshotView Protocol:**
```python
"""File responsibility: Snapshot view interface definition."""

from typing import Protocol


class SnapshotView(Protocol):
    """Interface that any snapshot display component must implement.
    
    Implemented by QtSnapshotView in the UI views layer.
    """
    
    def show_success(self, message: str, snapshot_id: str) -> None: ...
    def show_error(self, message: str) -> None: ...
    def show_loading(self, message: str = "Creating snapshot...") -> None: ...
```

**Create DiffView Protocol:**
```python
"""File responsibility: Diff view interface definition."""

from typing import Protocol

from ...application.actions.presentation_models import NodePresentation


class DiffView(Protocol):
    """Interface that any diff display component must implement.
    
    Implemented by QtDiffPanelView in the UI views layer.
    """
    
    def show_loading(self) -> None: ...
    def show_diff_tree(self, nodes: list[NodePresentation]) -> None: ...
    def show_summary(self, added: int, deleted: int, modified: int) -> None: ...
    def show_error(self, message: str) -> None: ...
```

#### Step 1.5: Implement Presentation Models
File: `application/actions/presentation_models.py`

**Create presentation dataclasses:**
```python
"""File responsibility: UI-friendly presentation models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NodePresentation:
    """UI-friendly format for a tree node."""
    path: str
    type_id: str
    state: str  # "ADDED", "DELETED", "MODIFIED", "UNCHANGED"
    has_changes: bool


@dataclass(frozen=True)
class PropertyPresentation:
    """UI-friendly format for property differences."""
    name: str
    old_display: str      # Formatted string like "10.0 (via Sketch.X)"
    new_display: str      # Formatted string like "20.0"
    state: str            # "ADDED", "DELETED", "MODIFIED", "UNCHANGED"


@dataclass(frozen=True)
class SnapshotPresentation:
    """UI-friendly format for snapshot summary."""
    id: str
    name: str
    created_at: str
    node_count: int
```

---

### Phase 2: Take Snapshot Action

#### Step 2.1: Write Tests for TakeSnapshotAction
Test file: `tests/unit/application/actions/commands/test_take_snapshot_action.py`

**Test cases:**
1. `test_execute_success_creates_snapshot` - Happy path: creates snapshot, returns success
2. `test_execute_no_active_document` - Error: no active document available
3. `test_execute_extraction_failure` - Error: extractor raises exception
4. `test_execute_saves_to_repository` - Verifies snapshot is saved
5. `test_execute_generates_unique_id` - Each snapshot gets unique UUID
6. `test_execute_with_custom_name` - Uses provided name parameter
7. `test_execute_auto_generates_name` - Generates name from document name

**Dependencies to mock:**
- `FakeFreeCadPort` (returns doc or None)
- `SnapshotExtractor` (returns Snapshot or raises)
- `FakeSnapshotRepository` (returns snapshot ID)
- `FakeGuiPort` (captures messages)

#### Step 2.2: Implement TakeSnapshotAction
File: `application/actions/commands/take_snapshot.py`

**Responsibility:** Orchestrate snapshot creation workflow

**Public interface:**
```python
class TakeSnapshotAction:
    def __init__(
        self,
        freecad_port: FreeCadPort,
        extractor: SnapshotExtractor,
        snapshot_repo: SnapshotRepository,
        gui_port: GuiPort,
    ) -> None: ...
    
    def execute(self, name: str | None = None) -> SnapshotResult:
        """Create a snapshot of the active document.
        
        Args:
            name: Optional custom snapshot name. Auto-generated if not provided.
        
        Returns:
            SnapshotResult with success status and snapshot details.
        """
        ...
```

**Workflow:**
1. Get active document via `FreeCadPort`
2. If no document, return `SnapshotResult(success=False, error_message="...")`
3. Extract tree via `SnapshotExtractor`
4. Create Snapshot object
5. Save to `SnapshotRepository`, get snapshot ID
6. Log success via `Logger` (internal to extractor)
7. Return `SnapshotResult(success=True, snapshot_id=..., snapshot_name=...)`

---

### Phase 3: Compare Snapshots Action

#### Step 3.1: Write Tests for CompareSnapshotsAction
Test file: `tests/unit/application/actions/commands/test_compare_snapshots_action.py`

**Test cases:**
1. `test_execute_success_computes_diff` - Happy path: compares two snapshots
2. `test_execute_old_not_found` - Error: old snapshot ID doesn't exist
3. `test_execute_new_not_found` - Error: new snapshot ID doesn't exist
4. `test_execute_computes_diff` - Verifies DiffEngine is called
5. `test_execute_uses_settings` - Uses SettingsRepository for exclusions
6. `test_execute_logs_progress` - Logger receives progress messages

**Dependencies to mock:**
- `FakeSnapshotRepository` (returns snapshots or None)
- `FakeDiffEngine` (returns DiffResult)
- `FakeSettingsRepository` (returns excluded types/properties)
- `FakeLogger` (captures log messages)

#### Step 3.2: Implement CompareSnapshotsAction
File: `application/actions/commands/compare_snapshots.py`

**Responsibility:** Orchestrate comparison workflow

**Public interface:**
```python
class CompareSnapshotsAction:
    def __init__(
        self,
        snapshot_repo: SnapshotRepository,
        diff_engine: DiffEngine,
        settings_repo: SettingsRepository,
        logger: Logger,
    ) -> None: ...
    
    def execute(self, old_id: str, new_id: str) -> CompareResult:
        """Compare two snapshots.
        
        Args:
            old_id: ID of older snapshot to compare from
            new_id: ID of newer snapshot to compare to
        
        Returns:
            CompareResult with diff data or error message.
        """
        ...
```

**Workflow:**
1. Retrieve old snapshot via `SnapshotRepository`
2. If not found, return `CompareResult(success=False, error_message="...")`
3. Retrieve new snapshot via `SnapshotRepository`
4. If not found, return `CompareResult(success=False, error_message="...")`
5. Get settings via `SettingsRepository`
6. Compute diff via `DiffEngine`
7. Return `CompareResult(success=True, diff_result=diff_result)`

---

### Phase 4: List Snapshots Query Action

#### Step 4.1: Write Tests for ListSnapshotsAction
Test file: `tests/unit/application/actions/queries/test_list_snapshots_action.py`

**Test cases:**
1. `test_execute_returns_all_snapshots` - Returns list of all snapshots
2. `test_execute_empty_repository` - Returns empty list when no snapshots
3. `test_execute_formats_summaries` - Each item is SnapshotSummary

**Dependencies to mock:**
- `FakeSnapshotRepository` (returns list of snapshots)

#### Step 4.2: Implement ListSnapshotsAction
File: `application/actions/queries/list_snapshots.py`

**Responsibility:** Query all snapshots and return summaries

**Public interface:**
```python
class ListSnapshotsAction:
    def __init__(self, snapshot_repo: SnapshotRepository) -> None: ...
    
    def execute(self) -> list[SnapshotSummary]:
        """Return list of all snapshots.
        
        Returns:
            List of SnapshotSummary objects (read-only query).
        """
        ...
```

---

### Phase 5: Snapshot Presenter

#### Step 5.1: Write Tests for SnapshotPresenter
Test file: `tests/unit/ui/presenters/test_snapshot_presenter.py`

**Test cases:**
1. `test_present_result_success_calls_view` - Calls view.show_success()
2. `test_present_result_error_calls_view` - Calls view.show_error()
3. `test_formats_success_message_correctly` - Message includes snapshot name
4. `test_formats_error_message_correctly` - Error message passed through

**Dependencies to mock:**
- `FakeSnapshotView` (captures method calls for verification)

#### Step 5.2: Implement SnapshotPresenter
File: `ui/presenters/snapshot_presenter.py`

**Responsibility:** Transform `SnapshotResult` into view calls

**Public interface:**
```python
class SnapshotPresenter:
    def __init__(self, view: SnapshotView) -> None: ...
    
    def present_result(self, result: SnapshotResult) -> None:
        """Format result and tell view what to show.
        
        Args:
            result: SnapshotResult from TakeSnapshotAction.execute()
        """
        ...
```

**Implementation pattern:**
```python
def present_result(self, result: SnapshotResult) -> None:
    """Transform result into view calls."""
    if result.success:
        self._view.show_success(
            message=f"Snapshot '{result.snapshot_name}' created",
            snapshot_id=result.snapshot_id,
        )
    else:
        self._view.show_error(result.error_message or "Unknown error")
```

---

### Phase 6: Diff Presenter

#### Step 6.1: Write Tests for DiffPresenter
Test file: `tests/unit/ui/presenters/test_diff_presenter.py`

**Test cases:**
1. `test_present_diff_calls_view_methods` - Calls show_diff_tree, show_summary
2. `test_formats_node_diffs_correctly` - Transforms NodeDiff to NodePresentation
3. `test_formats_property_changes` - Formats PropertyDiff with expressions
4. `test_handles_empty_diff` - No changes case
5. `test_calculates_summary_counts` - Correct added/deleted/modified counts

**Dependencies to mock:**
- `FakeDiffView` (captures method calls for verification)

#### Step 6.2: Implement DiffPresenter
File: `ui/presenters/diff_presenter.py`

**Responsibility:** Transform `DiffResult` into presentation models AND call view methods

**Public interface:**
```python
class DiffPresenter:
    def __init__(self, view: DiffView) -> None: ...
    
    def present_diff(self, diff_result: DiffResult) -> None:
        """Transform domain data and call view methods to render UI.
        
        Args:
            diff_result: DiffResult from CompareSnapshotsAction.execute()
        """
        ...
```

**Implementation pattern:**
```python
def present_diff(self, diff_result: DiffResult) -> None:
    """Transform domain DiffResult into presentation models, then call view methods."""
    # Transform domain objects to presentation models
    nodes = [self._format_node(node) for node in diff_result.node_diffs]
    
    # Call view methods to trigger UI rendering
    self._view.show_diff_tree(nodes)
    self._view.show_summary(
        added=diff_result.summary.added_nodes,
        deleted=diff_result.summary.deleted_nodes,
        modified=diff_result.summary.modified_nodes,
    )

def _format_node(self, node_diff: NodeDiff) -> NodePresentation:
    """Transform domain NodeDiff to presentation model."""
    return NodePresentation(
        path=node_diff.path,
        type_id=node_diff.type_id,
        state=node_diff.state.name,
        has_changes=node_diff.has_changes,
    )
```

---

### Phase 7: Dependency Injection Container

#### Step 7.1: Write Tests for DI Container
Test file: `tests/unit/application/di/test_container.py`

**Test cases:**
1. `test_container_creates_all_actions` - All actions are instantiated
2. `test_container_creates_all_presenters` - All presenters are instantiated
3. `test_container_wires_dependencies_correctly` - Actions have correct deps
4. `test_container_injects_view_into_presenters` - Presenters receive views

**Note:** These tests verify container wiring without testing individual components

#### Step 7.2: Create DI Container Module
File: `application/di/container.py`

**Responsibility:** Wire all application layer dependencies together

**Structure:**
```python
"""File responsibility: Dependency injection container for application and UI layers.

This module wires actions, presenters, and views together.
It's the composition root for the application layer.
"""

from dataclasses import dataclass

from ...infrastructure.freecad.context import FreeCadContext
from ...infrastructure.freecad.context import get_port as get_freecad_port
from ...infrastructure.freecad.settings_repo import FreeCADSettingsRepository
from ...domain.snapshots.extractor import SnapshotExtractor
from ...domain.diff.engine import DiffEngine
from ...domain.logging.logger import FreeCADLogger

from ..actions.commands.take_snapshot import TakeSnapshotAction
from ..actions.commands.compare_snapshots import CompareSnapshotsAction
from ..actions.queries.list_snapshots import ListSnapshotsAction
from ...ui.presenters.snapshot_presenter import SnapshotPresenter
from ...ui.presenters.diff_presenter import DiffPresenter


@dataclass
class ApplicationContainer:
    """Holds all wired application layer components."""
    
    # Actions (application layer)
    take_snapshot_action: TakeSnapshotAction
    compare_snapshots_action: CompareSnapshotsAction
    list_snapshots_action: ListSnapshotsAction
    
    # Presenters (UI layer)
    snapshot_presenter: SnapshotPresenter
    diff_presenter: DiffPresenter
    
    # Optional UI components (Phase 8)
    # diff_panel_view: DiffPanelView | None = None


def create_application_container(
    ctx: FreeCadContext,
    snapshot_repo: InMemorySnapshotRepository,
    diff_view=None,  # Phase 8: Will be DiffPanelView instance
) -> ApplicationContainer:
    """Wire all application layer dependencies.
    
    Args:
        ctx: FreeCAD runtime context
        snapshot_repo: Snapshot repository (created in init_gui.py)
        diff_view: Optional view for diff display (Phase 8)
    
    Returns:
        ApplicationContainer with all wired components
    """
    # Get infrastructure adapters
    freecad_port = get_freecad_port(ctx)
    gui_port = get_gui_port(ctx)
    logger = FreeCADLogger()
    settings_repo = FreeCADSettingsRepository(ctx)
    
    # Create domain services
    extractor = SnapshotExtractor(logger=logger)
    diff_engine = DiffEngine(settings_repo=settings_repo)
    
    # Create actions (application layer - pure orchestration)
    take_snapshot_action = TakeSnapshotAction(
        freecad_port=freecad_port,
        extractor=extractor,
        snapshot_repo=snapshot_repo,
        gui_port=gui_port,
    )
    
    compare_snapshots_action = CompareSnapshotsAction(
        snapshot_repo=snapshot_repo,
        diff_engine=diff_engine,
        settings_repo=settings_repo,
        logger=logger,
    )
    
    list_snapshots_action = ListSnapshotsAction(snapshot_repo=snapshot_repo)
    
    # Create presenters (UI layer - interface adapters)
    # Note: For Phase 7, may use fake/None views until Phase 8
    from ...ui.protocols.snapshot_view import SnapshotView
    from ...ui.protocols.diff_view import DiffView
    
    snapshot_view: SnapshotView = None  # TODO: Phase 8 - create Qt view
    diff_view_impl: DiffView = diff_view  # TODO: Phase 8 - create Qt view
    
    snapshot_presenter = SnapshotPresenter(view=snapshot_view)
    diff_presenter = DiffPresenter(view=diff_view_impl) if diff_view_impl else None
    
    return ApplicationContainer(
        take_snapshot_action=take_snapshot_action,
        compare_snapshots_action=compare_snapshots_action,
        list_snapshots_action=list_snapshots_action,
        snapshot_presenter=snapshot_presenter,
        diff_presenter=diff_presenter,
    )
```

---

### Phase 8: Wire Commands to Actions and Presenters

#### Step 8.1: Write Tests for Commands
Test file: `tests/unit/entrypoints/test_commands.py`

**Test cases:**
1. `test_take_snapshot_command_calls_action_and_presenter` - Verifies flow
2. `test_compare_command_calls_action_and_presenter` - Verifies flow
3. `test_command_resources_correct` - Menu text, tooltips, icons

**Dependencies to mock:**
- `FakeApplicationContainer` (provides actions and presenters)

#### Step 8.2: Update `init_gui.py`
File: `init_gui.py` - Make it thin wrapper around DI container

**Implementation:**
```python
"""FreeCAD Diff Workbench GUI initialization."""

from .application.di.container import create_application_container
from .entrypoints.commands import register_commands
from .entrypoints.workbench import DiffWorkbench
from .freecad_version_check import check_python_and_freecad_version
from .infrastructure.freecad.context import get_runtime_context
from .domain.snapshots.repository import InMemorySnapshotRepository
from .resources import TRANSLATIONSSPATH

# Initialize FreeCAD language support
Gui.addLanguagePath(TRANSLATIONSPATH)
Gui.updateLocale()

# Check Python and FreeCAD version compatibility
check_python_and_freecad_version()

# Create runtime context for dependency injection
ctx = get_runtime_context()

# Create infrastructure adapters
snapshot_repo = InMemorySnapshotRepository()

# Create application layer container (wires all dependencies)
container = create_application_container(
    ctx=ctx,
    snapshot_repo=snapshot_repo,
    diff_view=None,  # Phase 8: Will be DiffPanelView()
)

# Register commands with wired actions and presenters
register_commands(container)

# Register workbench
Gui.addWorkbench(DiffWorkbench())
```

#### Step 8.3: Update `commands.py`
File: `entrypoints/commands.py` - Implement `Activated()` methods

**Structure:**
```python
"""File responsibility: FreeCAD command entry points for the Diff Workbench."""

import os

from ..infrastructure.freecad.app_port import get_app_port
from ..resources import ICONPATH
from ..application.di.container import ApplicationContainer


_translate = get_app_port().translate


class _TakeSnapshotCommand:
    """Command to take a new snapshot of the active document."""
    
    def __init__(self, action: TakeSnapshotAction, presenter: SnapshotPresenter):
        self._action = action
        self._presenter = presenter
    
    def GetResources(self) -> dict[str, str]:
        return {
            "MenuText": _translate("Workbench", "Take Snapshot"),
            "ToolTip": _translate("Workbench", "Create a snapshot of the current document"),
            "Pixmap": os.path.join(ICONPATH, "TakeSnapshot.svg"),
        }
    
    def IsActive(self) -> bool:
        return True
    
    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        result = self._action.execute()
        self._presenter.present_result(result)


class _CompareCommand:
    """Command to compare against a selected snapshot."""
    
    def __init__(
        self,
        action: CompareSnapshotsAction,
        presenter: DiffPresenter,
    ):
        self._action = action
        self._presenter = presenter
    
    def GetResources(self) -> dict[str, str]:
        return {
            "MenuText": _translate("Workbench", "Compare"),
            "ToolTip": _translate("Workbench", "Compare snapshots"),
            "Pixmap": os.path.join(ICONPATH, "Compare.svg"),
        }
    
    def IsActive(self) -> bool:
        return True
    
    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        # TODO: Phase 8 - Get snapshot IDs from UI selection
        old_id = self._get_selected_old_snapshot()
        new_id = self._get_selected_new_snapshot()
        
        result = self._action.execute(old_id, new_id)
        if result.success and self._presenter:
            self._presenter.present_diff(result.diff_result)
    
    def _get_selected_old_snapshot(self) -> str:
        """TODO: Phase 8 - Get from UI selection."""
        raise NotImplementedError("Phase 8")
    
    def _get_selected_new_snapshot(self) -> str:
        """TODO: Phase 8 - Get from UI selection."""
        raise NotImplementedError("Phase 8")


def register_commands(container: ApplicationContainer) -> None:
    """Register the Diff Workbench commands with FreeCAD.
    
    Args:
        container: Application container with wired actions and presenters
    """
    import FreeCADGui as Gui  # pylint: disable=import-error
    
    Gui.addCommand("DiffTakeSnapshot", _TakeSnapshotCommand(
        action=container.take_snapshot_action,
        presenter=container.snapshot_presenter,
    ))
    Gui.addCommand("DiffCompare", _CompareCommand(
        action=container.compare_snapshots_action,
        presenter=container.diff_presenter,
    ))
```

---

## Test Strategy

### Unit Tests (No FreeCAD Required)
**Location:** `tests/unit/`

| Test File | Coverage | Location | Dependencies |
|-----------|----------|----------|--------------|
| `test_result_models.py` | Result dataclasses | `unit/application/actions/` | None |
| `test_take_snapshot_action.py` | Snapshot creation workflow | `unit/application/actions/commands/` | FakeFreeCadPort, FakeSnapshotRepository |
| `test_compare_snapshots_action.py` | Comparison workflow | `unit/application/actions/commands/` | FakeSnapshotRepository, FakeDiffEngine |
| `test_list_snapshots_action.py` | Query all snapshots | `unit/application/actions/queries/` | FakeSnapshotRepository |
| `test_snapshot_presenter.py` | Success/error formatting | `unit/ui/presenters/` | Fake view |
| `test_diff_presenter.py` | Diff result formatting | `unit/ui/presenters/` | Fake view |
| `test_container.py` | Dependency wiring | `unit/application/di/` | Verifies all components wired correctly |
| `test_commands.py` | Command entry points | `unit/entrypoints/` | Fake container |

**Fake implementations needed:**
- `FakeFreeCadPort` in `tests/fakes/` - Returns mock document or None
- `FakeGuiPort` in `tests/fakes/` - Captures show_message calls
- `FakeSnapshotView` in `tests/fakes/` - Captures method calls
- `FakeDiffView` in `tests/fakes/` - Captures method calls
- Already have `FakeSnapshotRepository` and `FakeSettingsRepository`

### Domain Integration Tests (No FreeCAD, No Mocks)
**Location:** `tests/integration/application/actions/`

| Test File | Coverage | Description |
|-----------|----------|-------------|
| `test_take_snapshot_integration.py` | Real extractor + real repo | End-to-end snapshot creation with fake ports |
| `test_compare_snapshots_integration.py` | Real diff engine + real repo | End-to-end comparison with fake ports |

These tests use:
- ✅ Real domain services (SnapshotExtractor, DiffEngine)
- ✅ Real repository (InMemorySnapshotRepository)
- ❌ Fake infrastructure ports (no FreeCAD runtime needed)

### Full Integration Tests (With FreeCAD)
**Location:** `tests/integration/`

| Test File | Coverage | When |
|-----------|----------|------|
| `test_controller_integration.py` | End-to-end with real ports | Phase 10 (Testing & Polish) |

**Note:** Full integration tests are deferred to Phase 10 when the UI components exist.

---

## Findings & Notes

### Key Design Decisions

1. **Action Pattern**: All use cases use `.execute()` method for consistent API across commands and queries.

2. **Separation of Concerns**: 
   - **Commands**: Entry points, trigger action + presenter
   - **Actions**: Pure orchestration, return results (application layer)
   - **Presenters**: Transform data + call view methods (UI layer)
   - **Views**: Qt widgets implementing view protocols (UI layer)

3. **Error Handling**: Use result pattern (success/error + data) instead of exceptions for expected failures.

4. **UI Agnostic Presenters**: Presenters receive view via Protocol, not Qt objects. This enables unit testing without Qt.

5. **DI Container**: Complex wiring extracted to `application/di/container.py` keeps `init_gui.py` clean and maintainable.

6. **Actions as Test Entry Points**: Actions serve as both application entry points and integration test targets, enabling domain integration tests without FreeCAD.

7. **Clean Architecture Compliance**: Presenters moved to UI layer as interface adapters, respecting dependency boundaries.

### Architecture Flow Summary

```
User clicks "Take Snapshot" button
          │
          ▼
┌─────────────────────┐
│  _TakeSnapshotCommand│  ← FreeCAD command entry point
│  def Activated():    │
│      result = self._action.execute()
│      self._presenter.present_result(result)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ TakeSnapshotAction  │  ← Application layer orchestration
│                     │
│  def execute(name): │
│      doc = self.freecad_port.get_active_document()
│      snapshot = self.extractor.extract_tree(doc)
│      snapshot_id = self.repo.save(snapshot)
│      return SnapshotResult(success=True, ...)
└──────────┬──────────┘
           │
           ▼
     Result returned to command
           │
           ▼
┌─────────────────────┐
│ SnapshotPresenter   │  ← UI layer interface adapter
│                     │
│  def present_result(result):
│      if result.success:
│          self._view.show_success(...)  # ← Calls protocol method
│      else:
│          self._view.show_error(...)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   SnapshotView      │  ← Interface (Protocol, UI layer)
│   (Protocol)        │
└──────────┬──────────┘
           │ Runtime binding
           ▼
┌─────────────────────┐
│  QtSnapshotView     │  ← Qt widget implementation (Phase 8)
│  (QWidget)          │
│  def show_success(message, snapshot_id):
│      QMessageBox.information(..., message, snapshot_id)
└─────────────────────┘
```

### API Signatures

**TakeSnapshotAction:**
```python
class TakeSnapshotAction:
    def __init__(
        self,
        freecad_port: FreeCadPort,
        extractor: SnapshotExtractor,
        snapshot_repo: SnapshotRepository,
        gui_port: GuiPort,
    ) -> None: ...
    
    def execute(self, name: str | None = None) -> SnapshotResult:
        """Create a snapshot of the active document."""
        ...
```

**CompareSnapshotsAction:**
```python
class CompareSnapshotsAction:
    def __init__(
        self,
        snapshot_repo: SnapshotRepository,
        diff_engine: DiffEngine,
        settings_repo: SettingsRepository,
        logger: Logger,
    ) -> None: ...
    
    def execute(self, old_id: str, new_id: str) -> CompareResult:
        """Compare two snapshots."""
        ...
```

**DiffPresenter:**
```python
class DiffPresenter:
    def __init__(self, view: DiffView) -> None: ...
    
    def present_diff(self, diff_result: DiffResult) -> None:
        """Transform domain DiffResult into view calls."""
        ...
```

---

## Success Criteria

- [ ] TakeSnapshotAction creates snapshots and saves to repository
- [ ] CompareSnapshotsAction retrieves snapshots, computes diff, returns result
- [ ] ListSnapshotsAction queries all snapshots and returns summaries
- [ ] Presenters transform domain objects to presentation models AND call view methods
- [ ] Commands delegate to actions and presenters (implemented Activated() methods)
- [ ] DI container wires all dependencies correctly
- [ ] All unit tests pass without FreeCAD runtime
- [ ] Domain integration tests pass with fake ports but real domain services
- [ ] Linting passes (ruff, mypy, pylint)
- [ ] Actions are injectable and testable
- [ ] Presenters are in UI layer (clean architecture compliance)

---

## Notes

- This phase does NOT implement Qt widgets (Phase 8)
- Commands have minimal implementation until Phase 8 provides UI dialogs for snapshot selection
- Full integration testing deferred to Phase 10
- Actions serve as both application entry points and integration test targets
- Clean Architecture is respected: Application layer = business logic only, UI layer = interface adapters + widgets

---

## Review Comments Implementation Plan

The following additional tasks address review comments on the original plan:

### Comment 1: Timestamp Always in Snapshot Name

**Issue**: `_generate_default_name()` currently uses document name when available, which can lead to duplicate snapshot names.

**Decision**: Always include timestamp in generated name for uniqueness and traceability.

**Implementation Steps:**

- [x] **Step R1.1: Write Tests for Timestamp-in-Name Behavior**
  - Test file: `tests/unit/application/actions/commands/test_take_snapshot_action.py`
  - Added test cases:
    - `test_execute_auto_generates_name_with_timestamp` - Verifies timestamp is always included
    - `test_name_format_is_document_timestamp` - Format: `{doc_name}_{YYYYMMDD_HHMMSS}`
    - `test_name_uses_fallback_when_no_doc_name` - Uses "snapshot" when doc has no Name attribute

- [x] **Step R1.2: Update `_generate_default_name()` Implementation**
  - File: `application/actions/commands/take_snapshot.py`
  - Changed to always include timestamp in format `{document_name}_{timestamp}`
  - Removed UUID from name format
  - Uses "snapshot" as fallback when document has no Name attribute

#### Step R1.1: Write Tests for Timestamp-in-Name Behavior
Test file: `tests/unit/application/actions/commands/test_take_snapshot_action.py` (add to existing tests)

**New test cases:**
1. `test_execute_auto_generates_name_with_timestamp` - Verifies timestamp is always included
2. `test_name_format_is_document_timestamp` - Format: `{doc_name}_{YYYYMMDD_HHMMSS}`
3. `test_name_uses_fallback_when_no_doc_name` - Uses "snapshot" when doc has no Name attribute

**Example assertions:**
```python
def test_name_format_is_document_timestamp(self):
    """Verify name format includes document name and timestamp only."""
    # Arrange
    mock_doc = MagicMock()
    mock_doc.Name = "MyPart"
    self._freecad_port.get_active_document.return_value = mock_doc
    
    # Act
    result = self._action.execute()
    
    # Assert - format should be: MyPart_20240319_143022
    assert result.success is True
    assert result.snapshot_name is not None
    assert result.snapshot_name.startswith("MyPart_")
    # Verify timestamp pattern (8 digits _ 6 digits)
    parts = result.snapshot_name.split("_")
    assert len(parts) == 3  # doc_name + date + time
```

#### Step R1.2: Update `_generate_default_name()` Implementation
File: `application/actions/commands/take_snapshot.py`

**Change from:**
```python
def _generate_default_name(self, doc: object) -> str:
    """Generate a default name from document info."""
    try:
        doc_name = getattr(doc, "Name", None)
        if doc_name is not None:
            return cast(str, doc_name)
    except (AttributeError, TypeError):
        pass
    
    # Fallback to timestamp with UUID
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"snapshot_{timestamp}_{short_uuid}"
```

**Change to:**
```python
def _generate_default_name(self, doc: object) -> str:
    """Generate a default name with ALWAYS includes timestamp.
    
    Format: {document_name}_{timestamp}
    Example: "MyPart_20240319_143022"
    
    This ensures uniqueness and chronological ordering without verbose names.
    
    Args:
        doc: FreeCAD document object
        
    Returns:
        Generated snapshot name with timestamp
    """
    # Try to get document name for readability
    try:
        doc_name = getattr(doc, "Name", None)
        if doc_name is None or doc_name == "":
            doc_name = "snapshot"
    except (AttributeError, TypeError):
        doc_name = "snapshot"
    
    # Always include timestamp for uniqueness and traceability
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{doc_name}_{timestamp}"
```

---

### Comment 2: Move Presentation Models to UI Layer

**Issue**: `presentation_models.py` is currently in `application/actions/` but should be in UI layer as it contains UI-specific data transformations.

**Decision**: Move to `ui/presenters/presentation_models.py` to follow Clean Architecture.

**Implementation Steps:**

- [x] **Step R2.1: Create New File in UI Layer**
  - File: `ui/presenters/presentation_models.py`
  - Contains `NodePresentation`, `PropertyPresentation`, `SnapshotPresentation` dataclasses

- [x] **Step R2.2: Update Imports in UI Layer**
  - Updated `ui/protocols/diff_view.py` to import from `..presenters.presentation_models`
  - Updated `ui/presenters/diff_presenter.py` to import from `.presentation_models`

- [x] **Step R2.3: Delete Old File**
  - Deleted `application/actions/presentation_models.py` after migration complete

- [x] **Step R2.4: Write Tests for Presentation Models**
  - Test file: `tests/unit/ui/presenters/test_presentation_models.py`
  - Added tests:
    - `test_node_presentation_is_frozen` - Verify immutability
    - `test_property_presentation_fields` - Verify all fields present
    - `test_snapshot_presentation_fields` - Verify all fields present
    - `test_presentation_models_are_dataclasses` - Verify dataclass behavior

#### Step R2.1: Create New File in UI Layer
File: `ui/presenters/presentation_models.py`

**Content** (copy from current location):
```python
"""File responsibility: UI-friendly presentation models for diff display."""

from dataclasses import dataclass


__all__ = ["NodePresentation", "PropertyPresentation", "SnapshotPresentation"]


@dataclass(frozen=True)
class NodePresentation:
    """UI-friendly format for a tree node."""
    path: str
    type_id: str
    state: str  # "ADDED", "DELETED", "MODIFIED", "UNCHANGED"
    has_changes: bool


@dataclass(frozen=True)
class PropertyPresentation:
    """UI-friendly format for property differences."""
    name: str
    old_display: str      # Formatted string like "10.0 (via Sketch.X)"
    new_display: str      # Formatted string like "20.0"
    state: str            # "ADDED", "DELETED", "MODIFIED", "UNCHANGED"


@dataclass(frozen=True)
class SnapshotPresentation:
    """UI-friendly format for snapshot summary."""
    id: str
    name: str
    created_at: str
    node_count: int
```

#### Step R2.2: Update Imports in UI Layer
Files to update:
- `ui/protocols/diff_view.py` - Change import from `..presentation_models` to `..presenters.presentation_models`
- `ui/presenters/diff_presenter.py` - Change import from `..presentation_models` to `.presentation_models`

#### Step R2.3: Delete Old File
File: `application/actions/presentation_models.py` (DELETE after migration complete)

#### Step R2.4: Write Tests for Presentation Models
Test file: `tests/unit/ui/presenters/test_presentation_models.py`

**Test cases:**
1. `test_node_presentation_is_frozen` - Verify immutability
2. `test_property_presentation_fields` - Verify all fields present
3. `test_snapshot_presentation_fields` - Verify all fields present
4. `test_presentation_models_are_dataclasses` - Verify dataclass behavior

---

### Comment 3: Integration Tests Should Assert Output Content

**Issue**: Integration tests currently only check `success=True` and non-null results, not actual output content.

**Decision**: Add assertions for actual diff content in integration tests.

**Implementation Steps:**

- [x] **Step R3.1: Update Existing Integration Tests**
  - File: `tests/integration/application/actions/test_compare_snapshots_integration.py`
  - Added assertions for:
    - Node counts and states (ADDED, DELETED, MODIFIED)
    - Property changes with old/new values
    - Exclusion rules verification
    - Empty diff verification

- [x] **Step R3.2: Add New Integration Test Cases**
  - Added test cases:
    - `test_compare_snapshots_detects_deleted_node` - Verify DELETED state
    - `test_compare_snapshots_multiple_changes` - Multiple nodes with different states
    - `test_compare_snapshots_nested_children` - Changes in child nodes
    - `test_compare_snapshots_property_value_changes` - Numeric/string value differences

#### Step R3.1: Update Existing Integration Tests
File: `tests/integration/application/actions/test_compare_snapshots_integration.py`

**Add assertions to existing tests:**

For `test_compare_snapshots_with_existing_snapshots`:
```python
# Assert - add these checks
assert result.success is True
assert result.diff_result is not None
# Verify the diff detected the Label property change
assert len(result.diff_result.node_diffs) == 1
node_diff = result.diff_result.node_diffs[0]
assert node_diff.path == "/Part"
assert node_diff.state == DiffState.MODIFIED
# Verify property changes
assert len(node_diff.property_diffs) == 1
prop_diff = node_diff.property_diffs[0]
assert prop_diff.name == "Label"
assert prop_diff.state == DiffState.MODIFIED
```

For `test_compare_snapshots_empty_snapshots`:
```python
# Assert - verify empty diff
assert result.success is True
assert result.diff_result is not None
assert result.diff_result.node_diffs == []
assert result.diff_result.summary.added_nodes == 0
assert result.diff_result.summary.deleted_nodes == 0
assert result.diff_result.summary.modified_nodes == 0
```

For `test_compare_snapshots_with_exclusions`:
```python
# Assert - verify excluded nodes are NOT in diff
assert result.success is True
assert result.diff_result is not None
# Origin nodes should be excluded
for node_diff in result.diff_result.node_diffs:
    assert node_diff.type_id != "App::Origin"
```

For `test_compare_snapshots_detects_added_node`:
```python
# Assert - verify added node detection
assert result.success is True
assert result.diff_result is not None
# Find the NewPart node
new_part_diffs = [n for n in result.diff_result.node_diffs if n.path == "/NewPart"]
assert len(new_part_diffs) == 1
assert new_part_diffs[0].state == DiffState.ADDED
```

#### Step R3.2: Add New Integration Test Cases
Add these additional test cases to cover more scenarios:

1. `test_compare_snapshots_detects_deleted_node` - Verify DELETED state
2. `test_compare_snapshots_multiple_changes` - Multiple nodes with different states
3. `test_compare_snapshots_nested_children` - Changes in child nodes
4. `test_compare_snapshots_property_value_changes` - Numeric/string value differences

---

### Comment 4: Action Unit Tests vs Integration Tests Strategy

**Question**: Should actions have unit tests, or are integration tests sufficient?

**Decision**: Keep both with different focus areas (hybrid approach).

**Rationale:**
- **Unit tests** provide fast feedback for error handling paths and edge cases
- **Integration tests** verify real domain services work together correctly
- Both are valuable; they serve different purposes in the testing pyramid

**Implementation Steps:**

- [x] **Step R4.1: Document Testing Strategy**
  - Updated `docs/Architecture.md` with "Unit Tests vs Integration Tests" section
  - Documented focus areas, dependencies, and speed expectations for each test type

**Testing Strategy Update:**

| Test Type | Location | Focus | Dependencies | Speed |
|-----------|----------|-------|--------------|-------|
| **Unit Tests** | `tests/unit/application/actions/` | Error paths, validation, orchestration logic | Fakes/Mocks | Fast (<5ms/test) |
| **Integration Tests** | `tests/integration/application/actions/` | Happy path, real domain services, end-to-end flow | Real services + faked ports | Medium (~50ms/test) |

**Unit Test Focus Areas:**
- No active document error
- Snapshot not found errors  
- Extraction failures (exceptions)
- Repository save failures
- Input validation
- Edge cases (None values, empty inputs)

**Integration Test Focus Areas:**
- Successful snapshot creation workflow
- Successful comparison workflow
- Real diff engine algorithms
- Real extractor behavior
- Complex scenarios (multiple nodes, nested changes)

**Success Criteria Update:**
- [ ] Unit tests cover all error handling paths
- [ ] Integration tests verify happy path with real domain services
- [ ] Test coverage is comprehensive without significant redundancy
- [ ] Unit tests run in under 1 second total
- [ ] Integration tests run in under 5 seconds total

---

## Updated Success Criteria

- [ ] TakeSnapshotAction creates snapshots and saves to repository
- [ ] TakeSnapshotAction always generates names with timestamp format `{doc_name}_{timestamp}`
- [ ] CompareSnapshotsAction retrieves snapshots, computes diff, returns result
- [ ] ListSnapshotsAction queries all snapshots and returns summaries
- [ ] Presenters transform domain objects to presentation models AND call view methods
- [ ] Presentation models moved to `ui/presenters/presentation_models.py`
- [ ] Commands delegate to actions and presenters (implemented Activated() methods)
- [ ] DI container wires all dependencies correctly
- [ ] All unit tests pass without FreeCAD runtime
- [ ] Domain integration tests pass with fake ports but real domain services
- [ ] Integration tests assert actual output content (node counts, states, property changes)
- [ ] Linting passes (ruff, mypy, pylint)
- [ ] Actions are injectable and testable
- [ ] Presenters are in UI layer (clean architecture compliance)
- [ ] Hybrid testing strategy implemented (unit + integration tests with different focus)

---

## Documentation Updates

### Update Architecture.md

Add a new section to `docs/Architecture.md` under "Testing Strategy" documenting the unit vs integration test responsibilities:

**New Section:**

```markdown
### Unit Tests vs Integration Tests

**Unit Tests** (`tests/unit/`):
- Focus: Error handling paths, input validation, orchestration logic
- Dependencies: Fakes and mocks only
- Speed: Fast (< 1 second total)
- Examples: No document error, snapshot not found, extraction failures

**Integration Tests** (`tests/integration/application/actions/`):
- Focus: Happy path with real domain services, end-to-end workflows
- Dependencies: Real services (DiffEngine, SnapshotExtractor) + fake ports
- Speed: Medium (< 5 seconds total)
- Examples: Successful snapshot creation, complex diff scenarios, exclusion rules

**Principle**: Unit tests provide fast feedback for common errors; integration tests verify real services work together correctly.
```
