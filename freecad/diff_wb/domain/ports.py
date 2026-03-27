# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Port interfaces for the Diff Workbench.
# This module defines all Protocol interfaces (contracts) for external system
# interactions. These interfaces belong in the domain layer so that application
# and domain code can depend on abstractions without importing infrastructure.
"""Port interfaces for external system interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol


if TYPE_CHECKING:
    pass


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


class QtModule(Protocol):
    """Protocol for FreeCAD.Qt module which provides translation."""

    def translate(self, context: str, text: str) -> str: ...


class AppLike(Protocol):
    """Minimal Protocol for the FreeCAD application module."""

    ActiveDocument: DocumentLike | None
    Console: ConsoleLike

    def ParamGet(self, path: str) -> object: ...
    def translate(self, context: str, text: str) -> str: ...
    def GetString(self, name: str) -> str: ...

    @property
    def Qt(self) -> QtModule: ...


class GuiLike(Protocol):
    """Minimal Protocol for the FreeCAD GUI module."""

    def update(self) -> None: ...


@dataclass(frozen=True)
class FreeCadContext:
    """Bundle of runtime bindings for the Diff Workbench.

    This wrapper allows code to be written against Protocols
    and enables unit tests to provide a fake context without importing FreeCAD.

    Attributes:
        app: The FreeCAD application module (AppLike protocol)
        gui: The FreeCAD GUI module if available, None otherwise
    """

    app: AppLike
    gui: GuiLike | None = None


class FreeCadPort(Protocol):
    """Interface for FreeCAD document operations.

    This Protocol defines the minimal set of FreeCAD operations needed
    by the Diff Workbench, allowing for test doubles in unit tests.
    """

    def get_active_document(self) -> DocumentLike | None:
        """Get the active document, or None if no document is open."""
        ...

    def get_object(self, doc: DocumentLike, name: str) -> object | None:
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

    def translate(self, context: str, text: str) -> str:
        """Translate text using FreeCAD's translation system."""
        ...


class AppPort(Protocol):
    """Interface for application-level operations.

    This Protocol defines operations like translation that are provided
    by the FreeCAD application, allowing for test doubles.
    """

    def translate(self, context: str, text: str) -> str:
        """Translate the given text in the provided translation context."""
        ...


class GuiPort(Protocol):
    """Interface for FreeCAD GUI operations.

    This Protocol defines operations for loading Qt UI files and
    managing MDI subwindows, allowing for test doubles.
    """

    def load_ui(self, ui_path: str) -> object:
        """Load a Qt UI file and return the widget."""
        ...

    def get_main_window(self) -> object:
        """Get the main application window."""
        ...

    def get_mdi_area(self) -> Any:
        """Get the MDI area for subwindows, or None if not available."""
        ...

    def add_subwindow(self, *, mdi_area: object, widget: object) -> object:
        """Add a widget as an MDI subwindow and return the QMdiSubWindow."""
        ...

    def find_subwindow(self, *, mdi_area: object, title: str) -> object | None:
        """Find an existing subwindow by title, or None if not found."""
        ...


__all__ = [
    "FreeCadContext",
    "FreeCadPort",
    "AppPort",
    "GuiPort",
    "DocumentLike",
    "ConsoleLike",
    "QtModule",
    "AppLike",
    "GuiLike",
]
