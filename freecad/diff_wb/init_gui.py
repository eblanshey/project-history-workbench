# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: This module is the entrypoint for FreeCAD when loading the Diff Workbench.
It initializes the runtime context, wires dependency injection, creates infrastructure
adapters, and registers the workbench, commands, and translation paths.
"""

"""FreeCAD Diff Workbench GUI initialization."""

try:
    import FreeCADGui as Gui  # pylint: disable=import-error
except Exception:  # pylint: disable=broad-exception-caught
    Gui = None

if Gui is not None:
    from .application.di.container import create_application_container
    from .domain.snapshots import InMemorySnapshotRepository
    from .entrypoints.commands import register_commands
    from .entrypoints.workbench import DiffWorkbench
    from .freecad_version_check import check_python_and_freecad_version
    from .infrastructure.freecad.context import get_freecad_runtime_context
    from .resources import TRANSLATIONSPATH

    # Initialize FreeCAD language support
    Gui.addLanguagePath(TRANSLATIONSPATH)
    Gui.updateLocale()

    # Check Python and FreeCAD version compatibility
    check_python_and_freecad_version()

    # Create runtime context for dependency injection
    ctx = get_freecad_runtime_context()

    # Create infrastructure adapters
    snapshot_repo = InMemorySnapshotRepository()

    # Create application layer container (wires all dependencies)
    container = create_application_container(
        ctx=ctx,
        snapshot_repo=snapshot_repo,
        diff_view=None,  # Phase 8: Will be DiffPanelView() when UI exists
    )

    # Register commands with wired actions and presenters
    register_commands(container)

    # Register workbench
    Gui.addWorkbench(DiffWorkbench())
