"""Module responsibility: Fake snapshot view for testing."""

from typing import Protocol

from freecad.diff_wb.ui.protocols.snapshot_view import SnapshotView


class FakeSnapshotView(SnapshotView):
    """Fake implementation of SnapshotView for unit testing.

    Captures method calls for verification in tests.
    """

    def __init__(self):
        self._call_log = []
        self._last_call = None

    def show_success(self, message: str, snapshot_id: str) -> None:
        """Capture success call instead of showing UI."""
        call = {"method": "show_success", "message": message, "snapshot_id": snapshot_id}
        self._call_log.append(call)
        self._last_call = call

    def show_error(self, message: str) -> None:
        """Capture error call instead of showing UI."""
        call = {"method": "show_error", "message": message}
        self._call_log.append(call)
        self._last_call = call

    def show_loading(self, message: str = "Creating snapshot...") -> None:
        """Capture loading call instead of showing UI."""
        call = {"method": "show_loading", "message": message}
        self._call_log.append(call)
        self._last_call = call

    def clear_calls(self):
        """Clear the call log."""
        self._call_log.clear()
        self._last_call = None

    def get_call_count(self):
        """Return number of calls logged."""
        return len(self._call_log)
