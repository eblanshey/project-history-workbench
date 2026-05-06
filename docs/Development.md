# Development Guidelines

This guide describes how to make maintainable changes to DiffCAD. For environment setup, see [Development Setup](DevSetup.md). For system structure, see [Architecture](Architecture.md).

## Required Checks

Run code quality checks before submitting changes:

```bash
task check
```

Run unit tests:

```bash
task test
```

Run integration tests when behavior touches FreeCAD, git workflows, snapshots, preferences, or workbench activation:

```bash
task test:integration
```

Integration tests use FreeCAD's Python runtime through `./run_integration_tests.sh`. Do not use plain `pytest tests/integration` unless you are deliberately debugging collection behavior outside FreeCAD.

## Project Layout

```text
freecad/diff_wb/
├── application/       # Use cases and dependency injection container
├── domain/            # Core models, services, settings, ports, snapshot and diff logic
├── entrypoints/       # FreeCAD workbench and command integration
├── infrastructure/    # FreeCAD, git, and persistence adapters
├── resources/         # Icons, translations, UI resources
└── ui/                # Qt views, presenters, UI state, protocols, translation strings

tests/
├── unit/              # Fast tests using fakes and pure Python behavior
├── integration/       # FreeCAD runtime tests
├── fakes/             # Test doubles for ports, views, loggers, and repositories
└── freecad/           # Test FreeCAD documents
```

Keep tests close to the source structure they cover. For example, behavior in `freecad/diff_wb/domain/diff/engine.py` belongs under `tests/unit/domain/diff/` unless it needs the FreeCAD runtime.

## Coding Standards

- Keep changes minimal and focused.
- Prefer readable functions and direct data flow over new abstractions.
- Do not add compatibility layers unless there is a real persisted-data, shipped-API, or external-consumer need.
- Do not add comments that describe old bugs or temporary phases.
- Add comments only when code would otherwise be hard to understand.
- Use ASCII in new text unless the file already uses non-ASCII or the content needs it.
- Keep user-facing English strings in `freecad/diff_wb/ui/translation_strings.py`.
- Logs do not require translation.

Every Python file must start with a responsibility comment:

```python
# File responsibility: Explains what this file owns.
```

Every package `__init__.py` must start with a module responsibility comment:

```python
# Module responsibility: Explains what this package exposes or coordinates.
```

Keep those comments accurate when files change.

## Dependency Injection

Create dependencies at composition roots and pass them into classes or actions. Do not create FreeCAD, git, filesystem, or UI dependencies deep inside domain or application logic.

Preferred pattern:

```python
class CreateDiffAction:
    def __init__(self, diff_engine: DiffEngine) -> None:
        self._diff_engine = diff_engine

    def execute(self, old_snapshot: Snapshot, new_snapshot: Snapshot) -> Result[DiffResult]:
        diff = self._diff_engine.compute_diff(old_snapshot, new_snapshot)
        return Result.success(diff)
```

Guidelines:

- Application actions receive services and ports in constructors.
- Domain services receive protocols or value objects, not concrete infrastructure classes.
- UI presenters receive actions, view protocols, and UI state.
- Infrastructure adapters wrap external APIs.
- `ApplicationContainer` wires application actions and domain services.
- `compose_and_register_ui()` wires views, presenters, and `UIState`.

## Classes And Functions

Use classes when identity, state, interface contracts, or dependency injection make behavior clearer.

Good class use cases:

- Domain models and dataclasses: `Snapshot`, `TreeNode`, `Property`, `DiffResult`.
- Protocols and interfaces: `GitPort`, `SettingsRepository`, `FreeCadPort`.
- Services with injected dependencies: `DiffEngine`, `GitService`.
- Stateful infrastructure adapters: `GitPortAdapter`, `FreeCADSettingsRepository`.
- UI presenters and views.

Use functions for stateless, deterministic behavior.

Good function use cases:

- Pure transformations.
- Small comparison helpers.
- Serialization helpers.
- Test data builders.
- Local helpers that do not need injected dependencies.

Do not wrap a simple pure algorithm in a class only to make it look architectural.

## Imports And Public APIs

Prefer package-level imports when symbols are exported by `__init__.py`:

```python
from freecad.diff_wb.domain.diff import DiffEngine
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.domain.tree import Property
```

Direct module imports are fine when a symbol is intentionally not re-exported:

```python
from freecad.diff_wb.infrastructure.git.git_port_adapter import GitPortAdapter
```

Use `__all__` for clear module APIs when a package or module exposes a stable set of public symbols. Internal helpers should use a leading underscore.

## Logging

Use `Log` from `freecad.diff_wb.utils` for project logging:

```python
from freecad.diff_wb.utils import Log

Log.info("Repository refreshed")
Log.warning("No active document")
Log.error("Snapshot could not be loaded")
```

Behavior:

- Before FreeCAD initialization, logging falls back to stdout/stderr.
- After workbench initialization, logs go through `FreeCADLogger` to the FreeCAD console.
- Tests can install `FakeLogger` with `set_logger()`.
- Log messages are developer-facing and do not need translation.

## Translations

All user-facing English UI text belongs in `freecad/diff_wb/ui/translation_strings.py`.

Pattern:

- Define a named constant in `translation_strings.py`.
- Export it through `__all__`.
- Translate in views or entry point UI code with the appropriate Qt context.
- Use Qt-style placeholders such as `%1` and `%2` in templates.
- Presenters should pass raw data rather than formatted translated messages.

Example:

```python
REPOSITORY_INFO_TEMPLATE = "Repository: %1"
```

Avoid scattering literal button labels, dialog titles, tooltips, and status messages through views or commands.

## Testing Strategy

Write tests that protect real behavior and document useful contracts. Avoid tests that only freeze implementation details.

Good tests:

- Verify public behavior and result contracts.
- Verify components are wired correctly.
- Verify domain algorithms with meaningful examples.
- Verify integration between application actions and services.
- Verify FreeCAD runtime behavior when stubs or fakes are insufficient.

Avoid tests that:

- Check non-existence of fields or classes.
- Duplicate existing coverage without adding a new failure mode.
- Assert private implementation details that should remain easy to refactor.
- Preserve temporary development phases in filenames or test names.

### Unit Tests

Location: `tests/unit/`

Use unit tests for fast feedback and precise behavior checks. Unit tests should not require FreeCAD to be running.

Use unit tests for:

- Domain models and services.
- Diff algorithms.
- Settings codecs and persistence state.
- Application action orchestration.
- Presenter behavior with fake views.
- Entry point command routing with fakes where possible.
- Infrastructure code that can be tested without real FreeCAD.

### Integration Tests

Location: `tests/integration/`

Use integration tests when behavior depends on real FreeCAD APIs, FreeCAD document structure, GUI workbench activation, or runtime wiring.

Use integration tests for:

- Snapshot extraction from `.FCStd` documents.
- Workbench loading and activation.
- Qt widget behavior that needs FreeCAD runtime.
- FreeCAD document opening/recompute behavior.
- End-to-end workflows across adapters and application actions.

Run integration tests with:

```bash
task test:integration
```

## Common Contributor Tasks

### Add An Application Action

1. Add a focused action class under `freecad/diff_wb/application/actions/`.
2. Return an existing result model or add a small result model when needed.
3. Inject domain services or ports through the constructor.
4. Wire the action in `application/di/container.py`.
5. Add unit tests under `tests/unit/application/actions/`.

### Add UI Text

1. Add constants to `ui/translation_strings.py`.
2. Export constants through `__all__`.
3. Translate in the view or command dialog code.
4. Avoid formatting translated strings in presenters.

### Add A FreeCAD Command

1. Add a command class in `entrypoints/commands.py`.
2. Keep FreeCAD-specific code in the command.
3. Delegate behavior to a presenter or application action.
4. Register the command in `register_commands()`.
5. Add the command name to the workbench toolbox if it should appear in toolbar/menu.
6. Add command tests under `tests/unit/entrypoints/`.

### Add A Setting Or Preference

1. Add default values in `domain/config.py` if needed.
2. Update settings models or codecs under `domain/settings/`.
3. Update `FreeCADSettingsRepository` persistence behavior.
4. Update preferences UI in `ui/views/settings_preferences_page.py`.
5. Add tests for model/codec behavior and repository persistence behavior.

### Add Snapshot Or Diff Behavior

1. Put pure comparison behavior under `domain/diff/`.
2. Put snapshot model or serialization behavior under `domain/snapshots/` or `infrastructure/persistence/` depending on whether it is core model behavior or file format behavior.
3. Use focused unit tests for algorithms.
4. Add integration tests if real FreeCAD documents or runtime APIs are required.

## FreeCAD Runtime Notes

FreeCAD type stubs are installed by `uv` under `.venv/lib/python3.12/site-packages/`. Check them before assuming FreeCAD signatures.

Use the extracted AppImage runtime for live API checks:

```bash
./run_with_freecad.sh python -c "import FreeCAD; print(dir(FreeCAD))"
```

The `FreeCADGui` module is not generally available through `run_with_freecad.sh`. GUI behavior often needs manual FreeCAD testing or integration tests that run through FreeCAD's runtime.

## Additional Resources

- [Development Setup](DevSetup.md)
- [Architecture](Architecture.md)
- [FreeCAD preferences page API exploration](api-exploration/freecad-preferences-page-api.md)
- [FreeCAD document structure exploration](api-exploration/document-structure.md)
