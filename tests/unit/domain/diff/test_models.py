# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the domain diff models module.
"""Unit tests for domain diff models."""

from freecad.diff_wb.domain.diff.models import WARNING_OLD_SNAPSHOT_MISSING, DiffState, PropertyDiff
from freecad.diff_wb.domain.tree import Property, PropertyType


class TestPropertyDiffChildren:
    """Tests for PropertyDiff children computation."""

    def test_property_diff_computes_children(self):
        """PropertyDiff has children after creation for expandable properties."""
        # Create a Placement property with Position and Rotation
        old_placement = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)},
        )
        new_placement = Property.create(
            PropertyType.PLACEMENT,
            {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=old_placement,
            new_value=new_placement,
        )

        # Should have Position and Rotation children
        assert len(prop_diff.children) == 2
        child_names = {child.property_name for child in prop_diff.children}
        assert child_names == {"Position", "Rotation"}

    def test_property_diff_no_children_for_primitives(self):
        """Primitive properties have empty children."""
        old_value = Property.create(PropertyType.FLOAT, 10.0)
        new_value = Property.create(PropertyType.FLOAT, 20.0)

        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=old_value,
            new_value=new_value,
        )

        assert prop_diff.children == []

    def test_property_diff_no_children_for_string(self):
        """String properties have empty children."""
        old_value = Property.create(PropertyType.STRING, "hello")
        new_value = Property.create(PropertyType.STRING, "world")

        prop_diff = PropertyDiff(
            property_name="Label",
            old_value=old_value,
            new_value=new_value,
        )

        assert prop_diff.children == []

    def test_property_diff_children_states_unchanged(self):
        """Children have correct UNCHANGED state when values are equal."""
        old_placement = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)},
        )
        new_placement = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)},
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=old_placement,
            new_value=new_placement,
        )

        # Parent should be UNCHANGED
        assert prop_diff.state == DiffState.UNCHANGED

        # All children should also be UNCHANGED
        for child in prop_diff.children:
            assert child.state == DiffState.UNCHANGED

    def test_property_diff_children_states_modified(self):
        """Children have correct MODIFIED state when values differ."""
        old_placement = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)},
        )
        new_placement = Property.create(
            PropertyType.PLACEMENT,
            {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)},
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=old_placement,
            new_value=new_placement,
        )

        # Parent should be MODIFIED
        assert prop_diff.state == DiffState.MODIFIED

        # Position should be MODIFIED
        position_child = next(c for c in prop_diff.children if c.property_name == "Position")
        assert position_child.state == DiffState.MODIFIED

        # Rotation should be UNCHANGED
        rotation_child = next(c for c in prop_diff.children if c.property_name == "Rotation")
        assert rotation_child.state == DiffState.UNCHANGED

    def test_property_diff_children_added(self):
        """Children have ADDED state when property is new."""
        new_placement = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)},
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=None,
            new_value=new_placement,
        )

        # Parent should be ADDED
        assert prop_diff.state == DiffState.ADDED

        # Children should also be ADDED
        for child in prop_diff.children:
            assert child.state == DiffState.ADDED

    def test_property_diff_children_deleted(self):
        """Children have DELETED state when property is removed."""
        old_placement = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)},
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=old_placement,
            new_value=None,
        )

        # Parent should be DELETED
        assert prop_diff.state == DiffState.DELETED

        # Children should also be DELETED
        for child in prop_diff.children:
            assert child.state == DiffState.DELETED

    def test_property_diff_vector_children(self):
        """Vector properties have x, y, z children."""
        old_vector = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_vector = Property.create(PropertyType.VECTOR, (4.0, 5.0, 6.0))

        prop_diff = PropertyDiff(
            property_name="Position",
            old_value=old_vector,
            new_value=new_vector,
        )

        # Should have x, y, z children
        assert len(prop_diff.children) == 3
        child_names = {child.property_name for child in prop_diff.children}
        assert child_names == {"x", "y", "z"}

        # All should be MODIFIED since values differ
        for child in prop_diff.children:
            assert child.state == DiffState.MODIFIED

    def test_property_diff_both_none(self):
        """PropertyDiff handles None for both old and new values."""
        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=None,
            new_value=None,
        )

        # Both None - since old is None, it defaults to ADDED state
        # (this is consistent with the current behavior)
        assert prop_diff.state == DiffState.ADDED
        assert prop_diff.children == []

    def test_property_diff_children_empty_both_sides(self):
        """PropertyDiff handles both sides having no children."""
        old_value = Property.create(PropertyType.STRING, "hello")
        new_value = Property.create(PropertyType.STRING, "world")

        prop_diff = PropertyDiff(
            property_name="Label",
            old_value=old_value,
            new_value=new_value,
        )

        assert prop_diff.children == []
        assert prop_diff.state == DiffState.MODIFIED


class TestWarningConstants:
    """Tests for warning constants in diff models."""

    def test_warning_old_snapshot_missing_exists(self):
        """Warning constant for missing old snapshot is defined."""
        # The constant should be importable and accessible
        assert WARNING_OLD_SNAPSHOT_MISSING is not None

    def test_warning_old_snapshot_missing_exact_value(self):
        """Warning constant equals expected string exactly."""
        assert WARNING_OLD_SNAPSHOT_MISSING == "Old snapshot missing"

    def test_warning_old_snapshot_missing_is_non_empty_descriptive(self):
        """Warning string is non-empty and descriptive."""
        # Check that the warning string is non-empty
        assert isinstance(WARNING_OLD_SNAPSHOT_MISSING, str)
        assert len(WARNING_OLD_SNAPSHOT_MISSING) > 0

        # Check that it contains descriptive text
        assert "old" in WARNING_OLD_SNAPSHOT_MISSING.lower() or "snapshot" in WARNING_OLD_SNAPSHOT_MISSING.lower()
