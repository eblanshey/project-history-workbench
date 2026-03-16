# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for property_diff module.

File responsibility: Tests for type-aware property comparison logic.
These tests verify property-level diff computation without any FreeCAD dependencies.
"""

from freecad.diff_wb.diff.diff_result import DiffState, PropertyDiff
from freecad.diff_wb.diff.property_diff import (
    compare_properties,
    should_exclude_property,
    values_are_equal,
)
from freecad.diff_wb.domain.property_value import PropertyType, PropertyValue


class TestValuesAreEqual:
    """Tests for values_are_equal function."""

    def test_both_none(self):
        """Test that None vs None returns True."""
        assert values_are_equal(None, None) is True

    def test_old_none_new_value(self):
        """Test that None vs value returns False."""
        new_val = PropertyValue.create(PropertyType.STRING, "test")
        assert values_are_equal(None, new_val) is False

    def test_old_value_new_none(self):
        """Test that value vs None returns False."""
        old_val = PropertyValue.create(PropertyType.STRING, "test")
        assert values_are_equal(old_val, None) is False

    def test_identical_bool_values(self):
        """Test BOOL type with same values."""
        old_val = PropertyValue.create(PropertyType.BOOL, True)
        new_val = PropertyValue.create(PropertyType.BOOL, True)
        assert values_are_equal(old_val, new_val) is True

    def test_different_bool_values(self):
        """Test BOOL type with different values."""
        old_val = PropertyValue.create(PropertyType.BOOL, True)
        new_val = PropertyValue.create(PropertyType.BOOL, False)
        assert values_are_equal(old_val, new_val) is False

    def test_identical_int_values(self):
        """Test INT type with same values."""
        old_val = PropertyValue.create(PropertyType.INT, 42)
        new_val = PropertyValue.create(PropertyType.INT, 42)
        assert values_are_equal(old_val, new_val) is True

    def test_different_int_values(self):
        """Test INT type with different values."""
        old_val = PropertyValue.create(PropertyType.INT, 42)
        new_val = PropertyValue.create(PropertyType.INT, 43)
        assert values_are_equal(old_val, new_val) is False

    def test_identical_float_values(self):
        """Test FLOAT type with same values."""
        old_val = PropertyValue.create(PropertyType.FLOAT, 3.14)
        new_val = PropertyValue.create(PropertyType.FLOAT, 3.14)
        assert values_are_equal(old_val, new_val) is True

    def test_different_float_values(self):
        """Test FLOAT type with different values."""
        old_val = PropertyValue.create(PropertyType.FLOAT, 3.14)
        new_val = PropertyValue.create(PropertyType.FLOAT, 2.71)
        assert values_are_equal(old_val, new_val) is False

    def test_float_within_tolerance(self):
        """Test FLOAT type with values within tolerance (1e-9)."""
        old_val = PropertyValue.create(PropertyType.FLOAT, 1.0)
        new_val = PropertyValue.create(PropertyType.FLOAT, 1.0 + 1e-10)
        assert values_are_equal(old_val, new_val) is True

    def test_float_exceeds_tolerance(self):
        """Test FLOAT type with values exceeding tolerance (1e-9)."""
        old_val = PropertyValue.create(PropertyType.FLOAT, 1.0)
        new_val = PropertyValue.create(PropertyType.FLOAT, 1.0 + 1e-8)
        assert values_are_equal(old_val, new_val) is False

    def test_identical_string_values(self):
        """Test STRING type with same values."""
        old_val = PropertyValue.create(PropertyType.STRING, "hello")
        new_val = PropertyValue.create(PropertyType.STRING, "hello")
        assert values_are_equal(old_val, new_val) is True

    def test_different_string_values(self):
        """Test STRING type with different values."""
        old_val = PropertyValue.create(PropertyType.STRING, "hello")
        new_val = PropertyValue.create(PropertyType.STRING, "world")
        assert values_are_equal(old_val, new_val) is False

    def test_identical_vector_values(self):
        """Test VECTOR type with same values."""
        old_val = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_val = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        assert values_are_equal(old_val, new_val) is True

    def test_different_vector_values(self):
        """Test VECTOR type with different values."""
        old_val = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_val = PropertyValue.create(PropertyType.VECTOR, (4.0, 5.0, 6.0))
        assert values_are_equal(old_val, new_val) is False

    def test_vector_within_tolerance(self):
        """Test VECTOR type with components within tolerance."""
        old_val = PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_val = PropertyValue.create(PropertyType.VECTOR, (1.0 + 1e-10, 2.0, 3.0))
        assert values_are_equal(old_val, new_val) is True

    def test_identical_placement_values(self):
        """Test PLACEMENT type with same values."""
        old_val = PropertyValue.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        new_val = PropertyValue.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        assert values_are_equal(old_val, new_val) is True

    def test_different_placement_values(self):
        """Test PLACEMENT type with different values."""
        old_val = PropertyValue.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        new_val = PropertyValue.create(
            PropertyType.PLACEMENT,
            {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        assert values_are_equal(old_val, new_val) is False

    def test_identical_link_values(self):
        """Test LINK type with same values."""
        old_val = PropertyValue.create(PropertyType.LINK, "Body")
        new_val = PropertyValue.create(PropertyType.LINK, "Body")
        assert values_are_equal(old_val, new_val) is True

    def test_different_link_values(self):
        """Test LINK type with different values."""
        old_val = PropertyValue.create(PropertyType.LINK, "Body")
        new_val = PropertyValue.create(PropertyType.LINK, "Cube")
        assert values_are_equal(old_val, new_val) is False

    def test_identical_expression_values(self):
        """Test STRING type with same values and identical expressions."""
        old_val = PropertyValue.create(PropertyType.STRING, "Body.Length", expression="Body.Length")
        new_val = PropertyValue.create(PropertyType.STRING, "Body.Length", expression="Body.Length")
        assert values_are_equal(old_val, new_val) is True

    def test_different_expression_values(self):
        """Test STRING type with different values and different expressions."""
        old_val = PropertyValue.create(PropertyType.STRING, "Body.Length", expression="Body.Length")
        new_val = PropertyValue.create(PropertyType.STRING, "Cube.Size", expression="Cube.Size")
        assert values_are_equal(old_val, new_val) is False

    def test_same_value_different_expression(self):
        """Test that same value with different expression returns False."""
        old_val = PropertyValue.create(PropertyType.FLOAT, 10.0, expression="Body.Length")
        new_val = PropertyValue.create(PropertyType.FLOAT, 10.0, expression="Cube.Size")
        assert values_are_equal(old_val, new_val) is False


class TestPropertyDiffState:
    """Tests for PropertyDiff state calculation."""

    def test_state_added(self):
        """Test ADDED state when old_value is None."""
        prop_diff = PropertyDiff(
            property_name="NewProperty",
            old_value=None,
            new_value=PropertyValue.create(PropertyType.STRING, "value"),
        )
        assert prop_diff.state == DiffState.ADDED

    def test_state_deleted(self):
        """Test DELETED state when new_value is None."""
        prop_diff = PropertyDiff(
            property_name="OldProperty",
            old_value=PropertyValue.create(PropertyType.STRING, "value"),
            new_value=None,
        )
        assert prop_diff.state == DiffState.DELETED

    def test_state_modified(self):
        """Test MODIFIED state when values differ."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
            new_value=PropertyValue.create(PropertyType.FLOAT, 20.0),
        )
        assert prop_diff.state == DiffState.MODIFIED

    def test_state_unchanged(self):
        """Test UNCHANGED state when values are equal."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
            new_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
        )
        assert prop_diff.state == DiffState.UNCHANGED

    def test_state_modified_same_value_different_expression(self):
        """Test MODIFIED state when values are same but expressions differ."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=PropertyValue.create(PropertyType.FLOAT, 10.0, expression="Body.Length"),
            new_value=PropertyValue.create(PropertyType.FLOAT, 10.0, expression="Cube.Size"),
        )
        assert prop_diff.state == DiffState.MODIFIED


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
            "NewProp1": PropertyValue.create(PropertyType.STRING, "value1"),
            "NewProp2": PropertyValue.create(PropertyType.INT, 42),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.ADDED

    def test_only_deletions(self):
        """Test when all properties are removed (deleted)."""
        old_props = {
            "OldProp1": PropertyValue.create(PropertyType.STRING, "value1"),
            "OldProp2": PropertyValue.create(PropertyType.INT, 42),
        }
        new_props = {}
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.DELETED

    def test_only_modifications(self):
        """Test when all properties are modified."""
        old_props = {
            "Prop1": PropertyValue.create(PropertyType.FLOAT, 10.0),
            "Prop2": PropertyValue.create(PropertyType.STRING, "old"),
        }
        new_props = {
            "Prop1": PropertyValue.create(PropertyType.FLOAT, 20.0),
            "Prop2": PropertyValue.create(PropertyType.STRING, "new"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.MODIFIED

    def test_only_unchanged_filtered_out(self):
        """Test that unchanged properties are filtered out."""
        old_props = {
            "Prop1": PropertyValue.create(PropertyType.FLOAT, 10.0),
            "Prop2": PropertyValue.create(PropertyType.STRING, "same"),
        }
        new_props = {
            "Prop1": PropertyValue.create(PropertyType.FLOAT, 10.0),
            "Prop2": PropertyValue.create(PropertyType.STRING, "same"),
        }
        result = compare_properties(old_props, new_props)
        assert result == []

    def test_mixed_changes(self):
        """Test combination of added, deleted, and modified properties."""
        old_props = {
            "DeletedProp": PropertyValue.create(PropertyType.STRING, "gone"),
            "ModifiedProp": PropertyValue.create(PropertyType.FLOAT, 10.0),
            "UnchangedProp": PropertyValue.create(PropertyType.INT, 5),
        }
        new_props = {
            "AddedProp": PropertyValue.create(PropertyType.STRING, "new"),
            "ModifiedProp": PropertyValue.create(PropertyType.FLOAT, 20.0),
            "UnchangedProp": PropertyValue.create(PropertyType.INT, 5),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 3

        states = {prop_diff.property_name: prop_diff.state for prop_diff in result}
        assert states["DeletedProp"] == DiffState.DELETED
        assert states["AddedProp"] == DiffState.ADDED
        assert states["ModifiedProp"] == DiffState.MODIFIED

    def test_excludes_time_stamp(self):
        """Test that TimeStamp property is filtered out."""
        old_props = {
            "TimeStamp": PropertyValue.create(PropertyType.STRING, "2024-01-01T00:00:00"),
            "Length": PropertyValue.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "TimeStamp": PropertyValue.create(PropertyType.STRING, "2024-01-01T00:00:01"),
            "Length": PropertyValue.create(PropertyType.FLOAT, 10.0),
        }
        result = compare_properties(old_props, new_props)
        # Only Length should appear (and it's unchanged, so filtered)
        assert len(result) == 0
        assert not any(p.property_name == "TimeStamp" for p in result)

    def test_excludes_label2(self):
        """Test that Label2 property is filtered out."""
        old_props = {
            "Label2": PropertyValue.create(PropertyType.STRING, "AutoLabel"),
            "Length": PropertyValue.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Label2": PropertyValue.create(PropertyType.STRING, "NewLabel"),
            "Length": PropertyValue.create(PropertyType.FLOAT, 20.0),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert not any(p.property_name == "Label2" for p in result)

    def test_all_property_types(self):
        """Test comparison of all property types in a single call."""
        old_props = {
            "BoolProp": PropertyValue.create(PropertyType.BOOL, True),
            "IntProp": PropertyValue.create(PropertyType.INT, 42),
            "FloatProp": PropertyValue.create(PropertyType.FLOAT, 3.14),
            "StringProp": PropertyValue.create(PropertyType.STRING, "hello"),
            "VectorProp": PropertyValue.create(PropertyType.VECTOR, (1.0, 2.0, 3.0)),
            "PlacementProp": PropertyValue.create(
                PropertyType.PLACEMENT, {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}
            ),
            "LinkProp": PropertyValue.create(PropertyType.LINK, "Body"),
        }
        new_props = {
            "BoolProp": PropertyValue.create(PropertyType.BOOL, False),  # Changed
            "IntProp": PropertyValue.create(PropertyType.INT, 42),  # Same
            "FloatProp": PropertyValue.create(PropertyType.FLOAT, 2.71),  # Changed
            "StringProp": PropertyValue.create(PropertyType.STRING, "world"),  # Changed
            "VectorProp": PropertyValue.create(PropertyType.VECTOR, (4.0, 5.0, 6.0)),  # Changed
            "PlacementProp": PropertyValue.create(
                PropertyType.PLACEMENT, {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}
            ),  # Changed
            "LinkProp": PropertyValue.create(PropertyType.LINK, "Cube"),  # Changed
        }
        result = compare_properties(old_props, new_props)

        assert len(result) == 6  # All except IntProp which is unchanged

        prop_names = {p.property_name for p in result}
        assert prop_names == {"BoolProp", "FloatProp", "StringProp", "VectorProp", "PlacementProp", "LinkProp"}

        # Verify all are MODIFIED
        for prop_diff in result:
            assert prop_diff.state == DiffState.MODIFIED

    def test_float_tolerance_edge_cases(self):
        """Test float tolerance with various edge cases."""
        # Very small difference within tolerance
        old_props = {
            "FloatProp": PropertyValue.create(PropertyType.FLOAT, 1.0),
        }
        new_props = {
            "FloatProp": PropertyValue.create(PropertyType.FLOAT, 1.0 + 1e-10),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 0  # Within tolerance, so unchanged

        # Difference exceeding tolerance
        new_props_exceed = {
            "FloatProp": PropertyValue.create(PropertyType.FLOAT, 1.0 + 1e-8),
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
            new_value=PropertyValue.create(PropertyType.STRING, "value"),
        )
        assert "+value" in str(added)

        # DELETED
        deleted = PropertyDiff(
            property_name="OldProp",
            old_value=PropertyValue.create(PropertyType.STRING, "value"),
            new_value=None,
        )
        assert "-value" in str(deleted)

        # MODIFIED
        modified = PropertyDiff(
            property_name="Length",
            old_value=PropertyValue.create(PropertyType.FLOAT, 10.0),
            new_value=PropertyValue.create(PropertyType.FLOAT, 20.0),
        )
        assert "10.0" in str(modified)
        assert "20.0" in str(modified)
        assert "->" in str(modified)

    def test_same_value_different_expression_is_modified(self):
        """Test that same value with different expression returns MODIFIED."""
        old_props = {
            "Length": PropertyValue.create(PropertyType.FLOAT, 10.0, expression="Body.Length"),
        }
        new_props = {
            "Length": PropertyValue.create(PropertyType.FLOAT, 10.0, expression="Cube.Size"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].state == DiffState.MODIFIED
