"""File responsibility: Unit tests for presentation models."""

import dataclasses
from dataclasses import is_dataclass

import pytest

from freecad.diff_wb.domain.diff.models import DiffState
from freecad.diff_wb.ui.presenters.presentation_models import (
    NodePresentation,
    PropertyPresentation,
    SnapshotPresentation,
)


class TestNodePresentation:
    """Tests for NodePresentation dataclass."""

    def test_node_presentation_is_frozen(self) -> None:
        """Verify immutability - frozen dataclass cannot be modified."""
        # Arrange
        node = NodePresentation(
            path="Part",
            type_id="Part::Feature",
            state=DiffState.MODIFIED,
            has_changes=True,
        )

        # Act & Assert - attempting to modify should raise FrozenInstanceError
        with pytest.raises(dataclasses.FrozenInstanceError):
            node.state = DiffState.UNCHANGED  # type: ignore[misc]

    def test_node_presentation_fields(self) -> None:
        """Verify all fields present in NodePresentation."""
        # Arrange & Act
        node = NodePresentation(
            path="Part/Body",
            type_id="PartDesign::Body",
            state=DiffState.ADDED,
            has_changes=False,
        )

        # Assert
        assert node.path == "Part/Body"
        assert node.type_id == "PartDesign::Body"
        assert node.state == DiffState.ADDED
        assert node.has_changes is False

    def test_node_presentation_accepts_children_list_parameter(self) -> None:
        """Verify NodePresentation accepts children list parameter."""
        # Arrange & Act
        child1 = NodePresentation(
            path="Part/Body/Pad",
            type_id="PartDesign::Pad",
            state=DiffState.UNCHANGED,
            has_changes=False,
        )
        child2 = NodePresentation(
            path="Part/Body/Pocket",
            type_id="PartDesign::Pocket",
            state=DiffState.MODIFIED,
            has_changes=True,
        )
        parent = NodePresentation(
            path="Part/Body",
            type_id="PartDesign::Body",
            state=DiffState.MODIFIED,
            has_changes=True,
            children=[child1, child2],
        )

        # Assert
        assert len(parent.children) == 2
        assert parent.children[0] == child1
        assert parent.children[1] == child2
        assert parent.children[0].path == "Part/Body/Pad"
        assert parent.children[1].path == "Part/Body/Pocket"

    def test_node_presentation_children_default_empty_list(self) -> None:
        """Verify children defaults to empty list when not provided."""
        # Arrange & Act
        node = NodePresentation(
            path="Part",
            type_id="Part::Feature",
            state=DiffState.UNCHANGED,
            has_changes=False,
        )

        # Assert
        assert node.children == []
        assert isinstance(node.children, list)

    def test_node_presentation_children_are_independent_instances(self) -> None:
        """Verify each instance gets its own children list (not shared)."""
        # Arrange & Act
        node1 = NodePresentation(
            path="Part1",
            type_id="Part::Feature",
            state=DiffState.UNCHANGED,
            has_changes=False,
        )
        node2 = NodePresentation(
            path="Part2",
            type_id="Part::Feature",
            state=DiffState.UNCHANGED,
            has_changes=False,
        )

        # Each should have its own list
        assert node1.children is not node2.children


class TestPropertyPresentation:
    """Tests for PropertyPresentation dataclass."""

    def test_property_presentation_is_frozen(self) -> None:
        """Verify immutability - frozen dataclass cannot be modified."""
        # Arrange
        prop = PropertyPresentation(
            name="Length",
            state=DiffState.MODIFIED,
        )

        # Act & Assert - attempting to modify should raise FrozenInstanceError
        with pytest.raises(dataclasses.FrozenInstanceError):
            prop.state = DiffState.UNCHANGED  # type: ignore[misc]

    def test_property_presentation_fields(self) -> None:
        """Verify all fields present in PropertyPresentation."""
        # Arrange & Act
        prop = PropertyPresentation(
            name="Width",
            state=DiffState.MODIFIED,
        )

        # Assert
        assert prop.name == "Width"
        assert prop.state == DiffState.MODIFIED

    def test_property_presentation_old_value_field(self) -> None:
        """Verify old_value field is present and can be set."""
        # Arrange & Act
        old_dict = {"x": 1.0, "y": 2.0}
        prop = PropertyPresentation(
            name="Vector",
            state=DiffState.MODIFIED,
            old_value=old_dict,
        )

        # Assert
        assert prop.old_value == old_dict

    def test_property_presentation_new_value_field(self) -> None:
        """Verify new_value field is present and can be set."""
        # Arrange & Act
        new_dict = {"x": 3.0, "y": 4.0}
        prop = PropertyPresentation(
            name="Vector",
            state=DiffState.MODIFIED,
            new_value=new_dict,
        )

        # Assert
        assert prop.new_value == new_dict

    def test_property_presentation_old_and_new_values_together(self) -> None:
        """Verify both old_value and new_value can be set simultaneously."""
        # Arrange & Act
        old_dict = {"x": 1.0, "y": 2.0}
        new_dict = {"x": 3.0, "y": 4.0}
        prop = PropertyPresentation(
            name="Vector",
            state=DiffState.MODIFIED,
            old_value=old_dict,
            new_value=new_dict,
        )

        # Assert
        assert prop.old_value == old_dict
        assert prop.new_value == new_dict

    def test_property_presentation_old_value_defaults_to_none(self) -> None:
        """Verify old_value defaults to None when not provided."""
        # Arrange & Act
        prop = PropertyPresentation(
            name="Length",
            state=DiffState.MODIFIED,
        )

        # Assert
        assert prop.old_value is None

    def test_property_presentation_new_value_defaults_to_none(self) -> None:
        """Verify new_value defaults to None when not provided."""
        # Arrange & Act
        prop = PropertyPresentation(
            name="Length",
            state=DiffState.MODIFIED,
        )

        # Assert
        assert prop.new_value is None

    def test_property_presentation_no_display_fields(self) -> None:
        """Verify old_display and new_display fields have been removed."""
        # Arrange & Act
        prop = PropertyPresentation(
            name="Length",
            state=DiffState.MODIFIED,
        )

        # Assert - these fields should not exist
        field_names = [f.name for f in dataclasses.fields(prop)]
        assert "old_display" not in field_names
        assert "new_display" not in field_names

    def test_property_presentation_no_deprecated_value_field(self) -> None:
        """Verify deprecated value field has been removed."""
        # Arrange & Act
        prop = PropertyPresentation(
            name="Length",
            state=DiffState.MODIFIED,
        )

        # Assert - this field should not exist
        field_names = [f.name for f in dataclasses.fields(prop)]
        assert "value" not in field_names

    def test_property_presentation_uses_diffstate_enum(self) -> None:
        """Verify state field uses DiffState enum type."""
        # Arrange & Act
        prop = PropertyPresentation(
            name="Length",
            state=DiffState.ADDED,
        )

        # Assert
        assert isinstance(prop.state, DiffState)
        assert prop.state == DiffState.ADDED


class TestSnapshotPresentation:
    """Tests for SnapshotPresentation dataclass."""

    def test_snapshot_presentation_is_frozen(self) -> None:
        """Verify immutability - frozen dataclass cannot be modified."""
        # Arrange
        snapshot = SnapshotPresentation(
            id="snap-001",
            name="v1.0",
            created_at="2024-01-15T10:30:00Z",
            node_count=42,
        )

        # Act & Assert - attempting to modify should raise FrozenInstanceError
        with pytest.raises(dataclasses.FrozenInstanceError):
            snapshot.node_count = 50  # type: ignore[misc]

    def test_snapshot_presentation_fields(self) -> None:
        """Verify all fields present in SnapshotPresentation."""
        # Arrange & Act
        snapshot = SnapshotPresentation(
            id="snap-abc-123",
            name="Initial version",
            created_at="2024-03-20T14:45:00Z",
            node_count=100,
        )

        # Assert
        assert snapshot.id == "snap-abc-123"
        assert snapshot.name == "Initial version"
        assert snapshot.created_at == "2024-03-20T14:45:00Z"
        assert snapshot.node_count == 100


class TestPresentationModelsAreDataclasses:
    """Tests verifying presentation models are proper dataclasses."""

    def test_presentation_models_are_dataclasses(self) -> None:
        """Verify all presentation models are dataclasses."""
        # Act & Assert
        assert is_dataclass(NodePresentation)
        assert is_dataclass(PropertyPresentation)
        assert is_dataclass(SnapshotPresentation)

    def test_node_presentation_dataclass_behavior(self) -> None:
        """Verify NodePresentation dataclass generates expected methods."""
        # Arrange
        node1 = NodePresentation(
            path="Part",
            type_id="Part::Feature",
            state=DiffState.MODIFIED,
            has_changes=True,
        )
        node2 = NodePresentation(
            path="Part",
            type_id="Part::Feature",
            state=DiffState.MODIFIED,
            has_changes=True,
        )
        node3 = NodePresentation(
            path="Part",
            type_id="Part::Feature",
            state=DiffState.UNCHANGED,
            has_changes=False,
        )

        # Assert
        assert node1 == node2  # Same values are equal
        assert node1 != node3  # Different values are not equal
        assert repr(node1).startswith("NodePresentation(")

    def test_property_presentation_dataclass_behavior(self) -> None:
        """Verify PropertyPresentation dataclass generates expected methods."""
        # Arrange
        prop1 = PropertyPresentation(
            name="Length",
            state=DiffState.MODIFIED,
        )
        prop2 = PropertyPresentation(
            name="Length",
            state=DiffState.MODIFIED,
        )

        # Assert
        assert prop1 == prop2
        assert repr(prop1).startswith("PropertyPresentation(")

    def test_snapshot_presentation_dataclass_behavior(self) -> None:
        """Verify SnapshotPresentation dataclass generates expected methods."""
        # Arrange
        snap1 = SnapshotPresentation(
            id="snap-001",
            name="v1",
            created_at="2024-01-01T00:00:00Z",
            node_count=10,
        )
        snap2 = SnapshotPresentation(
            id="snap-001",
            name="v1",
            created_at="2024-01-01T00:00:00Z",
            node_count=10,
        )

        # Assert
        assert snap1 == snap2
        assert repr(snap1).startswith("SnapshotPresentation(")
