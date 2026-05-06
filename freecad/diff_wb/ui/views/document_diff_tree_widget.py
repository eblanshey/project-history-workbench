"""File responsibility: Document diff tree widget with summary and staging controls."""

from collections.abc import Callable

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...domain.diff.models import DiffState
from ..presenters.presentation_models import DiffTreePresentation, DocumentStatusIndicator, NodePresentation
from ..translation_strings import DIFF_SUMMARY_CHANGED_LABEL, STAGE_ALL_LABEL
from .diff_theme import DIFF_STATE_ROLE, DiffItemDelegate, background_for_state, foreground_for_background
from .models import HistorySelection


__all__ = ["DocumentDiffTreeWidget"]


class DocumentDiffTreeWidget(QWidget):
    """Middle-column widget that renders document/node diffs and staging actions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_add_button_callback: Callable[[str], None] | None = None
        self._on_stage_all_callback: Callable[[], None] | None = None
        self._on_node_selection_callback: Callable[[str, str], None] | None = None
        self._current_selection: HistorySelection | None = None
        self._stage_buttons: dict[str, QPushButton] = {}
        self._diff_item_delegate: DiffItemDelegate | None = None
        self._setup_ui()

    @property
    def tree_widget(self) -> QTreeWidget:
        """Expose underlying tree for facade compatibility and focused tests."""
        return self._tree_widget

    def _setup_ui(self) -> None:
        summary_container = QWidget(self)
        summary_layout = QHBoxLayout(summary_container)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(16)

        self._changed_label = QLabel("")
        self._changed_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self._changed_label)

        self._stage_all_button = QPushButton()
        self._stage_all_button.setText(QCoreApplication.translate("DiffView", STAGE_ALL_LABEL))
        self._stage_all_button.setFixedWidth(70)
        self._stage_all_button.hide()
        self._stage_all_button.clicked.connect(self._on_stage_all_clicked)
        summary_layout.addWidget(self._stage_all_button)

        self._tree_widget = QTreeWidget()
        self._tree_widget.setHeaderLabels(["Tree"])
        self._tree_widget.setColumnCount(1)
        self._tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._diff_item_delegate = DiffItemDelegate(self._tree_widget)
        self._tree_widget.setItemDelegate(self._diff_item_delegate)
        self._tree_widget.itemClicked.connect(self._on_tree_item_clicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(summary_container)
        layout.addWidget(self._tree_widget)

    def set_current_history_selection(self, selection: HistorySelection | None) -> None:
        """Set current history selection for conditional Working Tree controls."""
        self._current_selection = selection

    def set_node_selection_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for node selection with (git_path, node_path).

        Args:
            callback: A callable receiving (git_path, node_path) when a node is clicked.
        """
        self._on_node_selection_callback = callback

    def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback for when the '+ Stage' button is clicked.

        Args:
            callback: A callable that receives the git_path (str) of the
                      document whose '+ Stage' button was clicked.
        """
        self._on_add_button_callback = callback

    def set_stage_all_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback for Stage All button.

        Args:
            callback: A no-argument callable to invoke on click.
        """
        self._on_stage_all_callback = callback

    def set_stage_all_button_visible(self, visible: bool) -> None:
        """Show or hide the Stage All button.

        Args:
            visible: Whether the button should be visible.
        """
        self._stage_all_button.setVisible(visible)

    def set_stage_all_button_enabled(self, enabled: bool) -> None:
        """Enable or disable the Stage All button.

        Args:
            enabled: Whether the button should be enabled.
        """
        self._stage_all_button.setEnabled(enabled)

    def show_doc_diff(self, nodes: list[NodePresentation], git_path: str = "") -> None:
        """Display the diff tree with color-coded nodes.

        Args:
            nodes: List of root-level NodePresentation objects with nested children.
            git_path: The git path to display as top-level item
        """
        self._tree_widget.clear()

        if not nodes:
            return

        top_level_text = git_path or "Unnamed Document"
        root_item = QTreeWidgetItem([top_level_text])
        root_item.setData(0, Qt.ItemDataRole.UserRole, git_path or top_level_text)

        for node in nodes:
            root_item.addChild(self._create_tree_item(node))

        self._tree_widget.addTopLevelItem(root_item)
        self._expand_nodes_with_changes(root_item)
        self._tree_widget.show()

    def show_doc_diffs(self, diffs: list[DiffTreePresentation]) -> None:
        """Display multiple diff trees in the tree widget.

        Args:
            diffs: List of DiffTreePresentation objects, each representing
                  a diff tree for one document with its metadata.
        """
        self._tree_widget.clear()
        self._stage_buttons.clear()

        if not diffs:
            return

        for diff in diffs:
            top_level_text = diff.git_path or "Unnamed Document"

            root_item = QTreeWidgetItem([top_level_text])
            root_item.setData(0, Qt.ItemDataRole.UserRole, diff.git_path or top_level_text)

            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(4, 2, 4, 2)

            layout.addWidget(QLabel(top_level_text))
            layout.addStretch()

            self._add_status_indicators(layout, diff.indicators)

            show_stage_button = (
                self._current_selection is not None and self._current_selection.item_kind == "WORKING_TREE"
            )

            if show_stage_button:
                add_button = QPushButton("+ Stage")
                add_button.setEnabled(diff.stage_button_enabled)
                add_button.setFixedWidth(40)
                add_button.clicked.connect(lambda checked, gp=diff.git_path: self._on_add_button_clicked(gp))
                layout.addWidget(add_button)
                if diff.git_path:
                    self._stage_buttons[diff.git_path] = add_button

            self._tree_widget.addTopLevelItem(root_item)
            self._tree_widget.setItemWidget(root_item, 0, container)

            for node in diff.nodes:
                item = self._create_tree_item(node)
                root_item.addChild(item)

            self._expand_nodes_with_changes(root_item)

        self._tree_widget.show()

    def clear_doc_diffs(self) -> None:
        """Clear document diff tree and related controls."""
        self._tree_widget.clear()
        self._changed_label.setText("No changes")
        self.set_stage_all_button_visible(False)
        self.set_stage_all_button_enabled(False)
        self._stage_buttons.clear()

    def _add_status_indicators(self, layout: QHBoxLayout, indicators: list[DocumentStatusIndicator]) -> None:
        """Add status indicators with tooltip to the layout.

        Args:
            layout: The QHBoxLayout to add widgets to.
            indicators: List of document status indicators to display.
        """
        if not indicators:
            return

        for indicator in indicators:
            icon_label = QLabel()
            icon_label.setPixmap(indicator.icon.pixmap(16, 16))
            icon_label.setToolTip(QCoreApplication.translate("DiffView", indicator.tooltip))
            layout.addWidget(icon_label)

    def _on_add_button_clicked(self, git_path: str) -> None:
        """Handle '+ Stage' button click by invoking the callback.

        Args:
            git_path: The git_path of the document whose button was clicked.
        """
        if self._on_add_button_callback:
            self._on_add_button_callback(git_path)

    def _expand_nodes_with_changes(self, item: QTreeWidgetItem) -> None:
        """Recursively expand nodes that have descendants with changes.

        Args:
            item: The tree item to check and expand if needed
        """
        child_count = item.childCount()
        has_changed_descendants = False

        for i in range(child_count):
            child = item.child(i)
            has_changes = child.data(0, Qt.ItemDataRole.UserRole + 1)
            if has_changes:
                has_changed_descendants = True
            self._expand_nodes_with_changes(child)

        if has_changed_descendants:
            item.setExpanded(True)

    def _create_tree_item(self, node: NodePresentation) -> QTreeWidgetItem:
        """Recursively create a QTreeWidgetItem from NodePresentation.

        Args:
            node: The NodePresentation to convert.

        Returns:
            QTreeWidgetItem with text, color, and children populated.
        """
        name = node.path.split("/")[-1] if node.path else ""
        text = node.label if node.label == name else f"{node.label} ({name})"

        item = QTreeWidgetItem([text])
        item.setToolTip(0, node.type_id)
        item.setData(0, Qt.ItemDataRole.UserRole, node.path)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, node.has_changes)

        self._apply_diff_state(item, node.state)

        for child in node.children:
            child_item = self._create_tree_item(child)
            item.addChild(child_item)

        return item

    def _apply_diff_state(self, item: QTreeWidgetItem, state: DiffState) -> None:
        """Apply semantic diff coloring data to a tree item."""
        if state == DiffState.UNCHANGED:
            return
        item.setData(0, DIFF_STATE_ROLE, state)
        background = background_for_state(state, self._tree_widget.palette())
        if background is None:
            return
        item.setBackground(0, QBrush(background))
        item.setForeground(0, QBrush(foreground_for_background(background, self._tree_widget.palette())))

    def show_summary(self, changed_docs: int) -> None:
        """Display count of documents that contain changes.

        Args:
            changed_docs: Number of changed documents.
        """
        if changed_docs == 0:
            self._changed_label.setText("No changes")
            return

        changed_text = QCoreApplication.translate("DiffView", DIFF_SUMMARY_CHANGED_LABEL)
        self._changed_label.setText(f"{changed_text} {changed_docs}")

    def _on_stage_all_clicked(self) -> None:
        """Handle Stage All button click by invoking the callback."""
        if self._on_stage_all_callback:
            self._on_stage_all_callback()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Extract git_path from root and node_path from clicked item, then invoke callback.

        Args:
            item: The clicked tree item
            column: The column that was clicked
        """
        if self._on_node_selection_callback is None:
            return

        node_path = item.data(0, Qt.ItemDataRole.UserRole)

        root = item
        while root.parent():
            root = root.parent()
        git_path = root.data(0, Qt.ItemDataRole.UserRole)

        if git_path and node_path:
            self._on_node_selection_callback(git_path, node_path)

    def collapse_tree_item(self, git_path: str) -> None:
        """Collapse the root tree item for the given git_path.

        Args:
            git_path: The git_path of the root tree item to collapse.
        """
        for i in range(self._tree_widget.topLevelItemCount()):
            item = self._tree_widget.topLevelItem(i)
            item_git_path = item.data(0, Qt.ItemDataRole.UserRole)
            if item_git_path == git_path:
                item.setExpanded(False)
                break

    def set_stage_button_enabled(self, git_path: str, enabled: bool) -> None:
        """Enable or disable the '+ Stage' button for a given git_path.

        Args:
            git_path: The git_path of the document whose button to update.
            enabled: Whether the stage button should be enabled.
        """
        if git_path in self._stage_buttons:
            self._stage_buttons[git_path].setEnabled(enabled)
