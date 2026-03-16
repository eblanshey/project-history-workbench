# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for tree_diff module.

File responsibility: Tests for the tree comparison algorithm with path-based indexing.
These tests verify the core diff computation logic without any FreeCAD dependencies.
"""

from datetime import datetime

import pytest

from freecad.diff_wb.diff.diff_result import DiffState, NodeDiff
from freecad.diff_wb.domain.property_value import PropertyValue, PropertyType
from freecad.diff_wb.domain.snapshot import Snapshot, TreeNode
from freecad.diff_wb.diff.tree_diff import (
    build_path_index,
    compare_nodes_by_path,
    compare_snapshots,
    create_added_node_diff,
    create_deleted_node_diff,
    find_added_paths,
    find_common_paths,
    find_deleted_paths,
    reconstruct_hierarchy,
)


class TestBuildPathIndex:
    """Tests for build_path_index function."""

    def test_empty_root_nodes(self):
        """Test building index from empty root nodes list."""
        index = build_path_index([])
        assert index == {}

    def test_single_root_node(self):
        """Test building index with a single root node."""
        root = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        snapshot = Snapshot(document_name="Test", timestamp=datetime.now(), root_nodes=[root])

        index = build_path_index(snapshot.root_nodes)

        assert len(index) == 1
        assert "Body" in index
        assert index["Body"] is root

    def test_nested_children(self):
        """Test building index with nested children."""
        grandchild = TreeNode(
            name="ShapeSource",
            type_id="Part::Feature",
            label="ShapeSource",
            path="Body/Pad/ShapeSource",
        )
        child = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            children=[grandchild],
        )
        root = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            children=[child],
        )

        index = build_path_index([root])

        assert len(index) == 3
        assert "Body" in index
        assert "Body/Pad" in index
        assert "Body/Pad/ShapeSource" in index

    def test_multiple_roots(self):
        """Test building index with multiple root nodes."""
        root1 = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        root2 = TreeNode(name="Cube", type_id="Part::Box", label="Cube", path="Cube")

        index = build_path_index([root1, root2])

        assert len(index) == 2
        assert "Body" in index
        assert "Cube" in index


class TestFindAddedPaths:
    """Tests for find_added_paths function."""

    def test_no_added_paths(self):
        """Test when new snapshot has no new paths."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None}  # type: ignore

        added = find_added_paths(old_index, new_index)

        assert added == set()

    def test_simple_addition(self):
        """Test detecting a simple addition."""
        old_index = {"Body": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None}  # type: ignore

        added = find_added_paths(old_index, new_index)

        assert added == {"Body/Pad"}

    def test_multiple_additions(self):
        """Test detecting multiple additions."""
        old_index = {"Body": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None, "Body/Pocket": None}  # type: ignore

        added = find_added_paths(old_index, new_index)

        assert added == {"Body/Pad", "Body/Pocket"}


class TestFindDeletedPaths:
    """Tests for find_deleted_paths function."""

    def test_no_deleted_paths(self):
        """Test when old snapshot has no deleted paths."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None}  # type: ignore

        deleted = find_deleted_paths(old_index, new_index)

        assert deleted == set()

    def test_simple_deletion(self):
        """Test detecting a simple deletion."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None}  # type: ignore

        deleted = find_deleted_paths(old_index, new_index)

        assert deleted == {"Body/Pad"}

    def test_multiple_deletions(self):
        """Test detecting multiple deletions."""
        old_index = {"Body": None, "Body/Pad": None, "Body/Pocket": None}  # type: ignore
        new_index = {"Body": None}  # type: ignore

        deleted = find_deleted_paths(old_index, new_index)

        assert deleted == {"Body/Pad", "Body/Pocket"}


class TestFindCommonPaths:
    """Tests for find_common_paths function."""

    def test_all_common(self):
        """Test when all paths are common."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None}  # type: ignore

        common = find_common_paths(old_index, new_index)

        assert common == {"Body", "Body/Pad"}

    def test_no_common(self):
        """Test when no paths are common."""
        old_index = {"Body": None}  # type: ignore
        new_index = {"Cube": None}  # type: ignore

        common = find_common_paths(old_index, new_index)

        assert common == set()

    def test_partial_common(self):
        """Test when some paths are common."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None, "Body/Pocket": None}  # type: ignore

        common = find_common_paths(old_index, new_index)

        assert common == {"Body"}


class TestCompareNodesByPath:
    """Tests for compare_nodes_by_path function."""

    def test_identical_nodes(self):
        """Test comparing identical nodes returns None."""
        props = {
            "Label": PropertyValue.create(PropertyType.STRING, "Body"),
        }
        old_node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            properties=props,
        )
        new_node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            properties=props,
        )

        old_index = {"Body": old_node}
        new_index = {"Body": new_node}

        result = compare_nodes_by_path("Body", old_index, new_index)

        assert result is None

    def test_modified_property(self):
        """Test detecting a modified property."""
        old_props = {
            "Length": PropertyValue.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Length": PropertyValue.create(PropertyType.FLOAT, 20.0),
        }
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )

        old_index = {"Body/Pad": old_node}
        new_index = {"Body/Pad": new_node}

        result = compare_nodes_by_path("Body/Pad", old_index, new_index)

        assert result is not None
        assert result.path == "Body/Pad"
        assert result.state == DiffState.MODIFIED

    def test_added_property(self):
        """Test detecting an added property."""
        old_props = {}
        new_props = {
            "NewProperty": PropertyValue.create(PropertyType.STRING, "value"),
        }
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )

        old_index = {"Body/Pad": old_node}
        new_index = {"Body/Pad": new_node}

        result = compare_nodes_by_path("Body/Pad", old_index, new_index)

        assert result is not None
        assert result.state == DiffState.MODIFIED

    def test_deleted_property(self):
        """Test detecting a deleted property."""
        old_props = {
            "OldProperty": PropertyValue.create(PropertyType.STRING, "value"),
        }
        new_props = {}
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )

        old_index = {"Body/Pad": old_node}
        new_index = {"Body/Pad": new_node}

        result = compare_nodes_by_path("Body/Pad", old_index, new_index)

        assert result is not None
        assert result.state == DiffState.MODIFIED

    def test_excluded_properties_filtered(self):
        """Test that excluded properties are filtered out during comparison."""
        # TimeStamp is in EXCLUDED_PROPERTIES (AUTO_EXCLUDED_PROPERTIES)
        old_props = {
            "TimeStamp": PropertyValue.create(PropertyType.STRING, "2024-01-01T00:00:00"),
            "Label": PropertyValue.create(PropertyType.STRING, "Pad"),
        }
        new_props = {
            "TimeStamp": PropertyValue.create(PropertyType.STRING, "2024-01-01T00:00:01"),  # Different timestamp
            "Label": PropertyValue.create(PropertyType.STRING, "Pad"),
        }
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )

        old_index = {"Body/Pad": old_node}
        new_index = {"Body/Pad": new_node}

        result = compare_nodes_by_path("Body/Pad", old_index, new_index)

        # Should return None because only excluded property (TimeStamp) differs
        assert result is None


class TestCreateAddedNodeDiff:
    """Tests for create_added_node_diff function."""

    def test_creates_correct_state(self):
        """Test that added node diff has ADDED state."""
        node = TreeNode(
            name="NewObject",
            type_id="Part::Box",
            label="New Object",
            path="NewObject",
        )

        result = create_added_node_diff("NewObject", node)

        assert result.path == "NewObject"
        assert result.type_id == "Part::Box"
        assert result.state == DiffState.ADDED


class TestCreateDeletedNodeDiff:
    """Tests for create_deleted_node_diff function."""

    def test_creates_correct_state(self):
        """Test that deleted node diff has DELETED state."""
        node = TreeNode(
            name="OldObject",
            type_id="Part::Box",
            label="Old Object",
            path="OldObject",
        )

        result = create_deleted_node_diff("OldObject", node)

        assert result.path == "OldObject"
        assert result.type_id == "Part::Box"
        assert result.state == DiffState.DELETED


class TestReconstructHierarchy:
    """Tests for reconstruct_hierarchy function."""

    def test_hierarchy_order(self):
        """Test that hierarchy is reconstructed in correct tree order.

        Verifies that:
        - Parents appear before their children
        - Siblings are sorted alphabetically
        """
        from freecad.diff_wb.diff.diff_result import PropertyDiff

        # Create NodeDiff objects in random/unsorted order
        diffs = [
            NodeDiff(
                path="Body/Pad/ShapeSource",
                type_id="Part::Feature",
                property_diffs=[
                    PropertyDiff(
                        property_name="Placement",
                        old_value=PropertyValue.create(PropertyType.VECTOR, (0, 0, 0)),
                        new_value=PropertyValue.create(PropertyType.VECTOR, (1, 1, 1)),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pocket",
                type_id="PartDesign::Pocket",
                property_diffs=[
                    PropertyDiff(
                        property_name="Depth",
                        old_value=None,
                        new_value=PropertyValue.create(PropertyType.FLOAT, 5.0),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pad",
                type_id="PartDesign::Pad",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
                        new_value=None,
                    )
                ],
            ),
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=PropertyValue.create(PropertyType.STRING, "OldBody"),
                        new_value=PropertyValue.create(PropertyType.STRING, "NewBody"),
                    )
                ],
            ),
            NodeDiff(
                path="Cube",
                type_id="Part::Box",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=None,
                        new_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        # Verify root nodes are in alphabetical order: Body, Cube
        assert len(result) == 2
        assert result[0].path == "Body"
        assert result[1].path == "Cube"

        # Verify Body's children are in order: Pad, Pocket (alphabetical)
        assert len(result[0].children) == 2
        assert result[0].children[0].path == "Body/Pad"
        assert result[0].children[1].path == "Body/Pocket"

        # Verify Pad has ShapeSource as child (parent before child)
        assert len(result[0].children[0].children) == 1
        assert result[0].children[0].children[0].path == "Body/Pad/ShapeSource"

    def test_empty_list(self):
        """Test reconstructing hierarchy from empty list."""
        result = reconstruct_hierarchy([])
        assert result == []

    def test_single_root(self):
        """Test reconstructing hierarchy with single root node."""
        from freecad.diff_wb.diff.diff_result import PropertyDiff

        diffs = [
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=None,
                        new_value=PropertyValue.create(PropertyType.STRING, "Body"),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        assert len(result) == 1
        assert result[0].path == "Body"
        assert len(result[0].children) == 0

    def test_parent_child_relationship(self):
        """Test that parent-child relationships are correctly reconstructed."""
        from freecad.diff_wb.diff.diff_result import PropertyDiff

        diffs = [
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=PropertyValue.create(PropertyType.STRING, "OldBody"),
                        new_value=PropertyValue.create(PropertyType.STRING, "NewBody"),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pad",
                type_id="PartDesign::Pad",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=None,
                        new_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        assert len(result) == 1
        assert result[0].path == "Body"
        assert len(result[0].children) == 1
        assert result[0].children[0].path == "Body/Pad"

    def test_deep_nesting(self):
        """Test reconstructing deeply nested hierarchy."""
        from freecad.diff_wb.diff.diff_result import PropertyDiff

        diffs = [
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=PropertyValue.create(PropertyType.STRING, "OldBody"),
                        new_value=PropertyValue.create(PropertyType.STRING, "NewBody"),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pad",
                type_id="PartDesign::Pad",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=None,
                        new_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pad/ShapeSource",
                type_id="Part::Feature",
                property_diffs=[
                    PropertyDiff(
                        property_name="Placement",
                        old_value=None,
                        new_value=PropertyValue.create(PropertyType.VECTOR, (0, 0, 0)),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        assert len(result) == 1
        assert result[0].path == "Body"
        assert len(result[0].children) == 1
        assert result[0].children[0].path == "Body/Pad"
        assert len(result[0].children[0].children) == 1
        assert result[0].children[0].children[0].path == "Body/Pad/ShapeSource"

    def test_multiple_roots(self):
        """Test reconstructing hierarchy with multiple root nodes."""
        from freecad.diff_wb.diff.diff_result import PropertyDiff

        diffs = [
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=PropertyValue.create(PropertyType.STRING, "OldBody"),
                        new_value=PropertyValue.create(PropertyType.STRING, "NewBody"),
                    )
                ],
            ),
            NodeDiff(
                path="Cube",
                type_id="Part::Box",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=None,
                        new_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        assert len(result) == 2
        paths = {d.path for d in result}
        assert paths == {"Body", "Cube"}


class TestCompareSnapshots:
    """Tests for compare_snapshots function (end-to-end tree comparison)."""

    def test_empty_snapshots(self):
        """Test comparing two empty snapshots."""
        old_snapshot = Snapshot(document_name="Test", timestamp=datetime.now(), root_nodes=[])
        new_snapshot = Snapshot(document_name="Test", timestamp=datetime.now(), root_nodes=[])

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == set()
        assert result.deleted_paths == set()
        assert result.common_paths == set()
        assert result.node_diffs == []

    def test_identical_snapshots(self):
        """Test comparing identical snapshots returns no changes."""
        node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
        )
        old_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[node],
        )
        new_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[node],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == set()
        assert result.deleted_paths == set()
        assert result.common_paths == {"Body"}
        assert result.node_diffs == []  # No changes means no NodeDiff objects

    def test_simple_addition(self):
        """Test detecting a simple addition."""
        old_node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
        )
        new_node = TreeNode(
            name="Cube",
            type_id="Part::Box",
            label="Cube",
            path="Cube",
        )
        old_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node],
        )
        new_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node, new_node],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == {"Cube"}
        assert result.deleted_paths == set()
        assert len(result.node_diffs) == 1
        assert result.node_diffs[0].path == "Cube"
        assert result.node_diffs[0].state == DiffState.ADDED

    def test_simple_deletion(self):
        """Test detecting a simple deletion."""
        old_node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
        )
        deleted_node = TreeNode(
            name="Cube",
            type_id="Part::Box",
            label="Cube",
            path="Cube",
        )
        old_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node, deleted_node],
        )
        new_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == set()
        assert result.deleted_paths == {"Cube"}
        assert len(result.node_diffs) == 1
        assert result.node_diffs[0].path == "Cube"
        assert result.node_diffs[0].state == DiffState.DELETED

    def test_simple_modification(self):
        """Test detecting a simple modification."""
        old_props = {
            "Length": PropertyValue.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Length": PropertyValue.create(PropertyType.FLOAT, 20.0),
        }
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )
        old_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node],
        )
        new_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[new_node],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == set()
        assert result.deleted_paths == set()
        assert result.common_paths == {"Body/Pad"}
        assert len(result.node_diffs) == 1
        assert result.node_diffs[0].path == "Body/Pad"
        assert result.node_diffs[0].state == DiffState.MODIFIED

    def test_complex_hierarchy_changes(self):
        """Test complex hierarchy with additions and modifications."""
        # Old: Body -> Pad (Length=10)
        old_pad = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties={"Length": PropertyValue.create(PropertyType.FLOAT, 10.0)},
        )
        old_body = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            children=[old_pad],
        )

        # New: Body -> Pad (Length=20), Pocket (added)
        new_pad = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties={"Length": PropertyValue.create(PropertyType.FLOAT, 20.0)},
        )
        new_pocket = TreeNode(
            name="Pocket",
            type_id="PartDesign::Pocket",
            label="Pocket",
            path="Body/Pocket",
        )
        new_body = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            children=[new_pad, new_pocket],
        )

        old_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_body],
        )
        new_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[new_body],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == {"Body/Pocket"}
        assert result.deleted_paths == set()
        assert "Body/Pad" in result.common_paths
        # Should have Body/Pad (modified) and Body/Pocket (added)
        assert len(result.node_diffs) >= 1

    def test_path_collision_different_paths(self):
        """Test that same name at different paths are handled correctly."""
        # Two objects with same name but different paths
        old_node1 = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body1/Pad",
        )
        old_node2 = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body2/Pad",
        )
        old_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node1, old_node2],
        )

        # Delete Body1/Pad, keep Body2/Pad
        new_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node2],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.deleted_paths == {"Body1/Pad"}
        assert "Body2/Pad" in result.common_paths


class TestPerformance:
    """Performance tests for tree_diff module."""

    def test_large_snapshot_performance(self):
        """Test performance with 1000+ nodes."""
        # Build a snapshot with 1000 nodes
        root_nodes = []
        for i in range(100):
            # Create 10 children per root
            children = [
                TreeNode(
                    name=f"Child{j}",
                    type_id="Part::Feature",
                    label=f"Child {j}",
                    path=f"Root{i}/Child{j}",
                )
                for j in range(10)
            ]
            root = TreeNode(
                name=f"Root{i}",
                type_id="PartDesign::Body",
                label=f"Root {i}",
                path=f"Root{i}",
                children=children,
            )
            root_nodes.append(root)

        old_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=root_nodes,
        )

        # New snapshot with slight modifications
        new_root_nodes = list(root_nodes)  # Copy reference
        new_snapshot = Snapshot(
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=new_root_nodes,
        )

        # This should complete quickly (under 100ms for 1000 nodes)
        import time

        start = time.time()
        result = compare_snapshots(old_snapshot, new_snapshot)
        elapsed = time.time() - start

        # Verify we got results
        assert result is not None
        # Performance target: < 100ms for 1000 nodes
        assert elapsed < 0.1, f"Performance test failed: took {elapsed:.3f}s (> 100ms)"
