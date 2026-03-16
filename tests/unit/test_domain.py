# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for domain models."""

from datetime import datetime

import pytest

from freecad.diff_wb.domain import (
    Placement,
    PropertyType,
    PropertyValue,
    Rotation,
    Snapshot,
    TreeNode,
    Vector,
)
from freecad.diff_wb.diff.diff_result import (
    DiffResult,
    DiffState,
    DiffSummary,
    NodeDiff,
    PropertyDiff,
)


class TestVector:
    """Tests for the Vector class."""

    def test_creation(self):
        """Test vector creation."""
        v = Vector(x=1.0, y=2.0, z=3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_string_representation(self):
        """Test string representation."""
        v = Vector(x=1.0, y=2.0, z=3.0)
        assert str(v) == "(1.0, 2.0, 3.0)"

    def test_equality_exact(self):
        """Test exact equality."""
        v1 = Vector(1.0, 2.0, 3.0)
        v2 = Vector(1.0, 2.0, 3.0)
        assert v1 == v2

    def test_equality_approximate(self):
        """Test approximate equality for floats."""
        v1 = Vector(1.0, 2.0, 3.0)
        v2 = Vector(1.0 + 1e-10, 2.0 - 1e-10, 3.0)
        assert v1 == v2

    def test_inequality(self):
        """Test inequality."""
        v1 = Vector(1.0, 2.0, 3.0)
        v2 = Vector(1.0, 2.0, 4.0)
        assert v1 != v2


class TestRotation:
    """Tests for the Rotation class."""

    def test_creation(self):
        """Test rotation creation."""
        r = Rotation(axis_x=0.0, axis_y=0.0, axis_z=1.0, angle_degrees=45.0)
        assert r.axis_x == 0.0
        assert r.axis_y == 0.0
        assert r.axis_z == 1.0
        assert r.angle_degrees == 45.0

    def test_identity(self):
        """Test identity rotation."""
        r = Rotation.identity()
        assert r.axis_x == 0.0
        assert r.axis_y == 0.0
        assert r.axis_z == 1.0
        assert r.angle_degrees == 0.0

    def test_string_representation(self):
        """Test string representation."""
        r = Rotation(0.0, 0.0, 1.0, 90.0)
        assert "Angle=90" in str(r)

    def test_equality(self):
        """Test rotation equality."""
        r1 = Rotation(0.0, 0.0, 1.0, 45.0)
        r2 = Rotation(0.0, 0.0, 1.0, 45.0)
        assert r1 == r2


class TestPlacement:
    """Tests for the Placement class."""

    def test_creation(self):
        """Test placement creation."""
        pos = Vector(1.0, 2.0, 3.0)
        rot = Rotation(0.0, 0.0, 1.0, 45.0)
        p = Placement(position=pos, rotation=rot)
        assert p.position == pos
        assert p.rotation == rot

    def test_identity(self):
        """Test identity placement."""
        p = Placement.identity()
        assert p.position == Vector(0.0, 0.0, 0.0)
        assert p.rotation == Rotation.identity()

    def test_equality(self):
        """Test placement equality."""
        p1 = Placement(Vector(1.0, 2.0, 3.0), Rotation(0.0, 0.0, 1.0, 45.0))
        p2 = Placement(Vector(1.0, 2.0, 3.0), Rotation(0.0, 0.0, 1.0, 45.0))
        assert p1 == p2


class TestPropertyValue:
    """Tests for the PropertyValue class."""

    # =====================================================================
    # PropertyValue.create() Tests
    # =====================================================================

    def test_bool_creation(self):
        """Test boolean property value creation."""
        pv = PropertyValue.create(PropertyType.BOOL, True)
        assert pv.type_ == PropertyType.BOOL
        assert pv.value is True

    def test_int_creation(self):
        """Test integer property value creation."""
        pv = PropertyValue.create(PropertyType.INT, 42)
        assert pv.type_ == PropertyType.INT
        assert pv.value == 42

    def test_float_creation(self):
        """Test float property value creation."""
        pv = PropertyValue.create(PropertyType.FLOAT, 3.14)
        assert pv.type_ == PropertyType.FLOAT
        assert pv.value == 3.14

    def test_string_creation(self):
        """Test string property value creation."""
        pv = PropertyValue.create(PropertyType.STRING, "hello")
        assert pv.type_ == PropertyType.STRING
        assert pv.value == "hello"

    def test_vector_creation(self):
        """Test vector property value creation."""
        pv = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        assert pv.type_ == PropertyType.VECTOR
        assert isinstance(pv.value, Vector)
        assert pv.value.x == 1.0
        assert pv.value.y == 2.0
        assert pv.value.z == 3.0

    def test_vector_with_expression(self):
        """Test vector with expression."""
        pv = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch001.X")
        assert pv.expression == "Sketch001.X"
        assert str(pv) == "(1.0, 2.0, 3.0) (via Sketch001.X)"

    def test_placement_creation(self):
        """Test placement property value creation."""
        pv = PropertyValue.create(PropertyType.PLACEMENT, {"position": (0, 0, 0), "rotation": (0, 0, 1, 90)})
        assert pv.type_ == PropertyType.PLACEMENT
        assert isinstance(pv.value, Placement)
        assert pv.value.position == Vector(0, 0, 0)
        assert pv.value.rotation == Rotation(0, 0, 1, 90)

    def test_placement_with_expression(self):
        """Test placement with expression."""
        pv = PropertyValue.create(
            PropertyType.PLACEMENT, {"position": (0, 0, 0), "rotation": (0, 0, 1, 45)}, expression="Body.Placement"
        )
        assert pv.type_ == PropertyType.PLACEMENT
        assert pv.expression == "Body.Placement"

    def test_link_creation(self):
        """Test link property value creation."""
        pv = PropertyValue.create(PropertyType.LINK, "Body")
        assert pv.type_ == PropertyType.LINK
        assert pv.value == "Body"

    # =====================================================================
    # Equality Tests
    # =====================================================================

    def test_equality_same_type(self):
        """Test equality for same type values."""
        pv1 = PropertyValue.create(PropertyType.INT, 42)
        pv2 = PropertyValue.create(PropertyType.INT, 42)
        assert pv1 == pv2

    def test_inequality_different_type(self):
        """Test inequality for different types."""
        pv1 = PropertyValue.create(PropertyType.INT, 42)
        pv2 = PropertyValue.create(PropertyType.FLOAT, 42.0)
        assert pv1 != pv2

    def test_float_approximate_equality(self):
        """Test approximate equality for floats."""
        pv1 = PropertyValue.create(PropertyType.FLOAT, 1.0)
        pv2 = PropertyValue.create(PropertyType.FLOAT, 1.0 + 1e-10)
        assert pv1 == pv2

    # =====================================================================
    # Expression Support Tests
    # =====================================================================

    def test_bool_with_expression(self):
        """Test boolean property with expression."""
        pv = PropertyValue.create(PropertyType.BOOL, True, expression="Sketch001.Constrain")
        assert pv.type_ == PropertyType.BOOL
        assert pv.value is True
        assert pv.expression == "Sketch001.Constrain"
        assert str(pv) == "True (via Sketch001.Constrain)"

    def test_int_with_expression(self):
        """Test integer property with expression."""
        pv = PropertyValue.create(PropertyType.INT, 10, expression="Sketch001.Count")
        assert pv.type_ == PropertyType.INT
        assert pv.value == 10
        assert pv.expression == "Sketch001.Count"
        assert str(pv) == "10 (via Sketch001.Count)"

    def test_float_with_expression(self):
        """Test float property with expression."""
        pv = PropertyValue.create(PropertyType.FLOAT, 5.5, expression="Body.Length")
        assert pv.type_ == PropertyType.FLOAT
        assert pv.value == 5.5
        assert pv.expression == "Body.Length"
        assert str(pv) == "5.5 (via Body.Length)"

    def test_string_with_expression(self):
        """Test string property with expression."""
        pv = PropertyValue.create(PropertyType.STRING, "test", expression="Document.Name")
        assert pv.type_ == PropertyType.STRING
        assert pv.value == "test"
        assert pv.expression == "Document.Name"
        assert str(pv) == "test (via Document.Name)"

    def test_link_with_expression(self):
        """Test link property with expression."""
        pv = PropertyValue.create(PropertyType.LINK, "Body001", expression="PartDesign::Feature")
        assert pv.type_ == PropertyType.LINK
        assert pv.value == "Body001"
        assert pv.expression == "PartDesign::Feature"
        assert str(pv) == "Body001 (via PartDesign::Feature)"

    def test_equality_same_value_different_expression(self):
        """Test that same values with different expressions are NOT equal."""
        pv1 = PropertyValue.create(PropertyType.FLOAT, 10.0)
        pv2 = PropertyValue.create(PropertyType.FLOAT, 10.0, expression="Sketch001.X")
        assert pv1 != pv2

    def test_equality_expression_vs_no_expression(self):
        """Test that value with expression differs from value without."""
        pv1 = PropertyValue.create(PropertyType.INT, 42, expression="Some.Expression")
        pv2 = PropertyValue.create(PropertyType.INT, 42)
        assert pv1 != pv2

    def test_equality_same_expression(self):
        """Test that same value and expression are equal."""
        pv1 = PropertyValue.create(PropertyType.STRING, "hello", expression="Doc.Name")
        pv2 = PropertyValue.create(PropertyType.STRING, "hello", expression="Doc.Name")
        assert pv1 == pv2

    def test_equality_different_expressions(self):
        """Test that same value with different expressions are NOT equal."""
        pv1 = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch001.X")
        pv2 = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch002.X")
        assert pv1 != pv2

    def test_equality_both_none_expressions(self):
        """Test equality when both have no expressions."""
        pv1 = PropertyValue.create(PropertyType.BOOL, False)
        pv2 = PropertyValue.create(PropertyType.BOOL, False)
        assert pv1 == pv2


class TestTreeNode:
    """Tests for the TreeNode class."""

    def test_creation(self):
        """Test tree node creation."""
        node = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", is_root=False)
        assert node.name == "Pad"
        assert node.path == "Body/Pad"
        assert node.is_root is False

    def test_creation_with_properties(self):
        """Test tree node with properties."""
        prop = PropertyValue.create(PropertyType.FLOAT, 10.0)
        node = TreeNode(
            name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", properties={"Length": prop}
        )
        assert "Length" in node.properties
        assert node.properties["Length"].value == 10.0

    def test_creation_with_children(self):
        """Test tree node with children."""
        child = TreeNode(name="Sub", type_id="Part::Feature", label="Sub", path="Body/Pad/Sub")
        node = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", children=[child])
        assert len(node.children) == 1
        assert node.children[0].name == "Sub"

    def test_string_representation(self):
        """Test string representation."""
        node = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad")
        assert "Body/Pad" in str(node)
        assert "PartDesign::Pad" in str(node)


class TestSnapshot:
    """Tests for the Snapshot class."""

    def test_creation(self):
        """Test snapshot creation."""
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp)
        assert snapshot.document_name == "TestDocument"
        assert snapshot.timestamp == timestamp

    def test_with_root_nodes(self):
        """Test snapshot with root nodes."""
        node = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp, root_nodes=[node])
        assert len(snapshot.root_nodes) == 1

    def test_get_all_nodes(self):
        """Test getting all nodes recursively."""
        child = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", is_root=False)
        parent = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body", children=[child])
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp, root_nodes=[parent])
        all_nodes = snapshot.get_all_nodes()
        assert len(all_nodes) == 2

    def test_find_node_by_path(self):
        """Test finding a node by path."""
        child = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", is_root=False)
        parent = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body", children=[child])
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp, root_nodes=[parent])
        found = snapshot.find_node_by_path("Body/Pad")
        assert found is not None
        assert found.name == "Pad"

    def test_find_nonexistent_node(self):
        """Test finding a nonexistent node."""
        timestamp = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(document_name="TestDocument", timestamp=timestamp)
        found = snapshot.find_node_by_path("NonExistent")
        assert found is None

    def test_snapshot_sorting(self):
        """Test that snapshots can be sorted by timestamp."""
        ts1 = datetime(2024, 1, 1, 0, 0, 0)
        ts2 = datetime(2024, 1, 2, 0, 0, 0)
        ts3 = datetime(2024, 1, 1, 12, 0, 0)

        snapshot1 = Snapshot(document_name="TestDocument", timestamp=ts1)
        snapshot2 = Snapshot(document_name="TestDocument", timestamp=ts2)
        snapshot3 = Snapshot(document_name="TestDocument", timestamp=ts3)

        # Sort snapshots by timestamp
        sorted_snapshots = sorted([snapshot2, snapshot1, snapshot3], key=lambda s: s.timestamp)

        assert sorted_snapshots[0] == snapshot1  # Earliest
        assert sorted_snapshots[1] == snapshot3  # Middle
        assert sorted_snapshots[2] == snapshot2  # Latest


class TestDiffState:
    """Tests for the DiffState enum."""

    def test_states_exist(self):
        """Test that all states exist."""
        assert DiffState.ADDED is not None
        assert DiffState.DELETED is not None
        assert DiffState.MODIFIED is not None
        assert DiffState.UNCHANGED is not None


class TestPropertyDiff:
    """Tests for the PropertyDiff class."""

    def test_added_property(self):
        """Test added property diff - state auto-calculated."""
        new_val = PropertyValue.create(PropertyType.FLOAT, 10.0)
        diff = PropertyDiff(property_name="Length", old_value=None, new_value=new_val)
        assert diff.state == DiffState.ADDED
        assert "+10.0" in str(diff)

    def test_deleted_property(self):
        """Test deleted property diff - state auto-calculated."""
        old_val = PropertyValue.create(PropertyType.FLOAT, 5.0)
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=None)
        assert diff.state == DiffState.DELETED
        assert "-5.0" in str(diff)

    def test_modified_property(self):
        """Test modified property diff - state auto-calculated."""
        old_val = PropertyValue.create(PropertyType.FLOAT, 5.0)
        new_val = PropertyValue.create(PropertyType.FLOAT, 10.0)
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED
        assert "5.0 -> 10.0" in str(diff)

    def test_unchanged_property(self):
        """Test unchanged property diff - state auto-calculated."""
        val = PropertyValue.create(PropertyType.FLOAT, 10.0)
        diff = PropertyDiff(property_name="Length", old_value=val, new_value=val)
        assert diff.state == DiffState.UNCHANGED

    # =====================================================================
    # Expression Change Tests in PropertyDiff
    # =====================================================================

    def test_expression_only_change_detected(self):
        """Test that expression-only change is detected as modified."""
        old_val = PropertyValue.create(PropertyType.FLOAT, 10.0)
        new_val = PropertyValue.create(PropertyType.FLOAT, 10.0, expression="Sketch001.X")
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED
        assert "10.0 -> 10.0" in str(diff)  # Values same but expression changed

    def test_value_only_change_detected(self):
        """Test that value-only change is detected as modified."""
        old_val = PropertyValue.create(PropertyType.INT, 10, expression="Sketch001.Count")
        new_val = PropertyValue.create(PropertyType.INT, 20, expression="Sketch001.Count")
        diff = PropertyDiff(property_name="Count", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED
        # String format: "Count: 10 (via Sketch001.Count) -> 20 (via Sketch001.Count)"
        assert "Count:" in str(diff)
        assert "10" in str(diff)
        assert "20" in str(diff)

    def test_both_expression_and_value_change(self):
        """Test that both expression and value change is detected."""
        old_val = PropertyValue.create(PropertyType.FLOAT, 5.0, expression="Sketch001.X")
        new_val = PropertyValue.create(PropertyType.FLOAT, 15.0, expression="Sketch002.Y")
        diff = PropertyDiff(property_name="Dimension", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED
        # String format includes property name, values, and expressions
        assert "Dimension:" in str(diff)
        assert "5.0" in str(diff)
        assert "15.0" in str(diff)
        assert "Sketch001.X" in str(diff)
        assert "Sketch002.Y" in str(diff)

    def test_expression_changed_to_none(self):
        """Test that removing an expression is detected as modified."""
        old_val = PropertyValue.create(PropertyType.STRING, "test", expression="Doc.Name")
        new_val = PropertyValue.create(PropertyType.STRING, "test")
        diff = PropertyDiff(property_name="Name", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED

    def test_expression_added_from_none(self):
        """Test that adding an expression is detected as modified."""
        old_val = PropertyValue.create(PropertyType.INT, 42)
        new_val = PropertyValue.create(PropertyType.INT, 42, expression="Some.Expr")
        diff = PropertyDiff(property_name="Value", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED

    def test_different_expressions_same_value(self):
        """Test different expressions with same value detected as modified."""
        old_val = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch001.X")
        new_val = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch002.X")
        diff = PropertyDiff(property_name="Position", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED


class TestNodeDiff:
    """Tests for the NodeDiff class."""

    def test_creation(self):
        """Test node diff creation - state auto-calculated from empty property_diffs and children."""
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad")
        assert diff.path == "Body/Pad"
        # With no property diffs or children, state should be UNCHANGED
        assert diff.state == DiffState.UNCHANGED

    def test_state_auto_calculated_from_property_diffs(self):
        """Test that state is auto-calculated based on property diffs."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=PropertyValue.create(PropertyType.FLOAT, 5.0),
            new_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
        )
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[prop_diff])
        # State should be MODIFIED because there's a changed property
        assert diff.state == DiffState.MODIFIED
        assert diff.has_changes is True

    def test_state_auto_calculated_unchanged(self):
        """Test that state is UNCHANGED when no property diffs."""
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[])
        assert diff.state == DiffState.UNCHANGED
        assert diff.has_changes is False

    def test_has_changes_with_property_diffs(self):
        """Test has_changes when there are property diffs."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=PropertyValue.create(PropertyType.FLOAT, 5.0),
            new_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
        )
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[prop_diff])
        assert diff.has_changes is True

    def test_changed_properties(self):
        """Test getting only changed properties."""
        changed = PropertyDiff(
            property_name="Length",
            old_value=PropertyValue.create(PropertyType.FLOAT, 5.0),
            new_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
        )
        unchanged = PropertyDiff(
            property_name="Type",
            old_value=PropertyValue.create(PropertyType.STRING, "Dimension"),
            new_value=PropertyValue.create(PropertyType.STRING, "Dimension"),
        )
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[changed, unchanged])
        changed_props = diff.changed_properties
        assert len(changed_props) == 1
        assert changed_props[0].property_name == "Length"


class TestDiffSummary:
    """Tests for the DiffSummary class."""

    def test_empty_summary(self):
        """Test empty summary."""
        summary = DiffSummary()
        assert summary.total_nodes == 0
        assert summary.added_nodes == 0

    def test_string_representation(self):
        """Test string representation."""
        summary = DiffSummary(added_nodes=2, deleted_nodes=1, modified_nodes=3, unchanged_nodes=10)
        str_repr = str(summary)
        assert "2 added" in str_repr
        assert "1 deleted" in str_repr


class TestDiffResult:
    """Tests for the DiffResult class."""

    def test_creation(self):
        """Test diff result creation."""
        diff = DiffResult(old_snapshot_name="v1", new_snapshot_name="v2")
        assert diff.old_snapshot_name == "v1"
        assert diff.new_snapshot_name == "v2"

    def test_has_changes_false(self):
        """Test has_changes when no changes."""
        diff = DiffResult(old_snapshot_name="v1", new_snapshot_name="v2")
        assert diff.has_changes is False

    def test_has_changes_true(self):
        """Test has_changes when there are changes."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
            new_value=PropertyValue.create(PropertyType.FLOAT, 20.0),
        )
        node_diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[prop_diff])
        diff = DiffResult(old_snapshot_name="v1", new_snapshot_name="v2", node_diffs=[node_diff])
        assert diff.has_changes is True

    def test_get_all_changed_paths(self):
        """Test getting all changed paths."""
        child_prop = PropertyDiff(
            property_name="Width",
            old_value=PropertyValue.create(PropertyType.FLOAT, 5.0),
            new_value=PropertyValue.create(PropertyType.FLOAT, 15.0),
        )
        child = NodeDiff(path="Body/Pad/Sub", type_id="Part::Feature", property_diffs=[child_prop])
        parent_prop = PropertyDiff(
            property_name="Length",
            old_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
            new_value=PropertyValue.create(PropertyType.FLOAT, 20.0),
        )
        parent = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[parent_prop], children=[child])
        unchanged = NodeDiff(path="Body", type_id="PartDesign::Body")

        diff = DiffResult(old_snapshot_name="v1", new_snapshot_name="v2", node_diffs=[parent, unchanged])

        changed_paths = diff.get_all_changed_paths()
        assert "Body/Pad/Sub" in changed_paths
        assert "Body/Pad" in changed_paths  # Parent included because child changed
        assert "Body" not in changed_paths  # Unchanged with no changed children
