# SPDX-License-Identifier: LGPL-3.0-or-later
"""FreeCAD command registrations for the Diff Workbench.

This module defines the toolbar/menu commands for snapshot management
and diff comparison operations.
"""

import os

from ..ports.app_port import AppPortAdapter
from ..resources import ICONPATH


class _TakeSnapshotCommand:
    """Command to take a new snapshot of the active document."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        translate = AppPortAdapter().translate
        return {
            "MenuText": translate("Workbench", "Take Snapshot"),
            "ToolTip": translate("Workbench", "Create a snapshot of the current document"),
            "Pixmap": os.path.join(ICONPATH, "TakeSnapshot.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the take snapshot action."""
        # TODO: Implement snapshot creation logic in Phase 4
        pass


class _CompareCommand:
    """Command to compare against a selected snapshot."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        translate = AppPortAdapter().translate
        return {
            "MenuText": translate("Workbench", "Compare"),
            "ToolTip": translate("Workbench", "Compare snapshots"),
            "Pixmap": os.path.join(ICONPATH, "Compare.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the compare action."""
        # TODO: Implement comparison logic in Phase 3-5
        pass


class _SwapColumnsCommand:
    """Command to swap left/right columns in the diff view."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        translate = AppPortAdapter().translate
        return {
            "MenuText": translate("Workbench", "Swap Columns"),
            "ToolTip": translate("Workbench", "Swap the left and right columns"),
            "Pixmap": os.path.join(ICONPATH, "SwapColumns.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the swap columns action."""
        # TODO: Implement column swap logic in Phase 5
        pass


def register_commands() -> None:
    """Register the Diff Workbench commands with FreeCAD."""
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand("DiffTakeSnapshot", _TakeSnapshotCommand())
    Gui.addCommand("DiffCompare", _CompareCommand())
    Gui.addCommand("DiffSwapColumns", _SwapColumnsCommand())
