# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD port adapters and factory functions.

This module provides adapter classes and factory functions that implement
the port interfaces defined in domain.ports. It adapts the real FreeCAD API
to the port abstractions, allowing domain/application code to remain independent
of FreeCAD-specific implementations.

All factory functions require an explicit FreeCadContext parameter - no automatic
context creation. This enforces explicit dependency injection and keeps the domain
and application layers testable without FreeCAD dependencies.
"""

from __future__ import annotations

from typing import Any

from ...domain.ports import (
    AppPort,
    DocumentLike,
    FreeCadContext,
    FreeCadPort,
    GuiPort,
)


def get_freecad_runtime_context() -> FreeCadContext:
    """Return a context wired to the real FreeCAD runtime modules.

    This function should only be called from the composition root (init_gui.py)
    when FreeCAD is actually running.

    Returns:
        FreeCadContext with real FreeCAD/FreeCADGui modules
    """
    import FreeCAD as App

    try:
        import FreeCADGui as Gui
    except Exception:  # pylint: disable=broad-exception-caught
        Gui = None  # type: ignore[assignment]

    return FreeCadContext(app=App, gui=Gui)  # type: ignore[arg-type]


class FreeCadPortAdapter:
    """Runtime adapter implementing FreeCadPort using real FreeCAD APIs.

    This class adapts the real FreeCAD API to the FreeCadPort interface,
    allowing domain code to work with the port abstraction while infrastructure code
    handles the actual FreeCAD calls.
    """

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def get_active_document(self) -> object | None:
        return self._ctx.app.ActiveDocument

    def get_object(self, doc: DocumentLike, name: str) -> object | None:
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

    def translate(self, context: str, text: str) -> str:
        try:
            qt_obj = self._ctx.app.Qt
        except AttributeError:
            # Fall back to simple translation if Qt not available
            return text.replace(" ", "_").lower()
        result = qt_obj.translate(context, text)
        return result


def get_port(ctx: FreeCadContext) -> FreeCadPort:
    """Get a FreeCadPort instance.

    Factory function that creates and returns a FreeCadPortAdapter
    instance using the provided context.

    Args:
        ctx: FreeCAD runtime context (mandatory)

    Returns:
        FreeCadPortAdapter instance
    """
    return FreeCadPortAdapter(ctx)  # type: ignore[return-value]


class AppPortAdapter:
    """Runtime adapter implementing AppPort using FreeCAD's translation API."""

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def translate(self, context: str, text: str) -> str:
        try:
            qt_obj = self._ctx.app.Qt
        except AttributeError:
            # Fall back to simple translation if Qt not available
            return text.replace(" ", "_").lower()
        result = qt_obj.translate(context, text)
        return result


def get_app_port(ctx: FreeCadContext) -> AppPort:
    """Get an AppPort instance.

    Factory function that creates and returns an AppPortAdapter
    instance using the provided context.

    Args:
        ctx: FreeCAD runtime context (mandatory)

    Returns:
        AppPortAdapter instance
    """
    return AppPortAdapter(ctx)


class GuiPortAdapter:
    """Runtime adapter implementing GuiPort using FreeCAD's Qt API.

    This class adapts FreeCAD's Qt API to the GuiPort interface,
    allowing domain code to work with the port abstraction while infrastructure code
    handles the actual Qt calls.
    """

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def load_ui(self, ui_path: str) -> object:
        from PySide6.QtCore import QFile
        from PySide6.QtUiTools import QUiLoader
        from PySide6.QtWidgets import QApplication as QtApp

        # Get the main application instance if available
        try:
            from FreeCADGui import getMainWindow

            if getMainWindow():
                QtApp.instance()
        except Exception:
            pass

        loader = QUiLoader()
        file = QFile(ui_path)
        if not file.open(QFile.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Cannot open UI file: {ui_path}")
        widget = loader.load(file)
        file.close()
        return widget

    def get_main_window(self) -> object:
        from FreeCADGui import getMainWindow

        return getMainWindow()

    def get_mdi_area(self) -> Any:
        main_window: Any = self.get_main_window()
        return main_window.workspace()

    def add_subwindow(self, *, mdi_area: Any, widget: object) -> object:
        subwindow = mdi_area.addSubWindow(widget)
        widget.setParent(mdi_area)  # type: ignore[attr-defined]
        return subwindow

    def find_subwindow(self, *, mdi_area: Any, title: str) -> Any:
        for sub in mdi_area.subWindowList():
            if sub.windowTitle() == title:
                return sub
        return None


def get_gui_port(ctx: FreeCadContext) -> GuiPort:
    """Get a GuiPort instance.

    Factory function that creates and returns a GuiPortAdapter
    instance using the provided context.

    Args:
        ctx: FreeCAD runtime context (mandatory)

    Returns:
        GuiPortAdapter instance

    Raises:
        RuntimeError: If GUI is not available
    """
    if ctx.gui is None:
        raise RuntimeError("GUI not available")
    return GuiPortAdapter(ctx)


__all__ = [
    "FreeCadContext",
    "get_freecad_runtime_context",
    "get_port",
    "get_app_port",
    "get_gui_port",
    "FreeCadPort",
    "AppPort",
    "GuiPort",
    "FreeCadPortAdapter",
    "AppPortAdapter",
    "GuiPortAdapter",
]
