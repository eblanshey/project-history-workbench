# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD Diff Workbench GUI initialization.

This module is the entrypoint for FreeCAD when loading the Diff Workbench.
It registers the workbench, commands, and translation paths.
"""

try:
    import FreeCADGui as Gui  # pylint: disable=import-error
except Exception:  # pylint: disable=broad-exception-caught
    Gui = None

if Gui is not None:
    from .entrypoints.commands import register_commands
    from .entrypoints.workbench import DiffWorkbench
    from .freecad_version_check import check_python_and_freecad_version
    from .resources import TRANSLATIONSPATH

    Gui.addLanguagePath(TRANSLATIONSPATH)
    Gui.updateLocale()

    check_python_and_freecad_version()
    register_commands()
    Gui.addWorkbench(DiffWorkbench())
