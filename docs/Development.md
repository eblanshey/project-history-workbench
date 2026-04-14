# FreeCAD Diff Workbench: Development Guide

## Common Import Patterns

### Domain Models

Recommended imports using module `__init__.py` for clean public API access:

```python
from freecad.diff_wb.domain.snapshots import Snapshot, SnapshotRepository
from freecad.diff_wb.domain.tree import TreeNode, Property, Vector
from freecad.diff_wb.domain.diff import DiffResult, DiffEngine
from freecad.diff_wb.domain.settings import Settings, SettingsRepository
```

### Infrastructure Adapters

Concrete implementations when you need real adapters instead of interfaces:

```python
from freecad.diff_wb.infrastructure.freecad.ports import FreeCadContext, get_port, get_app_port, get_gui_port
from freecad.diff_wb.infrastructure.freecad.settings_repo import FreeCADSettingsRepository
from freecad.diff_wb.infrastructure.freecad.logger import FreeCADLogger
```

### Logging

Use the unified logging utility for all application messages:

```python
from freecad.diff_wb.utils import Log

Log.info("Informational message")
Log.warning("Warning message")
Log.error("Error message")
```

**Important notes:**
- **No translation needed**: Log messages are not translated. They are meant for developers and technical users who can read English.
- **Default behavior**: Before initialization, messages go to stdout/stderr (visible in terminal).
- **Production**: After `workbench.Initialize()`, messages go to FreeCAD console via `FreeCADLogger`.
- **Testing**: Tests can inject a `FakeLogger` via `set_logger()` to capture and verify log messages.

Example usage:

```python
# In presenters, actions, or any application code
def take_snapshot(self, name: str) -> None:
    Log.info(f"Creating snapshot '{name}'")
    # ... snapshot logic ...
    Log.info(f"Snapshot '{name}' created successfully")
```

### Direct Module Access

Access specific classes directly when needed:

```python
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.diff.engine import DiffEngine
```









## Additional Resources

- [ARCHITECTURE.md](Architecture.md) - Detailed architecture overview
- [PLAN.md](MVP-Implementation.md) - Implementation plan and progress
- [feature_development.md](feature_development.md) - AI development process guide
