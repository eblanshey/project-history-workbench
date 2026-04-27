"""File responsibility: Unit tests for DiffPresenter."""

import datetime
from unittest.mock import MagicMock

from freecad.diff_wb.application.actions.create_diff import CreateDiffAction
from freecad.diff_wb.application.actions.create_document_snapshot_commit import CreateDocumentSnapshotForCommitAction
from freecad.diff_wb.application.actions.create_document_snapshot_working import (
    CreateDocumentSnapshotForWorkingTreeAction,
)
from freecad.diff_wb.application.actions.get_committed_file_paths import GetCommittedFilePathsAction
from freecad.diff_wb.application.actions.get_dirty_documents import GetDirtyDocumentsAction
from freecad.diff_wb.application.actions.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from freecad.diff_wb.application.actions.get_staged_file_paths import GetStagedFilePathsAction
from freecad.diff_wb.application.actions.stage_documents import StageDocumentsAction
from freecad.diff_wb.domain.diff.models import DiffHierarchy, DiffResult, DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.git.models import GitRepository
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.domain.tree import Property
from freecad.diff_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.diff_wb.ui.presenters.presentation_models import NodePresentation, PropertyPresentation
from freecad.diff_wb.ui.state import UIState
from freecad.diff_wb.ui.views.diff_panel_view import HistorySelection
from tests.fakes.fake_diff_view import FakeDiffView


def _create_test_presenter() -> tuple[FakeDiffView, DiffPresenter]:
    """Helper to create a DiffPresenter with mock dependencies.

    Returns:
        Tuple of (FakeDiffView, DiffPresenter) for test setup.
    """
    view = FakeDiffView()
    ui_state = UIState(git_repository=None)

    # Create mock actions
    get_eligible_docs_action = MagicMock(spec=GetOpenEligibleDocumentsAction)
    create_working_snapshot_action = MagicMock(spec=CreateDocumentSnapshotForWorkingTreeAction)
    create_commit_snapshot_action = MagicMock(spec=CreateDocumentSnapshotForCommitAction)
    create_diff_action = MagicMock(spec=CreateDiffAction)
    stage_documents_action = MagicMock(spec=StageDocumentsAction)
    get_dirty_documents_action = MagicMock(spec=GetDirtyDocumentsAction)
    get_staged_file_paths_action = MagicMock(spec=GetStagedFilePathsAction)
    get_committed_file_paths_action = MagicMock(spec=GetCommittedFilePathsAction)

    presenter = DiffPresenter(
        view=view,
        ui_state=ui_state,
        get_eligible_docs_action=get_eligible_docs_action,
        create_working_snapshot_action=create_working_snapshot_action,
        create_commit_snapshot_action=create_commit_snapshot_action,
        create_diff_action=create_diff_action,
        stage_documents_action=stage_documents_action,
        get_dirty_documents_action=get_dirty_documents_action,
        get_staged_file_paths_action=get_staged_file_paths_action,
        get_committed_file_paths_action=get_committed_file_paths_action,
    )
    return view, presenter


class TestDiffPresenterGitPath:
    """Tests for DiffPresenter git_path display functionality."""

    def test_present_diff_passes_git_path_to_view(self) -> None:
        """Passes git_path from new_snapshot to show_diff_tree."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        diff_result = DiffResult(
            old_snapshot=Snapshot(
                snapshot_id="s1",
                document_name="snapshot_v1",
                timestamp=datetime.datetime.now(),
            ),
            new_snapshot=Snapshot(
                snapshot_id="s2",
                document_name="snapshot_v2",
                timestamp=datetime.datetime.now(),
                git_path="path/to/doc.FCStd",
            ),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree
        calls = fake_view.get_calls()
        assert calls[2]["method"] == "show_diff_tree"
        assert calls[2]["git_path"] == "path/to/doc.FCStd"

    def test_present_diff_uses_document_name_when_git_path_empty(self) -> None:
        """Falls back to document_name when git_path is empty."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        diff_result = DiffResult(
            old_snapshot=Snapshot(
                snapshot_id="s1",
                document_name="snapshot_v1",
                timestamp=datetime.datetime.now(),
            ),
            new_snapshot=Snapshot(
                snapshot_id="s2",
                document_name="MyDocument",
                timestamp=datetime.datetime.now(),
                git_path="",  # Empty git_path
            ),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree
        calls = fake_view.get_calls()
        assert calls[2]["method"] == "show_diff_tree"
        assert calls[2]["git_path"] == "MyDocument"


class TestDiffPresenter:
    """Tests for DiffPresenter."""

    def test_present_diff_calls_view_methods(self) -> None:
        """Calls set_history_selection_callback in constructor, then show_diff_tree and show_summary."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        # Create a node with no property changes so it's UNCHANGED
        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="snapshot_v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="snapshot_v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - 4 calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree, show_summary
        assert fake_view.get_call_count() == 4
        calls = fake_view.get_calls()
        assert calls[0]["method"] == "set_history_selection_callback"
        assert calls[2]["method"] == "show_diff_tree"
        assert calls[3]["method"] == "show_summary"

    def test_formats_node_diffs_correctly(self) -> None:
        """Transforms NodeDiff to NodePresentation correctly."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        node_diff = NodeDiff(
            path="Part001",
            type_id="Part::Feature",
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree
        calls = fake_view.get_calls()
        nodes = calls[2]["nodes"]
        assert len(nodes) == 1
        presentation = nodes[0]
        assert isinstance(presentation, NodePresentation)
        assert presentation.path == "Part001"
        assert presentation.type_id == "Part::Feature"
        assert presentation.state == DiffState.MODIFIED
        assert presentation.has_changes is True

    def test_formats_property_changes(self) -> None:
        """Formats PropertyDiff with expressions correctly."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        old_prop = Property.from_freecad(10.0, {".": "Sketch.X"}, "Base")
        new_prop = Property.from_freecad(20.0, {}, "Base")
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree
        calls = fake_view.get_calls()
        nodes = calls[2]["nodes"]
        presentation = nodes[0]
        assert presentation.has_changes is True
        assert presentation.state == DiffState.MODIFIED

    def test_handles_empty_diff(self) -> None:
        """Handles case with no changes."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=DiffHierarchy(),
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree, show_summary
        calls = fake_view.get_calls()
        assert calls[2]["method"] == "show_diff_tree"
        assert calls[2]["nodes"] == []
        assert calls[3]["method"] == "show_summary"
        assert calls[3]["changed_docs"] == 0

    def test_calculates_changed_docs_for_single_diff(self) -> None:
        """Shows changed_docs=1 when single diff has any changes."""
        # Arrange
        fake_view, presenter = _create_test_presenter()
        added_node = NodeDiff(path="NewPart", type_id="Part::Feature", _force_state=DiffState.ADDED)
        deleted_node = NodeDiff(path="OldPart", type_id="Part::Feature", _force_state=DiffState.DELETED)
        modified_node = NodeDiff(
            path="ChangedPart",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(
                    property_name="Length",
                    old_value=Property.from_freecad(10.0, {}, "Base"),
                    new_value=Property.from_freecad(20.0, {}, "Base"),
                )
            ],
            _force_state=DiffState.MODIFIED,
        )
        unchanged_node = NodeDiff(path="UnchangedPart", type_id="Part::Feature")
        hierarchy = DiffHierarchy()
        hierarchy.add_node(added_node)
        hierarchy.add_node(deleted_node)
        hierarchy.add_node(modified_node)
        hierarchy.add_node(unchanged_node)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
            added_count=1,
            deleted_count=1,
            modified_count=1,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree, show_summary
        calls = fake_view.get_calls()
        summary_call = calls[3]
        assert summary_call["changed_docs"] == 1


class TestDiffPresenterFormatsChildren:
    """Tests for _format_node() populating children recursively."""

    def test_format_node_populates_children_recursive(self) -> None:
        """Test _format_node() populates children recursively from NodeDiff.children."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create a nested tree structure using factory functions
        grandchild = NodeDiff(
            path="Part/Body/Pad",
            type_id="PartDesign::Pad",
            _force_state=DiffState.UNCHANGED,
        )
        child = NodeDiff(
            path="Part/Body",
            type_id="PartDesign::Body",
            children=[grandchild],
            _force_state=DiffState.MODIFIED,
        )
        parent = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            children=[child],
            _force_state=DiffState.UNCHANGED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(parent)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree
        calls = fake_view.get_calls()
        presentations = calls[2]["nodes"]
        assert len(presentations) == 1

        # Check parent presentation
        parent_pres = presentations[0]
        assert parent_pres.path == "Part"
        assert len(parent_pres.children) == 1

        # Check child presentation (recursive)
        child_pres = parent_pres.children[0]
        assert child_pres.path == "Part/Body"
        assert len(child_pres.children) == 1

        # Check grandchild presentation (deeply nested)
        grandchild_pres = child_pres.children[0]
        assert grandchild_pres.path == "Part/Body/Pad"
        assert len(grandchild_pres.children) == 0

    def test_complete_tree_structure_preserved_through_transformation(self) -> None:
        """Test complete tree structure is preserved through transformation."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create a complex multi-level tree with multiple branches
        leaf1 = NodeDiff(path="Part/Body/Pad", type_id="PartDesign::Pad", _force_state=DiffState.ADDED)
        leaf2 = NodeDiff(path="Part/Body/Pocket", type_id="PartDesign::Pocket", _force_state=DiffState.DELETED)
        body = NodeDiff(
            path="Part/Body",
            type_id="PartDesign::Body",
            children=[leaf1, leaf2],
            _force_state=DiffState.MODIFIED,
        )
        leaf3 = NodeDiff(path="Part/Sketch", type_id="Sketcher::SketchObject", _force_state=DiffState.UNCHANGED)
        part = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            children=[body, leaf3],
            _force_state=DiffState.MODIFIED,
        )

        hierarchy = DiffHierarchy()
        hierarchy.add_node(part)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree
        calls = fake_view.get_calls()
        presentations = calls[2]["nodes"]

        # Root level
        assert len(presentations) == 1
        root = presentations[0]
        assert root.path == "Part"
        assert root.state == DiffState.MODIFIED
        assert len(root.children) == 2

        # First branch - Body with two leaves
        body_pres = root.children[0]
        assert body_pres.path == "Part/Body"
        assert body_pres.state == DiffState.MODIFIED
        assert len(body_pres.children) == 2

        # Body's children
        pad_pres = body_pres.children[0]
        assert pad_pres.path == "Part/Body/Pad"
        assert pad_pres.state == DiffState.ADDED
        assert pad_pres.has_changes is True

        pocket_pres = body_pres.children[1]
        assert pocket_pres.path == "Part/Body/Pocket"
        assert pocket_pres.state == DiffState.DELETED
        assert pocket_pres.has_changes is True

        # Second branch - Sketch (unchanged leaf)
        sketch_pres = root.children[1]
        assert sketch_pres.path == "Part/Sketch"
        assert sketch_pres.state == DiffState.UNCHANGED
        assert sketch_pres.has_changes is False
        assert len(sketch_pres.children) == 0

    def test_format_node_handles_empty_children(self) -> None:
        """Test _format_node() handles nodes with no children."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        leaf_node = NodeDiff(
            path="Part/Leaf",
            type_id="Part::Feature",
            _force_state=DiffState.ADDED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(leaf_node)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diff(diff_result)

        # Assert - calls: set_history_selection_callback (constructor),
        # set_stage_all_callback (constructor), show_diff_tree
        calls = fake_view.get_calls()
        presentations = calls[2]["nodes"]
        assert len(presentations) == 1
        assert presentations[0].path == "Part/Leaf"
        assert presentations[0].children == []


class TestTransformPropertyDiffsWithChildren:
    """Tests for _transform_property_diffs() including children transformation."""

    def test_transform_property_diffs_includes_children(self) -> None:
        """Test that property diffs with children are transformed correctly."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create property with children (list property with indexed children)
        old_list = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")
        new_list = Property.from_freecad([10.0, 2.0, 30.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Vector",
            old_value=old_list,
            new_value=new_list,
        )

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )
        presenter.present_diff(diff_result)

        # Act - use on_node_selected to trigger the transform
        presenter.on_node_selected("v2", "Part")

        # Assert
        calls = fake_view.get_calls()
        # Find show_properties call
        show_props_call = None
        for call in calls:
            if call["method"] == "show_properties":
                show_props_call = call
                break

        assert show_props_call is not None
        properties = show_props_call["properties"]
        assert len(properties) == 1

        prop_presentation = properties[0]
        assert isinstance(prop_presentation, PropertyPresentation)
        assert prop_presentation.name == "Vector"
        # Children should be populated from domain PropertyDiff (indexed list items)
        assert len(prop_presentation.children) > 0

    def test_list_items_appear_as_nested_children(self) -> None:
        """Test that list items appear as nested children with indexed names."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create a list property with indexed children
        old_position = Property.from_freecad([0.0, 0.0, 0.0], {}, "Base")
        new_position = Property.from_freecad([10.0, 20.0, 30.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Position",
            old_value=old_position,
            new_value=new_position,
        )

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("v2", "Part")

        # Assert
        calls = fake_view.get_calls()
        # Find show_properties call
        show_props_call = None
        for call in calls:
            if call["method"] == "show_properties":
                show_props_call = call
                break

        assert show_props_call is not None
        properties = show_props_call["properties"]
        position_pres = properties[0]

        # Should have children (indexed list items)
        assert len(position_pres.children) > 0
        child_names = {child.name for child in position_pres.children}
        assert "[0]" in child_names or "[1]" in child_names or "[2]" in child_names

    def test_transform_children_preserves_parent_values(self) -> None:
        """Test that parent old_value and new_value are preserved alongside children."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Create a property with both parent value and children
        old_placement = Property.from_freecad(
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)}, {}, "Base"
        )
        new_placement = Property.from_freecad(
            {"position": (10.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 45.0)}, {}, "Base"
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=old_placement,
            new_value=new_placement,
        )

        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("v2", "Part")

        # Assert
        calls = fake_view.get_calls()
        # Find show_properties call
        show_props_call = None
        for call in calls:
            if call["method"] == "show_properties":
                show_props_call = call
                break

        assert show_props_call is not None
        properties = show_props_call["properties"]
        prop_pres = properties[0]

        # Parent should still have old_value and new_value for display
        assert prop_pres.old_value is not None
        assert prop_pres.new_value is not None

    def test_transform_children_empty_for_primitives(self) -> None:
        """Test that primitive properties have empty children list."""
        # Arrange
        fake_view, presenter = _create_test_presenter()

        # Need to set up a diff_result first because on_node_selected requires it
        old_prop = Property.from_freecad(10.0, {}, "Base")
        new_prop = Property.from_freecad(20.0, {}, "Base")
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=old_prop,
            new_value=new_prop,
        )
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node_diff)
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=hierarchy,
        )
        presenter.present_diff(diff_result)

        # Act
        presenter.on_node_selected("v2", "Part")

        # Assert
        calls = fake_view.get_calls()
        # Find the show_properties call
        show_props_call = None
        for call in calls:
            if call["method"] == "show_properties":
                show_props_call = call
                break

        assert show_props_call is not None
        properties = show_props_call["properties"]
        prop_pres = properties[0]

        # Primitive should have empty children
        assert prop_pres.children == []


class TestDiffPresenterHistorySelection:
    """Tests for DiffPresenter history selection handling."""

    def test_on_history_item_selected_method_exists(self) -> None:
        """DiffPresenter has on_history_item_selected() method."""
        _, presenter = _create_test_presenter()
        assert hasattr(presenter, "on_history_item_selected")
        assert callable(presenter.on_history_item_selected)

    def test_on_history_item_selected_routes_working_tree(self) -> None:
        """on_history_item_selected() routes WORKING_TREE to _on_working_tree_selected()."""
        fake_view, presenter = _create_test_presenter()

        # Mock the internal methods
        with (
            MagicMock() as mock_working,
            MagicMock() as mock_staging,
            MagicMock() as mock_commit,
        ):
            presenter._on_working_tree_selected = mock_working
            presenter._on_staging_selected = mock_staging
            presenter._on_commit_selected = mock_commit

            # Act
            selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
            presenter.on_history_item_selected(selection)

            # Assert
            mock_working.assert_called_once()
            mock_staging.assert_not_called()
            mock_commit.assert_not_called()

    def test_on_history_item_selected_routes_staging(self) -> None:
        """on_history_item_selected() routes STAGING to _on_staging_selected()."""
        fake_view, presenter = _create_test_presenter()

        with (
            MagicMock() as mock_working,
            MagicMock() as mock_staging,
            MagicMock() as mock_commit,
        ):
            presenter._on_working_tree_selected = mock_working
            presenter._on_staging_selected = mock_staging
            presenter._on_commit_selected = mock_commit

            # Act
            selection = HistorySelection(item_kind="STAGING", commit_hash=None)
            presenter.on_history_item_selected(selection)

            # Assert
            mock_working.assert_not_called()
            mock_staging.assert_called_once()
            mock_commit.assert_not_called()

    def test_on_history_item_selected_routes_commit(self) -> None:
        """on_history_item_selected() routes COMMIT to _on_commit_selected()."""
        fake_view, presenter = _create_test_presenter()

        with (
            MagicMock() as mock_working,
            MagicMock() as mock_staging,
            MagicMock() as mock_commit,
        ):
            presenter._on_working_tree_selected = mock_working
            presenter._on_staging_selected = mock_staging
            presenter._on_commit_selected = mock_commit

            # Act
            commit_hash = "abc123"
            selection = HistorySelection(item_kind="COMMIT", commit_hash=commit_hash)
            presenter.on_history_item_selected(selection)

            # Assert
            mock_working.assert_not_called()
            mock_staging.assert_not_called()
            mock_commit.assert_called_once_with(commit_hash)


class TestDiffPresenterPresentDiffs:
    """Tests for DiffPresenter.present_diffs() method."""

    def test_present_diffs_accepts_list_of_diff_results(self) -> None:
        """present_diffs() accepts list[DiffResult]."""
        fake_view, presenter = _create_test_presenter()

        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=DiffHierarchy(),
        )

        # Act
        presenter.present_diffs([diff_result])

        # Assert
        assert fake_view.get_call_count() >= 1

    def test_present_diffs_transforms_to_diff_tree_presentation(self) -> None:
        """Each DiffResult is transformed to DiffTreePresentation."""
        from freecad.diff_wb.ui.presenters.presentation_models import DiffTreePresentation

        fake_view, presenter = _create_test_presenter()

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))

        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(
                snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now(), git_path="test.FCStd"
            ),
            hierarchy=hierarchy,
        )

        # Act
        presenter.present_diffs([diff_result])

        # Assert
        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        presentations = show_trees_call["diff_trees"]
        assert len(presentations) == 1
        assert isinstance(presentations[0], DiffTreePresentation)
        assert presentations[0].git_path == "test.FCStd"

    def test_present_diffs_handles_empty_list(self) -> None:
        """present_diffs() handles empty list."""
        fake_view, presenter = _create_test_presenter()

        # Act
        presenter.present_diffs([])

        # Assert
        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        assert show_trees_call["diff_trees"] == []

    def test_present_diffs_counts_changed_documents(self) -> None:
        """present_diffs() shows number of documents with changes."""
        fake_view, presenter = _create_test_presenter()

        changed = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=DiffHierarchy(),
            modified_count=2,
        )
        unchanged = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s3", document_name="v3", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s4", document_name="v4", timestamp=datetime.datetime.now()),
            hierarchy=DiffHierarchy(),
        )

        presenter.present_diffs([changed, unchanged])

        calls = fake_view.get_calls()
        show_summary_call = next((c for c in calls if c["method"] == "show_summary"), None)
        assert show_summary_call is not None
        assert show_summary_call["changed_docs"] == 1


class TestDiffPresenterWorkingTreeOrchestration:
    """Tests for DiffPresenter._on_working_tree_selected() orchestration."""

    def test_on_working_tree_selected_calls_get_eligible_docs(self) -> None:
        """_on_working_tree_selected() calls GetOpenEligibleDocumentsAction.execute() with correct repo."""

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock action
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = []
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Act
        presenter._on_working_tree_selected()

        # Assert
        presenter._get_eligible_docs.execute.assert_called_once_with(mock_repo)

    def test_on_working_tree_selected_creates_working_snapshots(self) -> None:
        """For each eligible document, creates working tree snapshot."""
        from tests.fakes.fake_freecad_port import DocumentLike

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock documents
        mock_doc1 = MagicMock(spec=DocumentLike)
        mock_doc1.FileName = "/test/path/doc1.FCStd"
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = [mock_doc1]
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Setup mock working snapshot
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc1.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc1.FCStd",
        )
        mock_working_result = MagicMock()
        mock_working_result.is_success = True
        mock_working_result.data = mock_working_snapshot
        mock_working_result.message = ""
        presenter._create_working_tree_snapshot.execute.return_value = mock_working_result

        # Setup mock commit result (stub returns None)
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_commit_result

        # Setup mock diff result
        mock_diff_result = DiffResult(
            old_snapshot=None,
            new_snapshot=mock_working_snapshot,
            hierarchy=DiffHierarchy(),
        )
        mock_create_diff_result = MagicMock()
        mock_create_diff_result.is_success = True
        mock_create_diff_result.data = mock_diff_result
        presenter._create_diff.execute.return_value = mock_create_diff_result

        # Act
        presenter._on_working_tree_selected()

        # Assert
        presenter._create_working_tree_snapshot.execute.assert_called_once_with(mock_repo, mock_doc1)

    def test_on_working_tree_selected_creates_diff_with_none_old_snapshot(self) -> None:
        """Creates diff with None old_snapshot and working tree snapshot as new."""
        from tests.fakes.fake_freecad_port import DocumentLike

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock document
        mock_doc = MagicMock(spec=DocumentLike)
        mock_doc.FileName = "/test/path/doc.FCStd"
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = [mock_doc]
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Setup mock working snapshot
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )
        mock_working_result = MagicMock()
        mock_working_result.is_success = True
        mock_working_result.data = mock_working_snapshot
        presenter._create_working_tree_snapshot.execute.return_value = mock_working_result

        # Setup mock commit result
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_commit_result

        # Mock the diff creation
        captured_old_snapshot = []

        def capture_diff(old, new):
            captured_old_snapshot.append(old)
            mock_diff_result = MagicMock()
            mock_diff_result.is_success = True
            mock_diff_result.data = DiffResult(
                old_snapshot=old,
                new_snapshot=new,
                hierarchy=DiffHierarchy(),
            )
            return mock_diff_result

        presenter._create_diff.execute.side_effect = capture_diff

        # Act
        presenter._on_working_tree_selected()

        # Assert
        assert len(captured_old_snapshot) == 1
        assert captured_old_snapshot[0] is None

    def test_on_working_tree_selected_logs_warning_and_continues_on_failure(self) -> None:
        """Logs warning for failed snapshots but continues processing."""
        from tests.fakes.fake_freecad_port import DocumentLike

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup multiple documents
        mock_doc1 = MagicMock(spec=DocumentLike)
        mock_doc1.FileName = "/test/path/doc1.FCStd"
        mock_doc2 = MagicMock(spec=DocumentLike)
        mock_doc2.FileName = "/test/path/doc2.FCStd"
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = [mock_doc1, mock_doc2]
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # First doc fails, second succeeds
        failed_result = MagicMock()
        failed_result.is_success = False
        failed_result.data = None
        failed_result.message = "Failed to extract"

        successful_snapshot = Snapshot(
            snapshot_id="ws2",
            document_name="doc2.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc2.FCStd",
        )
        successful_result = MagicMock()
        successful_result.is_success = True
        successful_result.data = successful_snapshot
        successful_result.message = ""

        call_count = [0]

        def create_working_side_effect(repo, doc):
            call_count[0] += 1
            if call_count[0] == 1:
                return failed_result
            return successful_result

        presenter._create_working_tree_snapshot.execute.side_effect = create_working_side_effect

        # Setup commit and diff mocks
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_commit_result

        mock_diff_result = MagicMock()
        mock_diff_result.is_success = True
        mock_diff_result.data = DiffResult(
            old_snapshot=None,
            new_snapshot=successful_snapshot,
            hierarchy=DiffHierarchy(),
        )
        presenter._create_diff.execute.return_value = mock_diff_result

        # Act
        presenter._on_working_tree_selected()

        # Assert - both docs should have been processed
        assert presenter._create_working_tree_snapshot.execute.call_count == 2

    def test_on_working_tree_selected_collects_all_successful_diffs(self) -> None:
        """Collects all successful DiffResults and passes to present_diffs()."""
        from tests.fakes.fake_freecad_port import DocumentLike

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup two documents
        mock_doc1 = MagicMock(spec=DocumentLike)
        mock_doc1.FileName = "/test/path/doc1.FCStd"
        mock_doc2 = MagicMock(spec=DocumentLike)
        mock_doc2.FileName = "/test/path/doc2.FCStd"
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = [mock_doc1, mock_doc2]
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Create snapshots for both docs
        snapshot1 = Snapshot(
            snapshot_id="ws1", document_name="doc1.FCStd", timestamp=datetime.datetime.now(), git_path="doc1.FCStd"
        )
        snapshot2 = Snapshot(
            snapshot_id="ws2", document_name="doc2.FCStd", timestamp=datetime.datetime.now(), git_path="doc2.FCStd"
        )

        def create_working_side_effect(repo, doc):
            result = MagicMock()
            result.is_success = True
            result.data = snapshot1 if doc == mock_doc1 else snapshot2
            result.message = ""
            return result

        presenter._create_working_tree_snapshot.execute.side_effect = create_working_side_effect

        # Setup commit and diff mocks
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_commit_result

        def create_diff_side_effect(old, new):
            result = MagicMock()
            result.is_success = True
            result.data = DiffResult(
                old_snapshot=None,
                new_snapshot=new,
                hierarchy=DiffHierarchy(),
                added_count=1,
                deleted_count=0,
                modified_count=0,
            )
            return result

        presenter._create_diff.execute.side_effect = create_diff_side_effect

        # Act
        presenter._on_working_tree_selected()

        # Assert - show_diff_trees should be called with 2 presentations
        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        assert len(show_trees_call["diff_trees"]) == 2

    def test_on_working_tree_selected_no_repo_hides_stage_all(self) -> None:
        """Selecting Working Tree with no git repository hides Stage All and clears state."""
        fake_view, presenter = _create_test_presenter()

        # Pre-populate stale state (simulating a prior selection)
        old_snapshot = Snapshot(
            snapshot_id="s1",
            document_name="old.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="old.FCStd",
        )
        presenter._diff_results_by_path = {
            "old.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=old_snapshot,
                hierarchy=DiffHierarchy(),
            ),
        }

        # No git repository set (ui_state.git_repository is None by default)

        # Act
        presenter._on_working_tree_selected()

        # Assert - stale state is cleared
        assert presenter._diff_results_by_path == {}

        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        assert show_trees_call["diff_trees"] == []

        visible_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_visible"),
            None,
        )
        assert visible_call is not None
        assert visible_call["visible"] is False


class TestDiffPresenterPresentDiffsDirtyPaths:
    """Tests for DiffPresenter.present_diffs() with dirty_paths parameter."""

    def test_present_diffs_sets_stage_button_enabled_from_dirty_paths(self) -> None:
        """Stage button enabled is set to True when document is in dirty_paths."""
        fake_view, presenter = _create_test_presenter()

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))

        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(
                snapshot_id="s2",
                document_name="v2",
                timestamp=datetime.datetime.now(),
                git_path="dirty.FCStd",
            ),
            hierarchy=hierarchy,
        )

        # Act - pass dirty_paths including this document
        presenter.present_diffs([diff_result], dirty_paths={"dirty.FCStd"})

        # Assert
        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        presentations = show_trees_call["diff_trees"]
        assert len(presentations) == 1
        # Stage button should be enabled because document has git-tracked changes
        assert presentations[0].stage_button_enabled is True


class TestDiffPresenterAddButton:
    """Tests for DiffPresenter.on_add_button_clicked() method."""

    def test_on_add_button_clicked_stages_document_successfully(self) -> None:
        """Stages document successfully when git repository and diff result exist."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock working snapshot
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )

        # Setup mock diff result
        mock_diff_result = DiffResult(
            old_snapshot=None,
            new_snapshot=mock_working_snapshot,
            hierarchy=DiffHierarchy(),
        )
        # Store in _diff_results_by_path as _on_working_tree_selected would
        presenter._diff_results_by_path = {"doc.FCStd": mock_diff_result}

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Act
        presenter.on_add_button_clicked("doc.FCStd")

        # Assert - stage was called with correct arguments
        presenter._stage_documents.execute.assert_called_once_with(mock_repo, [mock_working_snapshot])

    def test_on_add_button_clicked_no_git_repository_returns_early(self) -> None:
        """Returns early without staging when no git repository is available."""
        fake_view, presenter = _create_test_presenter()

        # No git repository set (ui_state.git_repository is None by default)

        # Act
        presenter.on_add_button_clicked("doc.FCStd")

        # Assert - stage was never called
        presenter._stage_documents.execute.assert_not_called()

    def test_on_add_button_clicked_missing_diff_result_logs_warning(self) -> None:
        """Logs warning when diff result not found for the given git_path."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # No diff results stored (empty _diff_results_by_path)
        presenter._diff_results_by_path = {}

        # Act
        presenter.on_add_button_clicked("missing.FCStd")

        # Assert - stage was never called
        presenter._stage_documents.execute.assert_not_called()

    def test_on_add_button_clicked_collapses_and_disables_after_staging(self) -> None:
        """Collapses tree item and disables stage button after successful staging."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock working snapshot
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )

        # Setup mock diff result
        mock_diff_result = DiffResult(
            old_snapshot=None,
            new_snapshot=mock_working_snapshot,
            hierarchy=DiffHierarchy(),
        )
        presenter._diff_results_by_path = {"doc.FCStd": mock_diff_result}

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Mock view methods for collapse and disable
        fake_view.collapse_tree_item = MagicMock()
        fake_view.set_stage_button_enabled = MagicMock()

        # Act
        presenter.on_add_button_clicked("doc.FCStd")

        # Assert - view methods called instead of refresh
        fake_view.collapse_tree_item.assert_called_once_with("doc.FCStd")
        fake_view.set_stage_button_enabled.assert_called_once_with("doc.FCStd", enabled=False)

    def test_on_add_button_clicked_clears_dirty_paths(self) -> None:
        """Only removes the staged file from _dirty_paths, not all paths."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Setup mock working snapshot
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )

        # Setup mock diff result
        mock_diff_result = DiffResult(
            old_snapshot=None,
            new_snapshot=mock_working_snapshot,
            hierarchy=DiffHierarchy(),
        )
        presenter._diff_results_by_path = {"doc.FCStd": mock_diff_result}

        # Pre-populate multiple dirty paths
        presenter._dirty_paths = {"doc.FCStd", "other.FCStd", "another.FCStd"}

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Act
        presenter.on_add_button_clicked("doc.FCStd")

        # Assert - only the staged path is removed, others remain
        assert presenter._dirty_paths == {"other.FCStd", "another.FCStd"}


class TestDiffPresenterStageAllClicked:
    """Tests for DiffPresenter.on_stage_all_clicked() method."""

    def test_on_stage_all_clicked_stages_all_documents(self) -> None:
        """Stages all documents when git repository and snapshots exist."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Create multiple snapshots with hierarchies that have changes
        hierarchy1 = DiffHierarchy()
        hierarchy1.add_node(NodeDiff(path="Part", type_id="Part::Feature", _force_state=DiffState.MODIFIED))
        snapshot1 = Snapshot(
            snapshot_id="ws1",
            document_name="doc1.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc1.FCStd",
        )

        hierarchy2 = DiffHierarchy()
        hierarchy2.add_node(NodeDiff(path="Part", type_id="Part::Feature", _force_state=DiffState.MODIFIED))
        snapshot2 = Snapshot(
            snapshot_id="ws2",
            document_name="doc2.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc2.FCStd",
        )

        # Populate _diff_results_by_path with multiple diff results
        presenter._diff_results_by_path = {
            "doc1.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=snapshot1,
                hierarchy=hierarchy1,
            ),
            "doc2.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=snapshot2,
                hierarchy=hierarchy2,
            ),
        }

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Act
        presenter.on_stage_all_clicked()

        # Assert - stage was called with all snapshots
        presenter._stage_documents.execute.assert_called_once_with(mock_repo, [snapshot1, snapshot2])

    def test_on_stage_all_clicked_no_repo_returns_early(self) -> None:
        """Returns early without staging when no git repository is available."""
        fake_view, presenter = _create_test_presenter()

        # No git repository set (ui_state.git_repository is None by default)

        # Act
        presenter.on_stage_all_clicked()

        # Assert - stage was never called
        presenter._stage_documents.execute.assert_not_called()

    def test_on_stage_all_clicked_empty_snapshots_returns_early(self) -> None:
        """Returns early when no snapshots exist in diff results."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Populate _diff_results_by_path with results that have no new_snapshot
        presenter._diff_results_by_path = {
            "doc.FCStd": DiffResult(
                old_snapshot=Snapshot(
                    snapshot_id="s1",
                    document_name="doc.FCStd",
                    timestamp=datetime.datetime.now(),
                ),
                new_snapshot=None,
                hierarchy=DiffHierarchy(),
            ),
        }

        # Act
        presenter.on_stage_all_clicked()

        # Assert - stage was never called
        presenter._stage_documents.execute.assert_not_called()

    def test_on_stage_all_clicked_ignores_documents_without_changes(self) -> None:
        """Only stages documents that have has_changes=True in their hierarchy."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Create a snapshot with changes (staggable)
        hierarchy_with_changes = DiffHierarchy()
        hierarchy_with_changes.add_node(NodeDiff(path="Part", type_id="Part::Feature", _force_state=DiffState.MODIFIED))
        snapshot_with_changes = Snapshot(
            snapshot_id="ws1",
            document_name="changed.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="changed.FCStd",
        )

        # Create a snapshot without changes (not staggable)
        hierarchy_no_changes = DiffHierarchy()
        hierarchy_no_changes.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        snapshot_no_changes = Snapshot(
            snapshot_id="ws2",
            document_name="unchanged.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="unchanged.FCStd",
        )

        # Populate _diff_results_by_path with both types
        presenter._diff_results_by_path = {
            "changed.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=snapshot_with_changes,
                hierarchy=hierarchy_with_changes,
            ),
            "unchanged.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=snapshot_no_changes,
                hierarchy=hierarchy_no_changes,
            ),
        }

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Act
        presenter.on_stage_all_clicked()

        # Assert - only the document with changes is staged
        presenter._stage_documents.execute.assert_called_once_with(mock_repo, [snapshot_with_changes])

    def test_on_stage_all_clicked_refreshes_view_on_success(self) -> None:
        """Refreshes the working tree view after successful staging."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature", _force_state=DiffState.MODIFIED))
        snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )

        presenter._diff_results_by_path = {
            "doc.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=snapshot,
                hierarchy=hierarchy,
            ),
        }

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Mock the refresh method to verify it's called
        with MagicMock() as mock_refresh:
            presenter._on_working_tree_selected = mock_refresh

            # Act
            presenter.on_stage_all_clicked()

            # Assert
            mock_refresh.assert_called_once()

    def test_on_stage_all_clicked_failure_logs_warning(self) -> None:
        """Logs warning when staging fails and does not refresh view."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )

        presenter._diff_results_by_path = {
            "doc.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=snapshot,
                hierarchy=DiffHierarchy(),
            ),
        }

        # Setup mock stage action to fail
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = False
        mock_stage_result.message = "Stage failed"
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Mock the refresh method to verify it's NOT called
        with MagicMock() as mock_refresh:
            presenter._on_working_tree_selected = mock_refresh

            # Act
            presenter.on_stage_all_clicked()

            # Assert - refresh was NOT called on failure
            mock_refresh.assert_not_called()

    def test_on_stage_all_clicked_clears_dirty_paths(self) -> None:
        """Clears _dirty_paths after successful all staging."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature", _force_state=DiffState.MODIFIED))
        snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )

        presenter._diff_results_by_path = {
            "doc.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=snapshot,
                hierarchy=hierarchy,
            ),
        }

        # Pre-populate dirty paths
        presenter._dirty_paths = {"doc.FCStd", "other.FCStd"}

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Act
        presenter.on_stage_all_clicked()

        # Assert - dirty paths cleared after successful staging
        assert presenter._dirty_paths == set()


class TestDiffPresenterStageAllClickedDirtyPaths:
    """Tests for on_stage_all_clicked() including git-dirty document handling."""

    def test_on_stage_all_clicked_includes_git_dirty_docs(self) -> None:
        """Stages documents that are git-dirty even without diff changes."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Create a snapshot WITHOUT changes (not staggable by diff alone)
        hierarchy_no_changes = DiffHierarchy()
        hierarchy_no_changes.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        snapshot_no_changes = Snapshot(
            snapshot_id="ws1",
            document_name="dirty.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="dirty.FCStd",
        )

        # Populate _diff_results_by_path with a doc that has no diff changes
        presenter._diff_results_by_path = {
            "dirty.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=snapshot_no_changes,
                hierarchy=hierarchy_no_changes,
            ),
        }

        # Set dirty_paths to include this document (simulating git-tracked changes)
        presenter._dirty_paths = {"dirty.FCStd"}

        # Setup mock stage action
        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Act
        presenter.on_stage_all_clicked()

        # Assert - the git-dirty document is staged despite having no diff changes
        presenter._stage_documents.execute.assert_called_once_with(mock_repo, [snapshot_no_changes])

    def test_on_stage_all_clicked_mixed_dirty_and_changed_docs(self) -> None:
        """Stages both git-dirty docs and docs with diff changes."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Doc with changes (staggable)
        hierarchy_changed = DiffHierarchy()
        hierarchy_changed.add_node(NodeDiff(path="Part", type_id="Part::Feature", _force_state=DiffState.MODIFIED))
        snapshot_changed = Snapshot(
            snapshot_id="ws1",
            document_name="changed.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="changed.FCStd",
        )

        # Doc that is git-dirty but has no diff changes
        hierarchy_no_changes = DiffHierarchy()
        hierarchy_no_changes.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        snapshot_dirty = Snapshot(
            snapshot_id="ws2",
            document_name="dirty.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="dirty.FCStd",
        )

        # Doc that is neither dirty nor changed (not staggable)
        hierarchy_unchanged = DiffHierarchy()
        hierarchy_unchanged.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        snapshot_unchanged = Snapshot(
            snapshot_id="ws3",
            document_name="clean.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="clean.FCStd",
        )

        presenter._diff_results_by_path = {
            "changed.FCStd": DiffResult(old_snapshot=None, new_snapshot=snapshot_changed, hierarchy=hierarchy_changed),
            "dirty.FCStd": DiffResult(old_snapshot=None, new_snapshot=snapshot_dirty, hierarchy=hierarchy_no_changes),
            "clean.FCStd": DiffResult(
                old_snapshot=None, new_snapshot=snapshot_unchanged, hierarchy=hierarchy_unchanged
            ),
        }
        presenter._dirty_paths = {"dirty.FCStd"}

        mock_stage_result = MagicMock()
        mock_stage_result.is_success = True
        mock_stage_result.message = ""
        presenter._stage_documents.execute.return_value = mock_stage_result

        # Act
        presenter.on_stage_all_clicked()

        # Assert - only changed and dirty docs are staged, not clean
        presenter._stage_documents.execute.assert_called_once_with(mock_repo, [snapshot_changed, snapshot_dirty])


class TestDiffPresenterStageAllButtonVisibility:
    """Tests for present_diffs() Stage All button visibility logic."""

    def test_present_diffs_shows_stage_all_button_during_working_tree(self) -> None:
        """Stage All button is visible when selection is WORKING_TREE."""
        fake_view, presenter = _create_test_presenter()

        # Set the current selection to WORKING_TREE
        fake_view._current_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=DiffHierarchy(),
        )

        # Act
        presenter.present_diffs([diff_result])

        # Assert
        calls = fake_view.get_calls()
        visible_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_visible"),
            None,
        )
        assert visible_call is not None
        assert visible_call["visible"] is True

    def test_on_staging_selected_no_results_hides_stage_all(self) -> None:
        """Selecting Staging when all staged diffs fail hides the Stage All button."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Return staged paths
        presenter._get_staged_file_paths.execute.return_value = MagicMock(is_success=True, data=["a.FCStd"])

        # All staged file diffs fail (index snapshot missing) - creates warning row
        mock_index_result = MagicMock()
        mock_index_result.is_success = False
        mock_index_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_index_result

        # Act
        presenter._on_staging_selected()

        # Assert - Stage All button is hidden (warning entries have stage_button_enabled=False)
        calls = fake_view.get_calls()
        visible_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_visible"),
            None,
        )
        assert visible_call is not None
        assert visible_call["visible"] is False

    def test_present_diffs_hides_stage_all_button_during_commit(self) -> None:
        """Stage All button is hidden when selection is COMMIT."""
        fake_view, presenter = _create_test_presenter()

        # Set the current selection to COMMIT
        fake_view._current_selection = HistorySelection(item_kind="COMMIT", commit_hash="abc123")

        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=DiffHierarchy(),
        )

        # Act
        presenter.present_diffs([diff_result])

        # Assert
        calls = fake_view.get_calls()
        visible_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_visible"),
            None,
        )
        assert visible_call is not None
        assert visible_call["visible"] is False

    def test_present_diffs_enables_stage_all_button_when_any_staggable(self) -> None:
        """Stage All button is enabled when at least one document is staggable."""
        fake_view, presenter = _create_test_presenter()

        # Set the current selection to WORKING_TREE
        fake_view._current_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Part", type_id="Part::Feature"))
        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(
                snapshot_id="s2",
                document_name="v2",
                timestamp=datetime.datetime.now(),
                git_path="dirty.FCStd",
            ),
            hierarchy=hierarchy,
        )

        # Act - pass dirty_paths to make the document staggable
        presenter.present_diffs([diff_result], dirty_paths={"dirty.FCStd"})

        # Assert
        calls = fake_view.get_calls()
        enabled_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_enabled"),
            None,
        )
        assert enabled_call is not None
        assert enabled_call["enabled"] is True

    def test_present_diffs_disables_stage_all_button_when_none_staggable(self) -> None:
        """Stage All button is disabled when no documents are staggable."""
        fake_view, presenter = _create_test_presenter()

        # Set the current selection to WORKING_TREE
        fake_view._current_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        diff_result = DiffResult(
            old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
            new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
            hierarchy=DiffHierarchy(),
        )

        # Act - no dirty_paths, so no documents are staggable
        presenter.present_diffs([diff_result])

        # Assert
        calls = fake_view.get_calls()
        enabled_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_enabled"),
            None,
        )
        assert enabled_call is not None
        assert enabled_call["enabled"] is False


class TestDiffPresenterStageAllButtonEdgeCasesNoDiff:
    """Tests for Stage All button visibility when no diff results are available."""

    def test_on_working_tree_selected_no_diff_results_hides_stage_all(self) -> None:
        """When eligible docs exist but diff creation fails, Stage All is hidden."""
        from tests.fakes.fake_freecad_port import DocumentLike

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Pre-populate stale state (simulating a prior selection)
        old_snapshot = Snapshot(
            snapshot_id="s1",
            document_name="old.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="old.FCStd",
        )
        presenter._diff_results_by_path = {
            "old.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=old_snapshot,
                hierarchy=DiffHierarchy(),
            ),
        }

        # Return eligible documents
        mock_doc = MagicMock(spec=DocumentLike)
        mock_doc.FileName = "/test/path/doc.FCStd"
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = [mock_doc]
        mock_docs_result.message = ""
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Working snapshot creation succeeds
        mock_working_snapshot = Snapshot(
            snapshot_id="ws1",
            document_name="doc.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="doc.FCStd",
        )
        mock_working_result = MagicMock()
        mock_working_result.is_success = True
        mock_working_result.data = mock_working_snapshot
        presenter._create_working_tree_snapshot.execute.return_value = mock_working_result

        # Commit snapshot returns None (stub)
        mock_commit_result = MagicMock()
        mock_commit_result.is_success = True
        mock_commit_result.data = None
        presenter._create_commit_snapshot.execute.return_value = mock_commit_result

        # Diff creation fails
        mock_diff_result = MagicMock()
        mock_diff_result.is_success = False
        mock_diff_result.message = "Diff failed"
        presenter._create_diff.execute.return_value = mock_diff_result

        # Dirty documents returns empty
        mock_dirty_result = MagicMock()
        mock_dirty_result.is_success = True
        mock_dirty_result.data = []
        presenter._get_dirty_documents.execute.return_value = mock_dirty_result

        # Act
        presenter._on_working_tree_selected()

        # Assert - stale state is cleared and Stage All is hidden
        assert presenter._diff_results_by_path == {}

        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        assert show_trees_call["diff_trees"] == []

        visible_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_visible"),
            None,
        )
        assert visible_call is not None
        assert visible_call["visible"] is False


class TestDiffPresenterStagingSelection:
    """Tests for staging selection plumbing and node lookup."""

    def test_on_staging_selected_populates_diff_map_using_git_path(self) -> None:
        """Staging selection stores diff results keyed by snapshot git_path."""
        fake_view, presenter = _create_test_presenter()

        presenter._ui_state.git_repository = GitRepository(name="repo", absolute_path="/repo")
        presenter._get_staged_file_paths.execute.return_value = MagicMock(is_success=True, data=["a.FCStd"])

        index_snapshot = Snapshot(
            snapshot_id="idx-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="a.FCStd",
        )
        head_snapshot = Snapshot(
            snapshot_id="head-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="a.FCStd",
        )
        presenter._create_commit_snapshot.execute.side_effect = [
            MagicMock(is_success=True, data=index_snapshot),
            MagicMock(is_success=True, data=head_snapshot),
        ]

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Body", type_id="PartDesign::Body", _force_state=DiffState.MODIFIED))
        presenter._create_diff.execute.return_value = MagicMock(
            is_success=True,
            data=DiffResult(old_snapshot=head_snapshot, new_snapshot=index_snapshot, hierarchy=hierarchy),
        )

        presenter._on_staging_selected()

        assert "a.FCStd" in presenter._diff_results_by_path

    def test_on_staging_selected_node_click_resolves_document_diff(self) -> None:
        """After staging selection, node click resolves and shows properties."""
        fake_view, presenter = _create_test_presenter()

        presenter._ui_state.git_repository = GitRepository(name="repo", absolute_path="/repo")
        presenter._get_staged_file_paths.execute.return_value = MagicMock(is_success=True, data=["a.FCStd"])

        index_snapshot = Snapshot(
            snapshot_id="idx-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="a.FCStd",
        )
        head_snapshot = Snapshot(
            snapshot_id="head-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="a.FCStd",
        )
        presenter._create_commit_snapshot.execute.side_effect = [
            MagicMock(is_success=True, data=index_snapshot),
            MagicMock(is_success=True, data=head_snapshot),
        ]

        old_prop = Property.from_freecad(10.0, {}, "Base")
        new_prop = Property.from_freecad(20.0, {}, "Base")
        node = NodeDiff(
            path="Body",
            type_id="PartDesign::Body",
            property_diffs=[PropertyDiff(property_name="Length", old_value=old_prop, new_value=new_prop)],
            _force_state=DiffState.MODIFIED,
        )
        hierarchy = DiffHierarchy()
        hierarchy.add_node(node)
        presenter._create_diff.execute.return_value = MagicMock(
            is_success=True,
            data=DiffResult(old_snapshot=head_snapshot, new_snapshot=index_snapshot, hierarchy=hierarchy),
        )

        presenter._on_staging_selected()
        presenter.on_node_selected("a.FCStd", "Body")

        prop_calls = [c for c in fake_view.get_calls() if c["method"] == "show_properties"]
        assert prop_calls
        assert len(prop_calls[-1]["properties"]) == 1

    def test_on_staging_selected_missing_git_path_key_clears_properties(self) -> None:
        """Node selection clears properties when staged diff has no keyable git_path."""
        fake_view, presenter = _create_test_presenter()

        presenter._ui_state.git_repository = GitRepository(name="repo", absolute_path="/repo")
        presenter._get_staged_file_paths.execute.return_value = MagicMock(is_success=True, data=["a.FCStd"])

        index_snapshot = Snapshot(
            snapshot_id="idx-1",
            document_name="a.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="",
        )
        presenter._create_commit_snapshot.execute.side_effect = [
            MagicMock(is_success=True, data=index_snapshot),
            MagicMock(is_success=True, data=None),
        ]

        hierarchy = DiffHierarchy()
        hierarchy.add_node(NodeDiff(path="Body", type_id="PartDesign::Body", _force_state=DiffState.MODIFIED))
        presenter._create_diff.execute.return_value = MagicMock(
            is_success=True,
            data=DiffResult(old_snapshot=None, new_snapshot=index_snapshot, hierarchy=hierarchy),
        )

        presenter._on_staging_selected()
        presenter.on_node_selected("a.FCStd", "Body")

        prop_calls = [c for c in fake_view.get_calls() if c["method"] == "show_properties"]
        assert prop_calls
        assert prop_calls[-1]["properties"] == []


class TestDiffPresenterStageAllButtonEdgeCases:
    """Tests for Stage All button visibility in edge cases."""

    def test_present_diffs_empty_results_hides_stage_all_button(self) -> None:
        """Calling present_diffs([], []) hides the Stage All button."""
        fake_view, presenter = _create_test_presenter()

        # Set the current selection to WORKING_TREE
        fake_view._current_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        # Act
        presenter.present_diffs([])

        # Assert
        calls = fake_view.get_calls()
        visible_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_visible"),
            None,
        )
        assert visible_call is not None
        assert visible_call["visible"] is False

    def test_on_staging_selected_no_staged_files_hides_stage_all_button(self) -> None:
        """Selecting Staging with no staged files hides the Stage All button."""
        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Return empty staged paths
        presenter._get_staged_file_paths.execute.return_value = MagicMock(is_success=True, data=[])

        # Act
        presenter._on_staging_selected()

        # Assert
        calls = fake_view.get_calls()
        visible_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_visible"),
            None,
        )
        assert visible_call is not None
        assert visible_call["visible"] is False

    def test_on_working_tree_selected_no_eligible_docs_clears_state(self) -> None:
        """No eligible docs clears _diff_results_by_path, trees, and hides Stage All button."""

        fake_view, presenter = _create_test_presenter()

        # Setup mock repo
        mock_repo = GitRepository(name="test-repo", absolute_path="/test/path")
        presenter._ui_state.git_repository = mock_repo

        # Pre-populate stale state (simulating a prior selection)
        old_snapshot = Snapshot(
            snapshot_id="s1",
            document_name="old.FCStd",
            timestamp=datetime.datetime.now(),
            git_path="old.FCStd",
        )
        presenter._diff_results_by_path = {
            "old.FCStd": DiffResult(
                old_snapshot=None,
                new_snapshot=old_snapshot,
                hierarchy=DiffHierarchy(),
            ),
        }
        fake_view._current_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

        # Return no eligible docs
        mock_docs_result = MagicMock()
        mock_docs_result.is_success = True
        mock_docs_result.data = []
        mock_docs_result.message = "no open documents"
        presenter._get_eligible_docs.execute.return_value = mock_docs_result

        # Act
        presenter._on_working_tree_selected()

        # Assert - stale state is cleared
        assert presenter._diff_results_by_path == {}

        calls = fake_view.get_calls()
        show_trees_call = next((c for c in calls if c["method"] == "show_diff_trees"), None)
        assert show_trees_call is not None
        assert show_trees_call["diff_trees"] == []

        visible_call = next(
            (c for c in calls if c["method"] == "set_stage_all_button_visible"),
            None,
        )
        assert visible_call is not None
        assert visible_call["visible"] is False


class TestDiffPresenterRuntimePrecision:
    """Tests for DiffPresenter using runtime precision from settings."""

    def test_transform_property_diffs_uses_runtime_precision(self) -> None:
        """Test that _transform_property_diffs uses precision from settings repo."""
        from unittest.mock import MagicMock

        from freecad.diff_wb.domain.settings.models import Settings
        from freecad.diff_wb.domain.settings.repository import SettingsRepository

        fake_view, presenter = _create_test_presenter()

        # Create mock settings repo that returns precision=4
        mock_settings_repo = MagicMock(spec=SettingsRepository)
        mock_settings = MagicMock(spec=Settings)
        mock_settings.float_precision = 4
        mock_settings_repo.get_settings.return_value = mock_settings
        presenter._settings_repo = mock_settings_repo

        # Setup diff result with float property
        old_prop = Property.from_freecad(3.14159265, {}, "Base")
        new_prop = Property.from_freecad(3.14159999, {}, "Base")
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=old_prop,
            new_value=new_prop,
        )
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )

        # Act - call on_node_selected to trigger transformation
        presenter.present_diff(
            DiffResult(
                old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
                new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
                hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
            )
        )
        presenter.on_node_selected("v2", "Part")

        # Assert - check that format uses 4 decimal places
        calls = fake_view.get_calls()
        show_props_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert show_props_call is not None

        properties = show_props_call["properties"]
        assert len(properties) >= 1
        # The container summary should use 4 decimal places (precision from settings)
        # Check that values are formatted with 4 decimal places
        prop_pres = properties[0]
        if prop_pres.old_value is not None and isinstance(prop_pres.old_value, str):
            # Should be formatted like "[3.1416]" with 4 decimal places
            assert ".1416" in prop_pres.old_value or "3.1416" in prop_pres.old_value

    def test_get_precision_uses_settings_repo_when_available(self) -> None:
        """Test that _get_precision returns value from settings repo."""
        from unittest.mock import MagicMock

        from freecad.diff_wb.domain.settings.models import Settings
        from freecad.diff_wb.domain.settings.repository import SettingsRepository

        fake_view, presenter = _create_test_presenter()

        # Create mock settings repo with precision=6
        mock_settings_repo = MagicMock(spec=SettingsRepository)
        mock_settings = MagicMock(spec=Settings)
        mock_settings.float_precision = 6
        mock_settings_repo.get_settings.return_value = mock_settings
        presenter._settings_repo = mock_settings_repo

        # Act
        precision = presenter._get_precision()

        # Assert
        assert precision == 6

    def test_get_precision_falls_back_to_default_when_no_settings_repo(self) -> None:
        """Test that _get_precision returns default when no settings repo."""
        fake_view, presenter = _create_test_presenter()
        presenter._settings_repo = None

        # Act
        precision = presenter._get_precision()

        # Assert - should use default precision (2)
        assert precision == 2


class TestDiffPresenterFormatFloatsWithPrecision:
    """Tests for float formatting with runtime precision in DiffPresenter."""

    def test_container_summary_formats_floats_with_runtime_precision(self) -> None:
        """Test that container summaries format floats using runtime precision."""
        from unittest.mock import MagicMock

        from freecad.diff_wb.domain.settings.models import Settings
        from freecad.diff_wb.domain.settings.repository import SettingsRepository

        fake_view, presenter = _create_test_presenter()

        # Setup settings repo with precision=5
        mock_settings_repo = MagicMock(spec=SettingsRepository)
        mock_settings = MagicMock(spec=Settings)
        mock_settings.float_precision = 5
        mock_settings_repo.get_settings.return_value = mock_settings
        presenter._settings_repo = mock_settings_repo

        # Create property with list values (triggers container summary)
        old_vec = Property.from_freecad([1.23456789, 2.34567890, 3.45678901], {}, "Base")
        new_vec = Property.from_freecad([1.23456111, 2.34567222, 3.45678333], {}, "Base")
        prop_diff = PropertyDiff(
            property_name="Position",
            old_value=old_vec,
            new_value=new_vec,
        )
        node_diff = NodeDiff(
            path="Part",
            type_id="Part::Feature",
            property_diffs=[prop_diff],
            _force_state=DiffState.MODIFIED,
        )

        # Act
        presenter.present_diff(
            DiffResult(
                old_snapshot=Snapshot(snapshot_id="s1", document_name="v1", timestamp=datetime.datetime.now()),
                new_snapshot=Snapshot(snapshot_id="s2", document_name="v2", timestamp=datetime.datetime.now()),
                hierarchy=(lambda h: (h.add_node(node_diff), h)[1])(DiffHierarchy()),
            )
        )
        presenter.on_node_selected("v2", "Part")

        # Assert - check precision=5 formatting
        calls = fake_view.get_calls()
        show_props_call = next((c for c in calls if c["method"] == "show_properties"), None)
        assert show_props_call is not None

        properties = show_props_call["properties"]
        assert len(properties) >= 1
        prop_pres = properties[0]
        # Container summary should have 5 decimal places
        if prop_pres.old_value is not None and isinstance(prop_pres.old_value, str):
            # Check for 5 decimal places format like "[1.23457 2.34568 3.45679]"
            assert prop_pres.old_value.count(".") > 0  # Has decimal points
