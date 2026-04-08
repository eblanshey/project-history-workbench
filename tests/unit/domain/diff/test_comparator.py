# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for the tree-comparison algorithm with path-based indexing.
"""Unit tests for tree_diff module.

These tests verify the core diff computation logic without any FreeCAD dependencies.
"""

from datetime import datetime

from freecad.diff_wb.config import EXCLUDED_PROPERTIES
from freecad.diff_wb.domain.diff.comparator import PropertyComparator, TreeComparator
from freecad.diff_wb.domain.diff.models import DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.tree import Property, PropertyType
from freecad.diff_wb.domain.tree.node import TreeNode


# Test fixtures - create comparator instances
_tree_comparator = TreeComparator()
_property_comparator = PropertyComparator()


def compare_properties(old_props, new_props):
    """Wrapper with default excluded_properties."""
    return _property_comparator.compare_properties(old_props, new_props, EXCLUDED_PROPERTIES)


should_exclude_property = _property_comparator._should_exclude_property
values_are_equal = _property_comparator._values_are_equal


class TestGetParentPath:
    """Tests for _get_parent_path method."""

    def test_parent_with_leading_slash(self):
        """Test extracting parent from path with leading slash."""
        result = _tree_comparator._get_parent_path("/Body/Pad")
        assert result == "/Body"

    def test_parent_without_leading_slash(self):
        """Test extracting parent from path without leading slash."""
        result = _tree_comparator._get_parent_path("Body/Pad")
        assert result == "Body"

    def test_root_with_leading_slash_returns_empty(self):
        """Test that root node with leading slash returns empty string."""
        result = _tree_comparator._get_parent_path("/Part")
        assert result == ""

    def test_root_without_leading_slash_returns_empty(self):
        """Test that root node without leading slash returns empty string."""
        result = _tree_comparator._get_parent_path("Part")
        assert result == ""

    def test_deep_nesting_with_leading_slash(self):
        """Test extracting parent from deeply nested path with leading slash."""
        result = _tree_comparator._get_parent_path("/A/B/C/D")
        assert result == "/A/B/C"

    def test_deep_nesting_without_leading_slash(self):
        """Test extracting parent from deeply nested path without leading slash."""
        result = _tree_comparator._get_parent_path("A/B/C/D")
        assert result == "A/B/C"

    def test_two_level_path_with_leading_slash(self):
        """Test extracting parent from two-level path with leading slash."""
        result = _tree_comparator._get_parent_path("/Body/Pad/Sketch")
        assert result == "/Body/Pad"

    def test_two_level_path_without_leading_slash(self):
        """Test extracting parent from two-level path without leading slash."""
        result = _tree_comparator._get_parent_path("Body/Pad/Sketch")
        assert result == "Body/Pad"


class TestValuesAreEqual:
    """Tests for values_are_equal function."""

    def test_both_none(self):
        """Test that None vs None returns True."""
        assert values_are_equal(None, None) is True

    def test_old_none_new_value(self):
        """Test that None vs value returns False."""
        new_val = Property.create(PropertyType.STRING, "test")
        assert values_are_equal(None, new_val) is False

    def test_old_value_new_none(self):
        """Test that value vs None returns False."""
        old_val = Property.create(PropertyType.STRING, "test")
        assert values_are_equal(old_val, None) is False

    def test_identical_bool_values(self):
        """Test BOOL type with same values."""
        old_val = Property.create(PropertyType.BOOL, True)
        new_val = Property.create(PropertyType.BOOL, True)
        assert values_are_equal(old_val, new_val) is True

    def test_different_bool_values(self):
        """Test BOOL type with different values."""
        old_val = Property.create(PropertyType.BOOL, True)
        new_val = Property.create(PropertyType.BOOL, False)
        assert values_are_equal(old_val, new_val) is False

    def test_identical_int_values(self):
        """Test INT type with same values."""
        old_val = Property.create(PropertyType.INT, 42)
        new_val = Property.create(PropertyType.INT, 42)
        assert values_are_equal(old_val, new_val) is True

    def test_different_int_values(self):
        """Test INT type with different values."""
        old_val = Property.create(PropertyType.INT, 42)
        new_val = Property.create(PropertyType.INT, 43)
        assert values_are_equal(old_val, new_val) is False

    def test_identical_float_values(self):
        """Test FLOAT type with same values."""
        old_val = Property.create(PropertyType.FLOAT, 3.14)
        new_val = Property.create(PropertyType.FLOAT, 3.14)
        assert values_are_equal(old_val, new_val) is True

    def test_different_float_values(self):
        """Test FLOAT type with different values."""
        old_val = Property.create(PropertyType.FLOAT, 3.14)
        new_val = Property.create(PropertyType.FLOAT, 2.71)
        assert values_are_equal(old_val, new_val) is False

    def test_float_within_tolerance(self):
        """Test FLOAT type with values within tolerance (1e-9)."""
        old_val = Property.create(PropertyType.FLOAT, 1.0)
        new_val = Property.create(PropertyType.FLOAT, 1.0 + 1e-10)
        assert values_are_equal(old_val, new_val) is True

    def test_float_exceeds_tolerance(self):
        """Test FLOAT type with values exceeding tolerance (1e-9)."""
        old_val = Property.create(PropertyType.FLOAT, 1.0)
        new_val = Property.create(PropertyType.FLOAT, 1.0 + 1e-8)
        assert values_are_equal(old_val, new_val) is False

    def test_identical_string_values(self):
        """Test STRING type with same values."""
        old_val = Property.create(PropertyType.STRING, "hello")
        new_val = Property.create(PropertyType.STRING, "hello")
        assert values_are_equal(old_val, new_val) is True

    def test_different_string_values(self):
        """Test STRING type with different values."""
        old_val = Property.create(PropertyType.STRING, "hello")
        new_val = Property.create(PropertyType.STRING, "world")
        assert values_are_equal(old_val, new_val) is False

    def test_identical_vector_values(self):
        """Test VECTOR type with same values."""
        old_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        assert values_are_equal(old_val, new_val) is True

    def test_different_vector_values(self):
        """Test VECTOR type with different values."""
        old_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_val = Property.create(PropertyType.VECTOR, (4.0, 5.0, 6.0))
        assert values_are_equal(old_val, new_val) is False

    def test_vector_within_tolerance(self):
        """Test VECTOR type with components within tolerance."""
        old_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_val = Property.create(PropertyType.VECTOR, (1.0 + 1e-10, 2.0, 3.0))
        assert values_are_equal(old_val, new_val) is True

    def test_identical_placement_values(self):
        """Test PLACEMENT type with same values."""
        old_val = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        new_val = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        assert values_are_equal(old_val, new_val) is True

    def test_different_placement_values(self):
        """Test PLACEMENT type with different values."""
        old_val = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        new_val = Property.create(
            PropertyType.PLACEMENT,
            {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        assert values_are_equal(old_val, new_val) is False

    def test_identical_expression_values(self):
        """Test STRING type with same values and identical expressions."""
        old_val = Property.create(PropertyType.STRING, "Body.Length", expression="Body.Length")
        new_val = Property.create(PropertyType.STRING, "Body.Length", expression="Body.Length")
        assert values_are_equal(old_val, new_val) is True

    def test_different_expression_values(self):
        """Test STRING type with different values and different expressions."""
        old_val = Property.create(PropertyType.STRING, "Body.Length", expression="Body.Length")
        new_val = Property.create(PropertyType.STRING, "Cube.Size", expression="Cube.Size")
        assert values_are_equal(old_val, new_val) is False

    def test_same_value_different_expression(self):
        """Test that same value with different expression returns False."""
        old_val = Property.create(PropertyType.FLOAT, 10.0, expression="Body.Length")
        new_val = Property.create(PropertyType.FLOAT, 10.0, expression="Cube.Size")
        assert values_are_equal(old_val, new_val) is False


class TestPropertyDiffState:
    """Tests for PropertyDiff state calculation."""

    def test_state_added(self):
        """Test ADDED state when old_value is None."""
        prop_diff = PropertyDiff(
            property_name="NewProperty",
            old_value=None,
            new_value=Property.create(PropertyType.STRING, "value"),
        )
        assert prop_diff.state == DiffState.ADDED

    def test_state_deleted(self):
        """Test DELETED state when new_value is None."""
        prop_diff = PropertyDiff(
            property_name="OldProperty",
            old_value=Property.create(PropertyType.STRING, "value"),
            new_value=None,
        )
        assert prop_diff.state == DiffState.DELETED

    def test_state_modified(self):
        """Test MODIFIED state when values differ."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0),
            new_value=Property.create(PropertyType.FLOAT, 20.0),
        )
        assert prop_diff.state == DiffState.MODIFIED

    def test_state_unchanged(self):
        """Test UNCHANGED state when values are equal."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0),
            new_value=Property.create(PropertyType.FLOAT, 10.0),
        )
        assert prop_diff.state == DiffState.UNCHANGED

    def test_state_unchanged_same_value_different_expression(self):
        """Test UNCHANGED state when values are same (expression tracked separately)."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0, expression="Body.Length"),
            new_value=Property.create(PropertyType.FLOAT, 10.0, expression="Cube.Size"),
        )
        assert prop_diff.state == DiffState.UNCHANGED


class TestCompareProperties:
    """Tests for compare_properties function."""

    def test_empty_dictionaries(self):
        """Test comparing empty property dictionaries."""
        result = compare_properties({}, {})
        assert result == []

    def test_only_additions(self):
        """Test when all properties are new (added)."""
        old_props = {}
        new_props = {
            "NewProp1": Property.create(PropertyType.STRING, "value1"),
            "NewProp2": Property.create(PropertyType.INT, 42),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.ADDED

    def test_only_deletions(self):
        """Test when all properties are removed (deleted)."""
        old_props = {
            "OldProp1": Property.create(PropertyType.STRING, "value1"),
            "OldProp2": Property.create(PropertyType.INT, 42),
        }
        new_props = {}
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.DELETED

    def test_only_modifications(self):
        """Test when all properties are modified."""
        old_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 10.0),
            "Prop2": Property.create(PropertyType.STRING, "old"),
        }
        new_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 20.0),
            "Prop2": Property.create(PropertyType.STRING, "new"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.MODIFIED

    def test_only_unchanged_included(self):
        """Test that unchanged properties are included in result."""
        old_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 10.0),
            "Prop2": Property.create(PropertyType.STRING, "same"),
        }
        new_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 10.0),
            "Prop2": Property.create(PropertyType.STRING, "same"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.UNCHANGED

    def test_mixed_changes(self):
        """Test combination of added, deleted, modified and unchanged properties."""
        old_props = {
            "DeletedProp": Property.create(PropertyType.STRING, "gone"),
            "ModifiedProp": Property.create(PropertyType.FLOAT, 10.0),
            "UnchangedProp": Property.create(PropertyType.INT, 5),
        }
        new_props = {
            "AddedProp": Property.create(PropertyType.STRING, "new"),
            "ModifiedProp": Property.create(PropertyType.FLOAT, 20.0),
            "UnchangedProp": Property.create(PropertyType.INT, 5),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 4

        states = {prop_diff.property_name: prop_diff.state for prop_diff in result}
        assert states["DeletedProp"] == DiffState.DELETED
        assert states["AddedProp"] == DiffState.ADDED
        assert states["ModifiedProp"] == DiffState.MODIFIED
        assert states["UnchangedProp"] == DiffState.UNCHANGED

    def test_excludes_time_stamp(self):
        """Test that TimeStamp property is filtered out."""
        old_props = {
            "TimeStamp": Property.create(PropertyType.STRING, "2024-01-01T00:00:00"),
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "TimeStamp": Property.create(PropertyType.STRING, "2024-01-01T00:00:01"),
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        result = compare_properties(old_props, new_props)
        # TimeStamp is excluded, Length is unchanged but included
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert result[0].state == DiffState.UNCHANGED

    def test_excludes_label2(self):
        """Test that Label2 property is filtered out."""
        old_props = {
            "Label2": Property.create(PropertyType.STRING, "AutoLabel"),
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Label2": Property.create(PropertyType.STRING, "NewLabel"),
            "Length": Property.create(PropertyType.FLOAT, 20.0),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert not any(p.property_name == "Label2" for p in result)

    def test_all_property_types(self):
        """Test comparison of all property types in a single call."""
        old_props = {
            "BoolProp": Property.create(PropertyType.BOOL, True),
            "IntProp": Property.create(PropertyType.INT, 42),
            "FloatProp": Property.create(PropertyType.FLOAT, 3.14),
            "StringProp": Property.create(PropertyType.STRING, "hello"),
            "VectorProp": Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0)),
            "PlacementProp": Property.create(
                PropertyType.PLACEMENT, {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}
            ),
        }
        new_props = {
            "BoolProp": Property.create(PropertyType.BOOL, False),  # Changed
            "IntProp": Property.create(PropertyType.INT, 42),  # Same
            "FloatProp": Property.create(PropertyType.FLOAT, 2.71),  # Changed
            "StringProp": Property.create(PropertyType.STRING, "world"),  # Changed
            "VectorProp": Property.create(PropertyType.VECTOR, (4.0, 5.0, 6.0)),  # Changed
            "PlacementProp": Property.create(
                PropertyType.PLACEMENT, {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}
            ),  # Changed
        }
        result = compare_properties(old_props, new_props)

        assert len(result) == 6  # All properties including unchanged IntProp

        prop_names = {p.property_name for p in result}
        assert prop_names == {"BoolProp", "IntProp", "FloatProp", "StringProp", "VectorProp", "PlacementProp"}

        # Verify modified are MODIFIED
        modified_props = [p for p in result if p.property_name != "IntProp"]
        for prop_diff in modified_props:
            assert prop_diff.state == DiffState.MODIFIED
        # Verify IntProp is unchanged
        assert next(p for p in result if p.property_name == "IntProp").state == DiffState.UNCHANGED

    def test_float_tolerance_edge_cases(self):
        """Test float tolerance with various edge cases."""
        # Very small difference within tolerance
        old_props = {
            "FloatProp": Property.create(PropertyType.FLOAT, 1.0),
        }
        new_props = {
            "FloatProp": Property.create(PropertyType.FLOAT, 1.0 + 1e-10),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1  # Within tolerance, so unchanged but included
        assert result[0].state == DiffState.UNCHANGED

        # Difference exceeding tolerance
        new_props_exceed = {
            "FloatProp": Property.create(PropertyType.FLOAT, 1.0 + 1e-8),
        }
        result_exceed = compare_properties(old_props, new_props_exceed)
        assert len(result_exceed) == 1
        assert result_exceed[0].state == DiffState.MODIFIED

    def test_property_diff_string_representation(self):
        """Test string representation of PropertyDiff objects."""
        # ADDED
        added = PropertyDiff(
            property_name="NewProp",
            old_value=None,
            new_value=Property.create(PropertyType.STRING, "value"),
        )
        assert "+value" in str(added)

        # DELETED
        deleted = PropertyDiff(
            property_name="OldProp",
            old_value=Property.create(PropertyType.STRING, "value"),
            new_value=None,
        )
        assert "-value" in str(deleted)

        # MODIFIED
        modified = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0),
            new_value=Property.create(PropertyType.FLOAT, 20.0),
        )
        assert "10.0" in str(modified)
        assert "20.0" in str(modified)
        assert "->" in str(modified)

    def test_same_value_different_expression_is_unchanged(self):
        """Test that same value with different expression returns UNCHANGED."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0, expression="Body.Length"),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0, expression="Cube.Size"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].state == DiffState.UNCHANGED


class TestPropertyDiffChildrenAutoComputed:
    """Tests verifying PropertyDiff auto-computes children for expandable properties.

    These tests verify that when the comparator creates PropertyDiff objects,
    the children are automatically populated by PropertyDiff's __post_init__ method.
    This is Phase 3 of the refactor-diff-architecture task.
    """

    def test_placement_property_diff_has_position_and_rotation_children(self):
        """Test that PropertyDiff for Placement has Position and Rotation children."""
        # Create two Placement properties that differ in position
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)

        assert len(result) == 1
        prop_diff = result[0]
        assert prop_diff.property_name == "Placement"
        assert prop_diff.state == DiffState.MODIFIED

        # Verify children are auto-computed
        assert len(prop_diff.children) == 2
        child_names = {child.property_name for child in prop_diff.children}
        assert "Position" in child_names
        assert "Rotation" in child_names

    def test_placement_property_diff_position_child_has_correct_state(self):
        """Test that Position child of Placement diff has MODIFIED state when position changes."""
        # Create two Placement properties with different positions
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        # Find Position child
        position_child = next(child for child in prop_diff.children if child.property_name == "Position")
        assert position_child.state == DiffState.MODIFIED

    def test_placement_property_diff_rotation_child_has_correct_state(self):
        """Test that Rotation child of Placement diff has MODIFIED state when rotation changes."""
        # Create two Placement properties with different rotations
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 45.0)},
            ),
        }
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        # Find Rotation child
        rotation_child = next(child for child in prop_diff.children if child.property_name == "Rotation")
        assert rotation_child.state == DiffState.MODIFIED

    def test_unchanged_placement_has_unchanged_children(self):
        """Test that unchanged Placement has UNCHANGED children."""
        # Create identical Placement properties
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.UNCHANGED

        # Both children should be UNCHANGED
        for child in prop_diff.children:
            assert child.state == DiffState.UNCHANGED

    def test_primitive_property_has_empty_children(self):
        """Test that primitive property (e.g., FLOAT) has empty children list."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 20.0),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.MODIFIED
        # Primitive types have no children
        assert len(prop_diff.children) == 0

    def test_vector_property_has_x_y_z_children(self):
        """Test that VECTOR property has x, y, z children."""
        old_props = {
            "Position": Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0)),
        }
        new_props = {
            "Position": Property.create(PropertyType.VECTOR, (4.0, 5.0, 6.0)),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.MODIFIED
        # Vector has x, y, z children
        assert len(prop_diff.children) == 3
        child_names = {child.property_name for child in prop_diff.children}
        assert child_names == {"x", "y", "z"}

    def test_added_placement_has_children(self):
        """Test that added Placement has Position and Rotation children with ADDED state."""
        old_props: dict[str, Property] = {}
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.ADDED

        # Children should also have ADDED state
        for child in prop_diff.children:
            assert child.state == DiffState.ADDED

    def test_deleted_placement_has_children(self):
        """Test that deleted Placement has Position and Rotation children with DELETED state."""
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }
        new_props: dict[str, Property] = {}

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.DELETED

        # Children should also have DELETED state
        for child in prop_diff.children:
            assert child.state == DiffState.DELETED


class TestCompareNodesById:
    """Tests for ID-based node comparison."""

    def test_identical_nodes_returns_unchanged(self):
        """Test comparing identical nodes returns UNCHANGED."""
        props = {
            "Label": Property.create(PropertyType.STRING, "Body"),
        }
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties=props,
        )
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties=props,
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        assert result is not None
        assert result.state == DiffState.UNCHANGED

    def test_modified_property_returns_modified(self):
        """Test detecting a modified property returns MODIFIED."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 20.0),
        }
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=old_props,
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=new_props,
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        assert result is not None
        assert result.state == DiffState.MODIFIED

    def test_includes_old_and_new_path_in_result(self):
        """Test that NodeDiff includes old_path and new_path."""
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        # NodeDiff should include old_path and new_path for move detection
        assert result.old_path == "Body/Pad"
        assert result.new_path == "Body/Pad"

    def test_includes_old_and_new_after_in_result(self):
        """Test that NodeDiff includes old_after and new_after."""
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        # NodeDiff should include old_after and new_after for reorder detection
        assert result.old_after == "Body"
        assert result.new_after == "Body"


class TestIdBasedCompareSnapshots:
    """Tests for ID-based snapshot comparison (end-to-end)."""

    def test_compare_two_flat_node_lists_by_id(self):
        """Test comparing two flat node lists by ID."""
        # Old snapshot has ID 1 only
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot has both ID 1 and ID 2
        new_node1 = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_node2 = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node1, new_node2],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        # ID 2 should be added, ID 1 unchanged
        assert result.added_count == 1
        assert result.deleted_count == 0
        assert result.modified_count == 0

    def test_detect_added_nodes(self):
        """Test detecting ADDED nodes (in new, not in old)."""
        # Old snapshot: only ID 1
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot: ID 1 and ID 2 (added)
        new_node1 = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_node2 = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node1, new_node2],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        assert result.added_count == 1
        assert result.deleted_count == 0
        assert result.modified_count == 0

    def test_detect_deleted_nodes(self):
        """Test detecting DELETED nodes (in old, not in new)."""
        # Old snapshot: ID 1 and ID 2
        old_node1 = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_node2 = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node1, old_node2],
        )

        # New snapshot: only ID 1
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 1
        assert result.modified_count == 0

    def test_detect_modified_nodes(self):
        """Test detecting MODIFIED nodes (in both, properties differ)."""
        # Old snapshot: ID 1 with Length=10
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={"Length": Property.create(PropertyType.FLOAT, 10.0)},
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot: ID 1 with Length=20 (modified)
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={"Length": Property.create(PropertyType.FLOAT, 20.0)},
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 0
        assert result.modified_count == 1

        # Find the node diff for ID 1 - it may be nested under parent placeholder
        # Look through the hierarchy for Body/Pad
        def find_node_diff(node_diffs, path):
            """Recursively find a NodeDiff by path."""
            for diff in node_diffs:
                if diff.path == path:
                    return diff
                found = find_node_diff(diff.children, path)
                if found:
                    return found
            return None

        pad_diff = find_node_diff(result.hierarchy.roots, "Body/Pad")
        assert pad_diff is not None
        assert pad_diff.state == DiffState.MODIFIED

    def test_id_based_comparison_produces_correct_sets(self):
        """Test ID-based comparison produces correct added/deleted/common sets."""
        # Old: IDs 1, 2, 3
        old_nodes = [
            TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", after="Body"),
            TreeNode(
                id=3, name="Sketch", type_id="PartDesign::Sketch", label="Sketch", path="Body/Sketch", after="Pad"
            ),
        ]
        # New: IDs 1, 2, 4 (2 unchanged, 1 modified, 3 deleted, 4 added)
        new_nodes = [
            TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            TreeNode(  # ID 2 modified (different properties)
                id=2,
                name="Pad",
                type_id="PartDesign::Pad",
                label="Pad",
                path="Body/Pad",
                after="Body",
                properties={"Length": Property.create(PropertyType.FLOAT, 20.0)},
            ),
            TreeNode(id=4, name="Box", type_id="Part::Box", label="Box", path="Box", after=None),  # Added
        ]

        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=old_nodes)
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=new_nodes)

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        # Correct counts: 1 added (ID 4), 1 deleted (ID 3), 1 modified (ID 2)
        assert result.added_count == 1
        assert result.deleted_count == 1
        assert result.modified_count == 1

    def test_node_diff_includes_path_and_after_for_move_detection(self):
        """Test NodeDiff includes old_path, new_path, old_after, new_after for future move/reorder detection."""
        # Old: ID 1 at path "Body/Original"
        old_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Body/Original",
            after="Body",
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New: Same ID but moved to different path "Body/Moved"
        new_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Body/Moved",
            after="Body",
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        # The NodeDiff should include old_path and new_path for move detection
        # Since the node is unchanged in properties but path changed
        # The node may be nested under a parent placeholder
        def find_node_diff(node_diffs, path):
            """Recursively find a NodeDiff by path."""
            for diff in node_diffs:
                if diff.path == path:
                    return diff
                found = find_node_diff(diff.children, path)
                if found:
                    return found
            return None

        feature_diff = find_node_diff(result.hierarchy.roots, "Body/Moved")
        assert feature_diff is not None
        assert feature_diff.old_path == "Body/Original"
        assert feature_diff.new_path == "Body/Moved"

    def test_node_diff_for_added_node_has_null_old_path(self):
        """Test that added node has None for old_path."""
        # New only: ID 2
        new_node = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        # Old is empty
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        # Added node should have old_path = None
        box_diff = result.hierarchy.roots[0]
        assert box_diff.old_path is None
        assert box_diff.new_path == "Box"

    def test_node_diff_for_deleted_node_has_null_new_path(self):
        """Test that deleted node has None for new_path."""
        # Old only: ID 1
        old_node = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New is empty
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        # Deleted node should have new_path = None
        box_diff = result.hierarchy.roots[0]
        assert box_diff.old_path == "Box"
        assert box_diff.new_path is None

    def test_hierarchical_output_preserved(self):
        """Test that hierarchical NodeDiff.children is preserved for UI."""
        # Create a parent-child relationship in flat nodes
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[body, pad])
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[body, pad])

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        # Should have hierarchical structure: Body -> Pad
        assert len(result.hierarchy.roots) == 1  # Root: Body
        body_diff = result.hierarchy.roots[0]
        assert len(body_diff.children) == 1  # Child: Pad
        assert body_diff.children[0].path == "Body/Pad"


class TestExcludedTypesFiltering:
    """Tests for excluded_types filtering in compare_snapshots."""

    def test_excludes_nodes_with_excluded_type(self):
        """Test that nodes with excluded type_id are filtered out."""
        # Old snapshot with App::Origin (excluded type)
        old_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot with same node
        new_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        # Pass App::Origin in excluded_types
        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], ["App::Origin"])

        # Origin node should be excluded
        assert len(result.hierarchy.roots) == 0
        assert result.added_count == 0
        assert result.deleted_count == 0
        assert result.modified_count == 0

    def test_excludes_children_of_excluded_type_parent(self):
        """Test that children of excluded type nodes are also filtered."""
        # Old snapshot with App::Origin and its child
        origin = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        xy_plane = TreeNode(
            id=2,
            name="XYPlane",
            type_id="App::Plane",
            label="XYPlane",
            path="Origin/XYPlane",
            after="Origin",
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[origin, xy_plane],
        )

        # New snapshot with same nodes
        new_origin = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        new_xy_plane = TreeNode(
            id=2,
            name="XYPlane",
            type_id="App::Plane",
            label="XYPlane",
            path="Origin/XYPlane",
            after="Origin",
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_origin, new_xy_plane],
        )

        # Pass App::Origin in excluded_types - should exclude both origin and its child
        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], ["App::Origin"])

        # Both nodes should be excluded
        assert len(result.hierarchy.roots) == 0

    def test_includes_nodes_not_in_excluded_types(self):
        """Test that nodes not in excluded_types are included."""
        # Old snapshot with Part::Feature
        old_node = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Feature",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot with same node
        new_node = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Feature",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        # Pass App::Origin in excluded_types (but our node is Part::Feature)
        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], ["App::Origin"])

        # Box node should be included
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].path == "Box"

    def test_excludes_added_nodes_with_excluded_type(self):
        """Test that added nodes with excluded type are filtered."""
        # Old snapshot is empty
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        # New snapshot with App::Origin (newly added)
        new_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], ["App::Origin"])

        # Should have no diffs (excluded)
        assert len(result.hierarchy.roots) == 0

    def test_excludes_deleted_nodes_with_excluded_type(self):
        """Test that deleted nodes with excluded type are filtered."""
        # Old snapshot with App::Origin (deleted)
        old_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot is empty
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], ["App::Origin"])

        # Should have no diffs (excluded)
        assert len(result.hierarchy.roots) == 0


class TestExcludedParentPathFiltering:
    """Tests for excluded parent path filtering in compare_snapshots."""

    def test_excludes_child_when_parent_excluded_by_type(self):
        """Test that child nodes are excluded when parent type is excluded."""
        # Old: Body -> Pad -> Sketch (Sketch will be excluded because parent Pad type is excluded)
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        sketch = TreeNode(
            id=3,
            name="Sketch",
            type_id="PartDesign::Sketch",
            label="Sketch",
            path="Body/Pad/Sketch",
            after="Pad",
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[body, pad, sketch],
        )

        # New: same nodes
        new_body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_sketch = TreeNode(
            id=3,
            name="Sketch",
            type_id="PartDesign::Sketch",
            label="Sketch",
            path="Body/Pad/Sketch",
            after="Pad",
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_body, new_pad, new_sketch],
        )

        # Exclude PartDesign::Pad (parent of Sketch)
        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], ["PartDesign::Pad"])

        # Body should be included (not excluded type), but Pad and Sketch should be excluded
        paths_in_result = {diff.path for diff in _flatten_diffs(result.hierarchy.roots)}
        assert "Body" in paths_in_result
        assert "Body/Pad" not in paths_in_result
        assert "Body/Pad/Sketch" not in paths_in_result

    def test_mixed_excluded_and_included_nodes(self):
        """Test that some nodes are excluded while others are included."""
        # Create nodes: Body with two children - one excluded, one included
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        # This Pad will be excluded
        pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        # This box will NOT be excluded (different parent)
        box = TreeNode(
            id=3,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[body, pad, box],
        )

        # New: same nodes
        new_body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_box = TreeNode(
            id=3,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_body, new_pad, new_box],
        )

        # Exclude PartDesign::Pad only
        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], ["PartDesign::Pad"])

        # Body and Box should be included, Pad should be excluded
        paths_in_result = {diff.path for diff in _flatten_diffs(result.hierarchy.roots)}
        assert "Body" in paths_in_result
        assert "Body/Pad" not in paths_in_result
        assert "Box" in paths_in_result


class TestEmptySnapshots:
    """Tests for handling empty snapshots in compare_snapshots."""

    def test_both_snapshots_empty_returns_empty(self):
        """Test that comparing two empty snapshots returns empty result."""
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 0
        assert result.modified_count == 0
        assert result.hierarchy.roots == []

    def test_old_empty_new_with_nodes_returns_added(self):
        """Test that when old is empty, new nodes are marked as added."""
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        new_box = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_box],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        assert result.added_count == 1
        assert result.deleted_count == 0
        assert result.modified_count == 0
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].state == DiffState.ADDED

    def test_new_empty_old_with_nodes_returns_deleted(self):
        """Test that when new is empty, old nodes are marked as deleted."""
        old_box = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_box],
        )

        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 1
        assert result.modified_count == 0
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].state == DiffState.DELETED

    def test_hierarchy_preserved_with_empty_parent(self):
        """Test that hierarchy is preserved when parent becomes empty."""
        # Old: Body with child Pad
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[body],
        )

        # New: empty (Body deleted)
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [], [])

        assert result.deleted_count == 1
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].path == "Body"
        assert result.hierarchy.roots[0].state == DiffState.DELETED


def _flatten_diffs(node_diffs: list[NodeDiff]) -> list[NodeDiff]:
    """Flatten a hierarchical list of NodeDiffs into a flat list."""
    result: list[NodeDiff] = []
    for diff in node_diffs:
        result.append(diff)
        if diff.children:
            result.extend(_flatten_diffs(diff.children))
    return result
