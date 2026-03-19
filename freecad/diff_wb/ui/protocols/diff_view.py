"""File responsibility: Diff view interface definition."""

from typing import Protocol

from ..presenters.presentation_models import NodePresentation


__all__ = ["DiffView"]


class DiffView(Protocol):
    """Interface that any diff display component must implement.

    Implemented by QtDiffPanelView in the UI views layer.
    """

    def show_loading(self) -> None: ...

    def show_diff_tree(self, nodes: list[NodePresentation]) -> None: ...

    def show_summary(self, added: int, deleted: int, modified: int) -> None: ...

    def show_error(self, message: str) -> None: ...
