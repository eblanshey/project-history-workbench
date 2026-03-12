# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD runtime context abstraction.

This module provides Protocol interfaces for the FreeCAD API parts used by
the Diff Workbench, plus a FreeCadContext wrapper for dependency injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ConsoleLike(Protocol):
    """Minimal Protocol for FreeCAD's console output API."""

    def PrintMessage(self, text: str) -> None: ...
    def PrintError(self, text: str) -> None: ...
    def PrintWarning(self, text: str) -> None: ...


class DocumentLike(Protocol):
    """Minimal Protocol for FreeCAD document operations."""

    Objects: list[object]

    def getObject(self, name: str) -> object | None: ...
    def recompute(self) -> None: ...


class AppLike(Protocol):
    """Minimal Protocol for the FreeCAD application module."""

    ActiveDocument: DocumentLike | None
    Console: ConsoleLike

    def translate(self, context: str, text: str) -> str: ...


class GuiLike(Protocol):
    """Minimal Protocol for the FreeCAD GUI module."""

    pass


@dataclass(frozen=True)
class FreeCadContext:
    """Bundle of runtime bindings for the Diff Workbench.

    This wrapper allows code to be written against Protocols and enables unit
    tests to provide a fake context without importing FreeCAD.
    """

    app: AppLike
    gui: GuiLike | None = None


def get_runtime_context() -> FreeCadContext:
    """Return a context wired to the real FreeCAD runtime modules."""
    import FreeCAD as App

    try:
        import FreeCADGui as Gui
    except Exception:  # pylint: disable=broad-exception-caught
        Gui = None

    return FreeCadContext(app=App, gui=Gui)
