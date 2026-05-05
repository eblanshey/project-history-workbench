"""File responsibility: Unit tests for DocumentDiffTreeWidget component.

These tests verify the extracted document diff tree widget functionality,
including tree rendering, staging controls, and callback wiring.
"""

from __future__ import annotations

import pytest

from freecad.diff_wb.domain.diff.models import DiffState
from freecad.diff_wb.ui.views.document_diff_tree_widget import DocumentDiffTreeWidget


@pytest.fixture(scope="module")
def widget() -> DocumentDiffTreeWidget:
    """Create a DocumentDiffTreeWidget instance for testing.

    Note: This uses module scope to ensure QApplication is created once
    and reused across all tests in this module.
    """
    from PySide6.QtWidgets import QApplication

    # Ensure QApplication exists before creating widgets
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    return DocumentDiffTreeWidget()


class TestShowDocDiffEmptyList:
    """Tests for show_doc_diff() with empty list."""

    def test_show_doc_diff_with_empty_list_clears_tree(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_doc_diff() clears tree when given empty list."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Tree has some items
        root_node = NodePresentation(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            state=DiffState.ADDED,
            has_changes=True,
            children=[],
        )
        widget.show_doc_diff([root_node])
        assert widget.tree_widget.topLevelItemCount() == 1

        # When: Show empty list
        widget.show_doc_diff([])

        # Then: Tree is cleared (empty nodes means no display)
        assert widget.tree_widget.topLevelItemCount() == 0


class TestShowDocDiffNodeColorsAndUserRole:
    """Tests for node colors and Qt.UserRole path storage."""

    def test_added_nodes_shown_with_green_background(self, widget) -> None:  # type: ignore[no-untyped-def]
        """ADDED nodes display with light green background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: ADDED node
        added_node = NodePresentation(
            path="Body/NewPad",
            type_id="PartDesign::Pad",
            label="NewPad",
            state=DiffState.ADDED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with ADDED node
        widget.show_doc_diff([added_node])

        # Then: Root item exists and child has green background
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        bg_color = child_item.background(0).color()
        assert bg_color == QColor(200, 255, 200)

    def test_deleted_nodes_shown_with_red_background(self, widget) -> None:  # type: ignore[no-untyped-def]
        """DELETED nodes display with light red background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: DELETED node
        deleted_node = NodePresentation(
            path="Body/OldPad",
            type_id="PartDesign::Pad",
            label="OldPad",
            state=DiffState.DELETED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with DELETED node
        widget.show_doc_diff([deleted_node])

        # Then: Root item exists and child has red background
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        bg_color = child_item.background(0).color()
        assert bg_color == QColor(255, 200, 200)

    def test_modified_nodes_shown_with_blue_background(self, widget) -> None:  # type: ignore[no-untyped-def]
        """MODIFIED nodes display with light blue background."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: MODIFIED node
        modified_node = NodePresentation(
            path="Body/ModifiedPad",
            type_id="PartDesign::Pad",
            label="ModifiedPad",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with MODIFIED node
        widget.show_doc_diff([modified_node])

        # Then: Root item exists and child has blue background
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        bg_color = child_item.background(0).color()
        assert bg_color == QColor(200, 200, 255)

    def test_unchanged_nodes_shown_without_color(self, widget) -> None:  # type: ignore[no-untyped-def]
        """UNCHANGED nodes display without custom color (default background)."""
        from PySide6.QtGui import QColor

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: UNCHANGED node
        unchanged_node = NodePresentation(
            path="Body/BasePart",
            type_id="PartDesign::Body",
            label="BasePart",
            state=DiffState.UNCHANGED,
            has_changes=False,
            children=[],
        )

        # When: Show tree with UNCHANGED node
        widget.show_doc_diff([unchanged_node])

        # Then: Root item exists and child has default background (not colored)
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        bg_color = child_item.background(0).color()
        # Should NOT be any of the special colors
        assert bg_color != QColor(200, 255, 200)  # Not green
        assert bg_color != QColor(255, 200, 200)  # Not red
        assert bg_color != QColor(200, 200, 255)  # Not blue

    def test_path_stored_in_user_role_for_retrieval(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Node paths are stored in Qt.UserRole for later property lookup."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Node with a specific path
        test_node = NodePresentation(
            path="Body/Pad/Length",
            type_id="PropertyLength",
            label="Length",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[],
        )

        # When: Show tree with the node
        widget.show_doc_diff([test_node])

        # Then: Path is retrievable from UserRole on child item (root is git_path wrapper)
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None
        stored_path = child_item.data(0, Qt.ItemDataRole.UserRole)
        assert stored_path == "Body/Pad/Length"


class TestShowDocDiffsWithStageButtons:
    """Tests for show_doc_diffs() with stage button visibility."""

    def test_show_doc_diffs_creates_top_level_document_rows(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_doc_diffs() creates top-level document rows."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                )
            ]
        )

        assert widget.tree_widget.topLevelItemCount() == 1
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.text(0) == "parts/A.FCStd"

    def test_stage_buttons_only_appear_when_working_tree_selected(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Stage buttons only appear when current selection is WORKING_TREE."""
        from PySide6.QtWidgets import QPushButton

        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )
        from freecad.diff_wb.ui.views.models import HistorySelection

        # Clear any previous state
        widget.clear_doc_diffs()

        # Set selection to WORKING_TREE
        widget.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                    stage_button_enabled=True,
                )
            ]
        )

        # Should have Stage button - check by looking at actual tree item containers
        has_stage_button = False
        for i in range(widget.tree_widget.topLevelItemCount()):
            item = widget.tree_widget.topLevelItem(i)
            container = widget.tree_widget.itemWidget(item, 0)
            if container is not None:
                buttons = container.findChildren(QPushButton)
                if any(button.text() == "+ Stage" for button in buttons):
                    has_stage_button = True
                    break
        assert has_stage_button

    def test_stage_buttons_hidden_when_not_working_tree(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Stage buttons are hidden when selection is not WORKING_TREE."""
        from PySide6.QtWidgets import QPushButton

        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )
        from freecad.diff_wb.ui.views.models import HistorySelection

        # Clear any previous state
        widget.clear_doc_diffs()

        # Set selection to COMMIT (not WORKING_TREE)
        widget.set_current_history_selection(HistorySelection(item_kind="COMMIT", commit_hash="abc123"))

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                    stage_button_enabled=True,
                )
            ]
        )

        # Should NOT have Stage button - check by looking at actual tree item containers
        # (findChildren may find orphaned buttons from previous tests)
        has_stage_button = False
        for i in range(widget.tree_widget.topLevelItemCount()):
            item = widget.tree_widget.topLevelItem(i)
            container = widget.tree_widget.itemWidget(item, 0)
            if container is not None:
                buttons = container.findChildren(QPushButton)
                if any(button.text() == "+ Stage" for button in buttons):
                    has_stage_button = True
                    break
        assert not has_stage_button

    def test_show_doc_diffs_with_empty_list_clears_tree(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_doc_diffs() clears tree when given empty list."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )

        # Given: Tree has some items
        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                )
            ]
        )
        assert widget.tree_widget.topLevelItemCount() == 1

        # When: Show empty list
        widget.show_doc_diffs([])

        # Then: Tree is cleared
        assert widget.tree_widget.topLevelItemCount() == 0


class TestCallbackWiring:
    """Tests for callback wiring methods."""

    def test_set_add_button_callback_invokes_callback(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_add_button_callback() invokes callback when triggered."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )
        from freecad.diff_wb.ui.views.models import HistorySelection

        captured: list[str] = []

        def callback(git_path: str) -> None:
            captured.append(git_path)

        widget.clear_doc_diffs()
        widget.set_add_button_callback(callback)
        widget.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                    stage_button_enabled=True,
                )
            ]
        )

        # Find and click the "+ Stage" button - look in tree item containers
        from PySide6.QtWidgets import QPushButton

        stage_button = None
        for i in range(widget.tree_widget.topLevelItemCount()):
            item = widget.tree_widget.topLevelItem(i)
            container = widget.tree_widget.itemWidget(item, 0)
            if container is not None:
                buttons = container.findChildren(QPushButton)
                for button in buttons:
                    if button.text() == "+ Stage":
                        stage_button = button
                        break
            if stage_button is not None:
                break

        assert stage_button is not None
        stage_button.click()

        assert captured == ["parts/A.FCStd"]

    def test_set_stage_all_callback_invokes_callback(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_stage_all_callback() invokes callback when triggered."""
        captured: list[bool] = []

        def callback() -> None:
            captured.append(True)

        widget.set_stage_all_callback(callback)
        widget._on_stage_all_clicked()

        assert captured == [True]

    def test_set_node_selection_callback_receives_git_path_and_node_path(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_node_selection_callback() receives (git_path, node_path) for child item clicks."""
        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )

        captured: list[tuple[str, str]] = []

        def callback(git_path: str, node_path: str) -> None:
            captured.append((git_path, node_path))

        widget.set_node_selection_callback(callback)
        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body",
                            type_id="PartDesign::Body",
                            label="Body",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                )
            ]
        )

        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        child_item = root_item.child(0)
        assert child_item is not None

        widget._on_tree_item_clicked(child_item, 0)

        assert captured == [("parts/A.FCStd", "Body")]


class TestDocumentDiffTreeWidgetIndependence:
    """Tests for DocumentDiffTreeWidget independence from property widget."""

    def test_widget_clears_document_diffs_without_property_widget(self, widget) -> None:  # type: ignore[no-untyped-def]
        """DocumentDiffTreeWidget does not need a property widget reference to clear document diffs."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # Given: Tree with items
        widget.show_doc_diff(
            [
                NodePresentation(
                    path="Body/Pad",
                    type_id="PartDesign::Pad",
                    label="Pad",
                    state=DiffState.MODIFIED,
                    has_changes=True,
                    children=[],
                )
            ]
        )
        assert widget.tree_widget.topLevelItemCount() == 1

        # When: Clear doc diffs
        widget.clear_doc_diffs()

        # Then: Tree is cleared
        assert widget.tree_widget.topLevelItemCount() == 0

    def test_widget_renders_document_diffs_without_property_widget(self, widget) -> None:  # type: ignore[no-untyped-def]
        """DocumentDiffTreeWidget does not need a property widget reference to render document diffs."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        # This test simply verifies that show_doc_diff works without any property widget
        widget.show_doc_diff(
            [
                NodePresentation(
                    path="Body/Pad",
                    type_id="PartDesign::Pad",
                    label="Pad",
                    state=DiffState.MODIFIED,
                    has_changes=True,
                    children=[],
                )
            ]
        )

        assert widget.tree_widget.topLevelItemCount() == 1
        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        assert root_item.childCount() == 1


class TestShowSummary:
    """Tests for show_summary() method."""

    def test_show_summary_with_zero_changes(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_summary(0) displays 'No changes'."""
        widget.show_summary(0)
        assert widget._changed_label.text() == "No changes"

    def test_show_summary_with_positive_count(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_summary(n) displays 'Changed: n' for n > 0."""
        widget.show_summary(3)
        assert widget._changed_label.text() == "Changed: 3"


class TestSetStageAllButtonVisibilityAndEnabled:
    """Tests for stage all button visibility and enabled state."""

    def test_set_stage_all_button_visible(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_stage_all_button_visible() controls button visibility."""
        widget.set_stage_all_button_visible(True)
        assert not widget._stage_all_button.isHidden()

        widget.set_stage_all_button_visible(False)
        assert widget._stage_all_button.isHidden()

    def test_set_stage_all_button_enabled(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_stage_all_button_enabled() controls button enabled state."""
        widget.set_stage_all_button_enabled(True)
        assert widget._stage_all_button.isEnabled()

        widget.set_stage_all_button_enabled(False)
        assert not widget._stage_all_button.isEnabled()


class TestCollapseTreeItem:
    """Tests for collapse_tree_item() method."""

    def test_collapse_tree_item_collapses_root(self, widget) -> None:  # type: ignore[no-untyped-def]
        """collapse_tree_item() collapses the root item for given git_path."""
        from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation

        widget.show_doc_diff(
            [
                NodePresentation(
                    path="Body/Pad",
                    type_id="PartDesign::Pad",
                    label="Pad",
                    state=DiffState.MODIFIED,
                    has_changes=True,
                    children=[],
                )
            ],
            git_path="parts/A.FCStd",
        )

        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        root_item.setExpanded(True)
        assert root_item.isExpanded()

        widget.collapse_tree_item("parts/A.FCStd")
        assert not root_item.isExpanded()


class TestSetStageButtonEnabled:
    """Tests for set_stage_button_enabled() method."""

    def test_set_stage_button_enabled_updates_button(self, widget) -> None:  # type: ignore[no-untyped-def]
        """set_stage_button_enabled() updates the stage button for given git_path."""
        from PySide6.QtWidgets import QPushButton

        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            NodePresentation,
        )
        from freecad.diff_wb.ui.views.models import HistorySelection

        widget.clear_doc_diffs()
        widget.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[
                        NodePresentation(
                            path="Body/Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            state=DiffState.MODIFIED,
                            has_changes=True,
                            children=[],
                        )
                    ],
                    git_path="parts/A.FCStd",
                    indicators=[],
                    stage_button_enabled=True,
                )
            ]
        )

        # Find stage button in tree item containers

        stage_button = None
        for i in range(widget.tree_widget.topLevelItemCount()):
            item = widget.tree_widget.topLevelItem(i)
            container = widget.tree_widget.itemWidget(item, 0)
            if container is not None:
                buttons = container.findChildren(QPushButton)
                for button in buttons:
                    if button.text() == "+ Stage":
                        stage_button = button
                        break
            if stage_button is not None:
                break

        assert stage_button is not None
        assert stage_button.isEnabled()

        widget.set_stage_button_enabled("parts/A.FCStd", False)
        assert not stage_button.isEnabled()


class TestWarningDisplay:
    """Tests for warning indicator rendering in show_doc_diffs()."""

    def test_show_doc_diffs_warning_is_tooltip_only(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Warnings are exposed via tooltip and not as inline orange text labels."""
        from PySide6.QtWidgets import QLabel

        from freecad.diff_wb.ui.presenters.presentation_models import (
            DiffTreePresentation,
            OldSnapshotMissingIndicator,
        )

        widget.show_doc_diffs(
            [
                DiffTreePresentation(
                    nodes=[],
                    git_path="parts/A.FCStd",
                    indicators=[OldSnapshotMissingIndicator()],
                )
            ]
        )

        root_item = widget.tree_widget.topLevelItem(0)
        assert root_item is not None
        container = widget.tree_widget.itemWidget(root_item, 0)
        assert container is not None

        labels = container.findChildren(QLabel)
        assert labels
        assert not any(label.text() == "Cannot find old snapshot. Diff cannot be generated." for label in labels)

        # Warning tooltip is shown on the icon label when icon assets are available.
        # In headless/unit environments icon loading may be unavailable, so keep this
        # assertion conditional.
        tooltip_values = [label.toolTip() for label in labels]
        if any(tooltip_values):
            assert "Cannot find old snapshot. Diff cannot be generated." in tooltip_values
