# Plan: Implement Check Task for freecad_diff_workbench

## Overview
Implement a "check" task similar to freecad_datamanager_workbench that runs linter, formatter, and other code quality checks using uv as the package manager.

## What is uv?
`uv` is a Python package manager (similar to how `npm` works for JavaScript). It can:
- Install dependencies: `uv add pytest`
- Run commands in a virtual environment: `uv run pytest`
- Install tools globally: `uv tool install ruff`

## What is Taskfile?
`Taskfile` is a task runner (similar to npm scripts or Make). It defines tasks in a YAML file that can run any command. The freecad_datamanager_workbench uses Taskfile with `uv run` to execute Python tools.

## Implementation Steps

### 1. Update pyproject.toml
Add missing dev dependencies to the `[dependency-groups]` section:
- `radon>=6.0.1` - For code complexity analysis
- `taskfile-help>=0.4.1` - For help commands (optional, but useful)

Add mypy configuration:
- Configure strict mode with appropriate exclusions
- Add overrides for FreeCAD modules to ignore missing imports
- Add overrides for ports modules to disable `attr-defined` and `no-any-return` errors (FreeCAD API doesn't have type stubs)

### 2. Create Taskfile.yml
Create a simple, single-file Taskfile.yml (not split into multiple files) with the following tasks:

#### Main Tasks:
- `default` - Show available tasks
- `check` - Run all code quality checks (format, lint, complexity)
- `format` - Format code with ruff
- `format:check` - Check formatting without modifying
- `lint` - Run linting with ruff and mypy
- `lint:ruff` - Run ruff linter
- `lint:mypy` - Run mypy type checker
- `lint:check_docstrs` - Check for required docstrings
- `metrics:complexity` - Analyze code complexity with radon

#### Supporting Variables:
- `APP_NAME` - Auto-detected from pyproject.toml
- `SRC` - Source directory (freecad/diff_wb/)
- `TESTS` - Tests directory (tests/)

### 3. Create check_docstrs.py Script
Create the docstring checker script:
- Create `scripts/` directory
- Create `check_docstrs.py` that checks for required docstrings
- Skip Adapter classes (they implement protocols that have docstrings)
- Skip Protocol classes (their methods are interface definitions)

### 4. Create .python-version File
Create a `.python-version` file specifying the Python version (e.g., `3.12`)

### 5. Create LICENSE-CODE File
Create a `LICENSE-CODE` file with the LGPL-3.0-or-later license text

### 6. Fix Code Issues
- Fix unused imports in resources.py
- Fix type annotations in settings_port.py (add return types, generic type parameters)

## Commands Users Will Run

| Command | Description |
|---------|-------------|
| `task` | Show available tasks |
| `task check` | Run all quality checks |
| `task format` | Format code |
| `task lint` | Run linters |
| `task metrics:complexity` | Check code complexity |

## Comparison to freecad_datamanager_workbench

This implementation will be **simpler** than freecad_datamanager_workbench:
- Single Taskfile.yml instead of multiple included taskfiles
- Fewer specialized tasks (no separate lint:src, lint:tests, etc.)
- No test execution in the check task (as requested)
- No SPDX header checks, emoji checks, or deadcode checks (can add later if needed)

## Files Created/Modified

1. **Created**: `tasks/1-implement-check-task.md` (this plan file)
2. **Created**: `Taskfile.yml` - Main task definitions
3. **Created**: `scripts/check_docstrs.py` - Docstring checker (with Adapter/Protocol exclusions)
4. **Created**: `.python-version` - Python version specification (3.12)
5. **Created**: `LICENSE-CODE` - LGPL-3.0-or-later license text
6. **Modified**: `pyproject.toml` - Added dev dependencies and mypy configuration
7. **Modified**: `freecad/diff_wb/ports/settings_port.py` - Fixed type annotations
8. **Modified**: `freecad/diff_wb/resources.py` - Removed unused import

## Implementation Notes

### Mypy Configuration
The mypy configuration uses `strict = true` but disables specific error codes for the ports modules:
- `attr-defined` - FreeCAD API methods aren't known to mypy
- `no-any-return` - FreeCAD returns dynamic types

This allows strict type checking while accommodating FreeCAD's lack of type stubs.

### Docstring Checker
The custom docstring checker skips:
- Classes ending with "Adapter" - These implement Protocol interfaces
- Classes inheriting from "Protocol" - These are interface definitions

This avoids requiring docstrings on implementation details when the interface already documents the contract.
