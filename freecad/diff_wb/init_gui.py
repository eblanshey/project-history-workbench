# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Ultra-thin GUI initialization module that only sets up translation
support, performs version checks, provides runtime context, and registers the DiffWorkbench
class with FreeCAD. No container creation, no command registration, no global state manipulation."""

try:
    import FreeCADGui as Gui
except Exception as e:
    from .utils import Log

    Log.exception(f"Failed to import FreeCADGui: {e}")
    Gui = None

if Gui is not None:
    from .entrypoints.workbench import DiffWorkbench
    from .freecad_version_check import check_python_and_freecad_version
    from .resources import TRANSLATIONSPATH

    # Initialize FreeCAD language support
    Gui.addLanguagePath(TRANSLATIONSPATH)
    Gui.updateLocale()

    # Check Python and FreeCAD version compatibility
    check_python_and_freecad_version()

    # Register workbench (container creation happens in workbench.Initialize())
    Gui.addWorkbench(DiffWorkbench())
