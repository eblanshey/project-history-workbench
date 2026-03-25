# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD command entry points for the Diff Workbench.

This module defines the FreeCAD commands that bridge user interactions
(toolbar/menu clicks) with application layer actions and UI presenters.
"""

import os

from ..resources import ICONPATH


class _TakeSnapshotCommand:
    """Command to take a new snapshot of the active document."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Take Snapshot",
            "ToolTip": "Create a snapshot of the current document",
            "Pixmap": os.path.join(ICONPATH, "TakeSnapshot.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container

        container = get_container()
        result = container.take_snapshot_action.execute()
        container.snapshot_presenter.present_result(result)


class _CompareCommand:
    """Command to compare against a selected snapshot."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Compare",
            "ToolTip": "Compare snapshots",
            "Pixmap": os.path.join(ICONPATH, "Compare.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container

        container = get_container()
        # Phase 8: Get snapshot IDs from UI selection
        # TODO: Phase 8 - Implement UI dialog for snapshot selection
        old_id = self._get_selected_old_snapshot()
        new_id = self._get_selected_new_snapshot()

        result = container.compare_snapshots_action.execute(old_id, new_id)
        if result.success and container.diff_presenter and result.diff_result is not None:
            container.diff_presenter.present_diff(result.diff_result)

    def _get_selected_old_snapshot(self) -> str:
        """Get the selected old snapshot ID from UI.

        Returns:
            The ID of the snapshot selected as the "old" snapshot.

        Raises:
            NotImplementedError: Phase 8 - UI selection not yet implemented.
        """
        raise NotImplementedError("Phase 8 - UI selection not yet implemented")

    def _get_selected_new_snapshot(self) -> str:
        """Get the selected new snapshot ID from UI.

        Returns:
            The ID of the snapshot selected as the "new" snapshot.

        Raises:
            NotImplementedError: Phase 8 - UI selection not yet implemented.
        """
        raise NotImplementedError("Phase 8 - UI selection not yet implemented")


class _SwapColumnsCommand:
    """Command to swap left/right columns in the diff view."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Swap Columns",
            "ToolTip": "Swap the left and right columns",
            "Pixmap": os.path.join(ICONPATH, "SwapColumns.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the swap columns action.

        TODO: Phase 8 - Implement when UI view exists.
        """
        # Phase 8: Will call view method to swap columns when UI is implemented
        pass


def register_commands() -> None:
    """Register the Diff Workbench commands with FreeCAD."""
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand("DiffTakeSnapshot", _TakeSnapshotCommand())
    Gui.addCommand("DiffCompare", _CompareCommand())
    Gui.addCommand("DiffSwapColumns", _SwapColumnsCommand())
