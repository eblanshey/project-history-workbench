# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD port interface and adapter.

This module defines the FreeCadPort Protocol for document operations
and provides a runtime adapter that uses the real FreeCAD API.
"""

from __future__ import annotations

from typing import Protocol

from .freecad_context import FreeCadContext, get_runtime_context


class FreeCadPort(Protocol):
    """Interface for FreeCAD document operations.

    This Protocol defines the minimal set of FreeCAD operations needed
    by the Diff Workbench, allowing for test doubles in unit tests.
    """

    def get_active_document(self) -> object | None:
        """Get the active document, or None if no document is open."""
        ...

    def get_object(self, doc: object, name: str) -> object | None:
        """Get a document object by name."""
        ...

    def try_recompute_active_document(self) -> None:
        """Recompute the active document if one exists."""
        ...

    def try_update_gui(self) -> None:
        """Trigger a GUI update if the GUI is available."""
        ...

    def log(self, text: str) -> None:
        """Log a message to the FreeCAD console."""
        ...

    def warn(self, text: str) -> None:
        """Show a warning message."""
        ...

    def message(self, text: str) -> None:
        """Show an informational message."""
        ...


class FreeCadPortAdapter:
    """Runtime adapter implementing FreeCadPort using real FreeCAD APIs."""

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def get_active_document(self) -> object | None:
        return self._ctx.app.ActiveDocument

    def get_object(self, doc: object, name: str) -> object | None:
        return doc.getObject(name)

    def try_recompute_active_document(self) -> None:
        doc = self._ctx.app.ActiveDocument
        if doc is not None:
            doc.recompute()

    def try_update_gui(self) -> None:
        if self._ctx.gui is not None:
            self._ctx.gui.update()

    def log(self, text: str) -> None:
        self._ctx.app.Console.PrintMessage(text + "\n")

    def warn(self, text: str) -> None:
        self._ctx.app.Console.PrintWarning(text + "\n")

    def message(self, text: str) -> None:
        self._ctx.app.Console.PrintMessage(text + "\n")


def get_port(ctx: FreeCadContext | None = None) -> FreeCadPort:
    """Get a FreeCadPort instance.

    If no context is provided, creates a runtime context.
    """
    if ctx is None:
        ctx = get_runtime_context()
    return FreeCadPortAdapter(ctx)
