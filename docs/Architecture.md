# Architecture

History Workbench uses a layered architecture with domain-driven and ports-and-adapters patterns. The goal is to keep FreeCAD, Qt, git, and filesystem details at the edges while core CAD-history behavior remains understandable and testable.

## Design Principles

- Dependencies point inward where practical: entry points and UI call application actions; application actions coordinate domain services; infrastructure adapts external systems.
- Domain concepts are explicit: snapshots, diffs, settings, tree paths, and git state have dedicated models and services.
- Application actions are small desktop use cases. They coordinate dependencies and return result objects rather than directly updating Qt views or dialogs.
- UI state stays in the UI layer. The application container does not own presenter state or view state.
- External systems are represented through ports. Real FreeCAD, git, YAML, and filesystem implementations live in infrastructure; tests usually use fakes.
- FreeCAD startup work stays minimal. The workbench registers commands first, then creates the diff panel when activated or opened.

## Desktop Layer Model

History Workbench is a desktop FreeCAD workbench hosted inside another application. Use the project layer names when deciding where code belongs.

```text
FreeCAD command/workbench callback -> entry point -> presenter or application action
Qt widget event                    -> presenter   -> application action
Application action                 -> domain service/model -> infrastructure adapter
Infrastructure adapter             -> FreeCAD / git / filesystem / YAML
```

FreeCAD commands are entry points. They expose `GetResources()`, answer `IsActive()`, and translate `Activated()` callbacks into presenter or application calls. They are not presenters, although small command-specific dialogs may still live there until they are worth extracting into UI code.

UI code owns Qt widgets, presenters, dialog flow, display feedback, translated display text, and UI session state. Application actions own workbench use cases such as stage, commit, diff, save-before-diff, and open visual comparison. Domain owns CAD-history models, rules, and algorithms. Infrastructure owns concrete FreeCAD, git, filesystem, YAML, and FreeCAD preference calls.

FreeCAD document changes often update the visible desktop UI as a side effect. Visibility is not the layer boundary. Opening, saving, recomputing, staging, and creating comparison documents belong in application use cases when they are part of a workbench operation and are performed through ports.

## Runtime Flow

```text
FreeCAD loads init_gui.py
        |
        v
Workbench.Initialize()
        |
        |-- create FreeCAD runtime context
        |-- create ApplicationContainer
        |-- configure Log with FreeCADLogger
        |-- register FreeCAD commands
        |-- register preferences page
        v
Workbench.Activated() or Open Diff Window command
        |
        v
compose_and_register_ui(container)
        |
        |-- create UIState
        |-- create DiffPanelView
        |-- create presenters
        |-- register presenters in UIRegistry
        |-- detect active git repository
        v
Presenter executes application actions
        |
        v
Domain services and infrastructure adapters perform work
```

## Layer Responsibilities

### Entry Points

Location: `freecad/history_wb/entrypoints/`

Entry points integrate with FreeCAD's workbench and command APIs. They are driving adapters from the host desktop application into History Workbench.

- `workbench.py` defines `HistoryWorkbench`, registers toolbars/menus, creates the application container, registers preferences, and opens the diff panel.
- `commands.py` defines FreeCAD command classes and delegates work to presenters or application actions.
- Entry points may access the global container through `freecad/history_wb/_container.py`.
- Entry points should stay thin. They translate FreeCAD callbacks into application or UI calls.
- Command classes should not own domain rules or multi-step workflow logic when a presenter or application action can own it instead.

### UI Layer

Location: `freecad/history_wb/ui/`

The UI layer owns presenter state, Qt views, dialog flow, display feedback, and view protocols.

- `composer.py` is the UI composition root. It creates views, presenters, and `UIState`.
- `state.py` stores UI-only state such as the detected `GitRepository`.
- `registry.py` stores globally reachable UI objects needed by FreeCAD commands.
- `presenters/` transforms application results into view updates and presentation feedback.
- `protocols/` defines presenter-facing view contracts.
- `views/` contains Qt widgets and preferences UI.
- User-facing UI text is translated at display sites with literal `translate("History", "...")` calls, or defined with `QT_TRANSLATE_NOOP` when deferred.

Presenters depend on view protocols and application actions. Views render Qt widgets and perform translation. Presenters should pass raw data, not translated UI strings. Dialogs and message boxes are presentation concerns even when they are launched from FreeCAD command entry points.

### Application Layer

Location: `freecad/history_wb/application/`

The application layer exposes workbench use cases as small action classes. Actions coordinate desktop side effects through ports without owning Qt presentation behavior.

- `actions/` contains use cases such as creating snapshots, creating document diffs, staging documents, committing staged files, opening visual comparisons, reading settings, and finding repositories.
- `actions/result_models.py` contains reusable result types.
- `di/container.py` wires application actions, domain services, and infrastructure adapters.

Actions should be stateless after construction. They receive dependencies through constructors, execute one operation, and return a result. They may save FreeCAD documents, open comparison documents, write snapshot files, or stage git paths when those effects are part of the use case and are performed through ports or domain services.

### Domain Layer

Location: `freecad/history_wb/domain/`

The domain layer contains core CAD-history concepts, rules, models, algorithms, and contracts.

- `diff/` contains diff models, comparison algorithms, and `DiffEngine`.
- `git/` contains git models, git port protocols, and `GitService`.
- `settings/` contains settings models, text codec helpers, persistence state, and `SettingsRepository`.
- `snapshots/` contains snapshot models, snapshot serialization helpers, snapshot repository contracts, and `SnapshotExtractor`.
- `tree/` contains tree nodes, property models, and data-path wrappers.
- `config.py` contains default diff settings such as exclusions and float precision.
- `freecad_ports.py` defines minimal FreeCAD-facing protocols used by domain/application code.

Most domain code is pure Python. `domain/snapshots/gui_extractor.py` extracts FreeCAD's visual tree through `claimChildren()` using injected `GuiLike` from `FreeCadContext`, so domain services avoid direct `FreeCADGui` imports while still matching runtime GUI behavior. Concrete FreeCAD runtime imports and document mutation belong in infrastructure adapters.

### Infrastructure Layer

Location: `freecad/history_wb/infrastructure/`

Infrastructure adapts external systems to project protocols. It is still required even for systems central to the workbench, because FreeCAD runtime modules, git CLI, YAML libraries, and filesystem IO are concrete integration details.

- `freecad/ports.py` adapts the runtime FreeCAD API to `FreeCadPort` and `AppPort`.
- `freecad/freecad_visual_diff_creator.py` creates visual comparison documents through FreeCAD and Part APIs.
- `freecad/freecad_file_manager.py` materializes and extracts FreeCAD document revisions for visual diffing.
- `freecad/settings_repo.py` persists diff settings through FreeCAD preferences.
- `freecad/logger.py` sends `Log` output to the FreeCAD console.
- `git/git_port_adapter.py` implements git operations by calling the git CLI.
- `persistence/snapshot_yaml.py` writes snapshot YAML.
- `persistence/snapshot_yaml_deserializer.py` reads snapshot YAML.

Infrastructure can depend on domain and application types. Domain and application code should not depend on infrastructure implementations directly except where dependencies are wired in the container.

## Current Source Layout

```text
freecad/history_wb/
├── _container.py
├── init_gui.py
├── resources.py
├── utils.py
├── version.py
├── application/
│   ├── actions/
│   └── di/
├── domain/
│   ├── config.py
│   ├── freecad_ports.py
│   ├── diff/
│   ├── git/
│   ├── settings/
│   ├── snapshots/
│   └── tree/
├── entrypoints/
│   ├── commands.py
│   └── workbench.py
├── infrastructure/
│   ├── freecad/
│   ├── git/
│   └── persistence/
├── resources/
│   ├── icons/
│   ├── translations/
│   └── ui/
└── ui/
    ├── composer.py
    ├── registry.py
    ├── state.py
    ├── presenters/
    ├── protocols/
    └── views/
```

## Dependency Rules

```text
Entry Points
    |
    v
UI Layer --------------+
    |                  |
    v                  |
Application Layer      |
    |                  |
    v                  |
Domain Layer <---------+
    ^
    |
Infrastructure Layer
```

- Entry points may call UI registries, presenters, commands, and application container accessors.
- UI may call application actions and use domain models for display state.
- Application may use domain services, domain models, and domain ports.
- Application actions may coordinate desktop side effects through ports, but should not import Qt widgets or concrete FreeCAD/git/filesystem implementations.
- Domain should not import UI or application modules.
- Infrastructure implements ports and can call external APIs.
- The container is a composition mechanism, not application state.

## Placement Rules

Use these rules when deciding where code belongs:

| Code mentions or does | Layer |
| --- | --- |
| FreeCAD command registration, `Activated()`, `GetResources()`, workbench lifecycle | Entry point |
| Qt widget, dialog, message box, translated display text, view state | UI |
| Multi-step user operation such as stage, commit, diff, save before diff, open comparison | Application |
| Snapshot/diff/tree/settings/git rule that can be expressed without concrete runtime APIs | Domain |
| `FreeCAD`, `FreeCADGui`, `Part`, git CLI, YAML library, direct filesystem IO, zip extraction | Infrastructure |
| Concrete object creation and dependency wiring | Composition root/container |

Opening a FreeCAD document, saving a modified document, recomputing, or creating a comparison document can visibly change the desktop UI. The deciding factor is not visibility. The deciding factor is ownership: presentation code decides what the user sees and asks for; application code decides what the workbench operation does; infrastructure code performs concrete runtime calls.

## Composition Roots

History Workbench has two composition roots.

### Application Composition

`workbench.Initialize()` creates the FreeCAD runtime context and calls `create_application_container(ctx)`. The container wires:

- FreeCAD adapters
- git adapter and git service
- settings repository
- snapshot extractor
- diff engine
- application actions

The container is stored through `set_container()` so FreeCAD command instances can access it at execution time.

### UI Composition

`compose_and_register_ui(container)` creates:

- `UIState`
- `DiffPanelView`
- `DiffPresenter`
- `GitRepositoryPresenter`

It then registers UI objects in `ui_registry` for command access. UI composition happens when the diff panel is created, not during initial FreeCAD module import.

## UI Composition Rules

Composite Qt views may be split into focused child widgets, but presenter-facing APIs should remain stable through view protocols.

- Presenters call view protocols, not concrete child widgets.
- The UI composer wires presenters to top-level views only.
- Top-level views act as facades for composed child widgets.
- Child widgets do not import, instantiate, or call sibling child widgets.
- Child widgets expose callbacks/events upward and narrow setter methods downward.
- Cross-widget side effects are coordinated by the top-level facade.
- Cross-widget coordination is tested at the facade level.

Example: `DiffPanelView` composes `HistoryPanelWidget`, `DocumentDiffTreeWidget`, and `PropertyDiffTreeWidget`. Selecting history in `HistoryPanelWidget` should not directly mutate `DocumentDiffTreeWidget`; `DiffPanelView` or a presenter coordinates the behavior.

## Snapshot And Diff Pipeline

History Workbench stores textual snapshots next to `.FCStd` files so git can compare CAD model state.

```text
FreeCAD document
        |
        v
SnapshotExtractor
        |
        v
Snapshot model
        |
        |-- working tree snapshot from open document
        |-- commit snapshot from YAML deserializer
        v
DiffEngine
        |
        v
DiffResult
        |
        v
DiffPresenter
        |
        v
DiffPanelView
```

Snapshots contain normalized object payloads and occurrence paths. This allows repeated or linked objects to be represented separately from object data. Diff comparison uses settings for exclusions and numeric precision.

## Git Workflow Integration

Git support is implemented as domain service plus infrastructure adapter.

- `GitService` owns repository-level workflow rules.
- `GitPort` defines git operations.
- `GitPortAdapter` calls the git CLI.
- Application actions use `GitService` to find repositories, list commits, stage files, detect staged/committed paths, and commit staged changes.
- The UI stores the active `GitRepository` in `UIState` because repository selection is UI session state.

History Workbench supplements normal git clients. It focuses on CAD-specific staging, snapshot generation, and review.

## Settings And Preferences

Default settings live in `domain/config.py`. Runtime settings are read and written through `SettingsRepository`, implemented by `FreeCADSettingsRepository` with FreeCAD preferences.

Settings affect diff computation and display. They do not affect snapshot generation.

## Public APIs

Module `__init__.py` files define public module APIs with `__all__` where useful. Importing from package-level modules is preferred when a symbol is exported there.

```python
from freecad.history_wb.domain.diff import DiffEngine
from freecad.history_wb.domain.snapshots import Snapshot
from freecad.history_wb.domain.tree import Property
```

Direct file imports are acceptable when a symbol is not part of a package API or when tests need focused access to implementation details.

## Known Tradeoffs

- `SnapshotExtractor` uses injected `GuiLike` to access GUI documents and `claimChildren()` behavior. This keeps extraction aligned with FreeCAD's visual tree without domain-level `FreeCADGui` imports.
- `ApplicationContainer` exposes small `log()` and `translate()` helpers for entry points. Core code should prefer `Log` and view-level translation patterns.
- Some FreeCAD APIs are difficult to type precisely. Protocols in `domain/freecad_ports.py` intentionally model only the behavior History Workbench uses.

## Glossary

| Term | Meaning |
| --- | --- |
| Action | Application-layer use case object with an `execute()` method. |
| Adapter | Infrastructure implementation of a port, such as `GitPortAdapter`. |
| Application Container | Object that wires actions, services, repositories, and adapters. |
| Composition Root | Place where dependencies are created and connected. |
| Domain | Core model and behavior independent from presentation details. |
| Port | Protocol that describes an external dependency. |
| Presenter | UI coordinator that turns application results into view updates. |
| Snapshot | Text-friendly representation of a FreeCAD document's model state. |
| UIState | UI-session state owned by the UI layer, such as detected repository. |
