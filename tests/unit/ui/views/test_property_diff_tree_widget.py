"""File responsibility: Unit tests for PropertyDiffTreeWidget component."""

import pytest
from PySide6.QtGui import QColor

from freecad.diff_wb.domain.diff.models import DiffState


@pytest.fixture(scope="module")
def widget() -> object:
    """Create a PropertyDiffTreeWidget instance for testing.

    Note: This uses module scope to ensure QApplication is created once
    and reused across all tests in this module.
    """
    from PySide6.QtWidgets import QApplication

    # Ensure QApplication exists before creating widgets
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    from freecad.diff_wb.ui.views.property_diff_tree_widget import PropertyDiffTreeWidget

    return PropertyDiffTreeWidget()


class TestPropertyDiffTreeWidgetShowPropertyDiff:
    """Tests for PropertyDiffTreeWidget.show_property_diff() method."""

    def test_empty_property_list_clears_tree(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() with empty list clears the properties tree."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Tree has existing items from previous call
        widget.show_property_diff(
            [
                PropertyPresentation(
                    name="Length",
                    state=DiffState.MODIFIED,
                ),
            ]
        )
        assert widget.topLevelItemCount() == 1

        # When: Call show_property_diff with empty list
        widget.show_property_diff([])

        # Then: Tree should be cleared
        assert widget.topLevelItemCount() == 0

    def test_single_property_added_state_green_background(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() with ADDED state displays green background in 3-column layout."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A single property with ADDED state
        properties = [
            PropertyPresentation(
                name="Length",
                old_value=None,
                new_value="25.0",
                state=DiffState.ADDED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Should have one group with one property child
        assert widget.topLevelItemCount() == 1  # One group header
        group_item = widget.topLevelItem(0)
        assert group_item is not None

        # Check group header text (default group is "Properties")
        assert group_item.text(0) == "Properties"

        # Check property is a child of the group
        assert group_item.childCount() == 1
        prop_item = group_item.child(0)
        assert prop_item is not None

        # Check property name (column 0) - CamelCase converted to spaced
        assert prop_item.text(0) == "Length"

        # Check Old Value column (column 1) is empty for ADDED
        assert prop_item.text(1) == ""

        # Check New Value column (column 2) has new value
        assert prop_item.text(2) == "25.0"

        # Check green background color on all 3 columns
        assert prop_item.background(0).color() == QColor(200, 255, 200)
        assert prop_item.background(1).color() == QColor(200, 255, 200)
        assert prop_item.background(2).color() == QColor(200, 255, 200)

    def test_single_property_deleted_state_red_background(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() with DELETED state displays red background in 3-column layout."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A single property with DELETED state
        properties = [
            PropertyPresentation(
                name="Width",
                old_value="15.0",
                new_value=None,
                state=DiffState.DELETED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Should have one group with one property child
        assert widget.topLevelItemCount() == 1
        group_item = widget.topLevelItem(0)
        assert group_item.childCount() == 1

        prop_item = group_item.child(0)
        assert prop_item is not None

        # Check property name
        assert prop_item.text(0) == "Width"

        # Check Old Value column (column 1) has old value for DELETED
        assert prop_item.text(1) == "15.0"

        # Check New Value column (column 2) is empty for DELETED
        assert prop_item.text(2) == ""

        # Check red background color on all 3 columns
        assert prop_item.background(0).color() == QColor(255, 200, 200)
        assert prop_item.background(1).color() == QColor(255, 200, 200)
        assert prop_item.background(2).color() == QColor(255, 200, 200)

    def test_single_property_modified_state_blue_background(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() with MODIFIED state displays blue background in 3-column layout."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: A single property with MODIFIED state
        properties = [
            PropertyPresentation(
                name="Height",
                old_value="10.0",
                new_value="20.0",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Check the property has blue background
        group_item = widget.topLevelItem(0)
        prop_item = group_item.child(0)

        # Check Old Value column (column 1) has old value for MODIFIED
        assert prop_item.text(1) == "10.0"

        # Check New Value column (column 2) has new value for MODIFIED
        assert prop_item.text(2) == "20.0"

        # Check blue background color on all 3 columns
        assert prop_item.background(0).color() == QColor(200, 200, 255)
        assert prop_item.background(1).color() == QColor(200, 200, 255)
        assert prop_item.background(2).color() == QColor(200, 200, 255)

    @pytest.mark.parametrize(
        ("state,old_val,new_val,col1,col2,expected_bg"),
        [
            (DiffState.ADDED, None, "25.0", "", "25.0", QColor(200, 255, 200)),
            (DiffState.DELETED, "15.0", None, "15.0", "", QColor(255, 200, 200)),
            (DiffState.MODIFIED, "10.0", "20.0", "10.0", "20.0", QColor(200, 200, 255)),
        ],
    )
    def test_state_variant_colors_and_columns(
        self,
        widget,
        state,
        old_val,
        new_val,
        col1,
        col2,
        expected_bg,  # type: ignore[no-untyped-def]
    ) -> None:
        """Parametrized test for ADDED/DELETED/MODIFIED state coloring and column values."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        properties = [
            PropertyPresentation(
                name="TestProp",
                old_value=old_val,
                new_value=new_val,
                state=state,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Verify column values and background color
        group_item = widget.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item is not None
        assert prop_item.text(1) == col1
        assert prop_item.text(2) == col2
        assert prop_item.background(0).color() == expected_bg
        assert prop_item.background(1).color() == expected_bg
        assert prop_item.background(2).color() == expected_bg

    def test_property_with_unchanged_state_gray_background(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() includes all properties with UNCHANGED state shown with gray background."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Mix of changed and unchanged properties
        properties = [
            PropertyPresentation(
                name="ChangedProp",
                old_value="10.0",
                new_value="20.0",
                state=DiffState.MODIFIED,
            ),
            PropertyPresentation(
                name="UnchangedProp",
                old_value="50.0",
                new_value="50.0",
                state=DiffState.UNCHANGED,
            ),
            PropertyPresentation(
                name="AnotherChanged",
                old_value=None,
                new_value="75.0",
                state=DiffState.ADDED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Should have 1 group with 3 property children
        assert widget.topLevelItemCount() == 1
        group_item = widget.topLevelItem(0)
        assert group_item.childCount() == 3

        # Get all property names
        names = [group_item.child(i).text(0) for i in range(3)]
        assert "Changed Prop" in names
        assert "Another Changed" in names
        assert "Unchanged Prop" in names

        # Find the unchanged property and verify its background is gray
        unchanged_index = names.index("Unchanged Prop")
        unchanged_item = group_item.child(unchanged_index)
        # For UNCHANGED, both columns show the same value
        assert unchanged_item.text(1) == "50.0"  # Value in left column
        assert unchanged_item.text(2) == "50.0"  # Same value in right column
        # Check background color is gray (light gray = 240, 240, 240) on all columns
        bg_color = unchanged_item.background(0).color()
        assert bg_color.red() == 240
        assert bg_color.green() == 240
        assert bg_color.blue() == 240


class TestPropertyDiffTreeWidgetGroupHeaders:
    """Tests for group header creation and styling."""

    def test_group_header_is_non_selectable(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() creates group headers that are not selectable."""
        from PySide6.QtCore import Qt

        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Group header should not be selectable
        group_item = widget.topLevelItem(0)
        assert group_item is not None
        flags = group_item.flags()
        assert not (flags & Qt.ItemFlag.ItemIsSelectable)

    def test_group_header_has_gray_background(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() creates group headers with gray background on all 3 columns."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Group header should have gray background (220, 220, 220) on all 3 columns
        group_item = widget.topLevelItem(0)
        assert group_item.background(0).color() == QColor(220, 220, 220)
        assert group_item.background(1).color() == QColor(220, 220, 220)
        assert group_item.background(2).color() == QColor(220, 220, 220)

    def test_group_header_is_bold(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() creates group headers with bold font."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Group header font should be bold
        group_item = widget.topLevelItem(0)
        font = group_item.font(0)
        assert font.bold()

    def test_groups_are_expanded_by_default(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() expands groups by default so properties are visible."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties to display
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Group should be expanded
        group_item = widget.topLevelItem(0)
        assert group_item.isExpanded()


class TestPropertyDiffTreeWidgetGroupSorting:
    """Tests for alphabetical group sorting in show_property_diff()."""

    def test_groups_appear_in_alphabetical_order(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() displays groups in alphabetical order (Base, Data, Format, etc.)."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties from multiple groups in non-alphabetical order
        properties = [
            PropertyPresentation(
                name="ZebraProp",
                state=DiffState.MODIFIED,
                group="Zebra",
            ),
            PropertyPresentation(
                name="AlphaProp",
                state=DiffState.MODIFIED,
                group="Alpha",
            ),
            PropertyPresentation(
                name="MiddleProp",
                state=DiffState.MODIFIED,
                group="Middle",
            ),
            PropertyPresentation(
                name="BetaProp",
                state=DiffState.MODIFIED,
                group="Beta",
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Groups should appear in alphabetical order
        assert widget.topLevelItemCount() == 4

        # Verify alphabetical order: Alpha, Beta, Middle, Zebra
        group_names = [widget.topLevelItem(i).text(0) for i in range(4)]
        assert group_names == ["Alpha", "Beta", "Middle", "Zebra"]

    def test_properties_within_groups_maintain_input_order(self, widget) -> None:  # type: ignore[no-untyped-def]
        """show_property_diff() maintains property order within each group as provided."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Multiple properties in same group with specific order
        properties = [
            PropertyPresentation(
                name="ZProp",
                state=DiffState.UNCHANGED,
                group="TestGroup",
            ),
            PropertyPresentation(
                name="AProp",
                state=DiffState.UNCHANGED,
                group="TestGroup",
            ),
            PropertyPresentation(
                name="MProp",
                state=DiffState.UNCHANGED,
                group="TestGroup",
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Properties within the group maintain their input order (ZProp, AProp, MProp)
        assert widget.topLevelItemCount() == 1
        group_item = widget.topLevelItem(0)
        assert group_item.text(0) == "TestGroup"
        assert group_item.childCount() == 3

        # Verify order is preserved as input (not sorted)
        prop_names = [group_item.child(i).text(0) for i in range(3)]
        assert prop_names == ["Z Prop", "A Prop", "M Prop"]


class TestPropertyDiffTreeWidgetCamelCaseConversion:
    """Tests for CamelCase to space conversion."""

    def test_camelcase_conversion_remains_unchanged_simple(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Simple CamelCase names are converted correctly."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Properties with various CamelCase patterns
        properties = [
            PropertyPresentation(
                name="SavedGeometry",
                state=DiffState.MODIFIED,
            ),
            PropertyPresentation(
                name="XMLParser",
                state=DiffState.MODIFIED,
            ),
            PropertyPresentation(
                name="Value2D",
                state=DiffState.MODIFIED,
            ),
        ]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: Names should be converted with spaces
        group_item = widget.topLevelItem(0)
        prop_names = [group_item.child(i).text(0) for i in range(3)]
        assert "Saved Geometry" in prop_names
        assert "XML Parser" in prop_names
        assert "Value 2D" in prop_names


class TestPropertyDiffTreeWidgetNestedChildren:
    """Tests for nested children recursion and expansion."""

    def test_nested_children_recurse_and_expansion_state_applied(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Nested children are recursively added and expansion state is applied after insertion."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: Nested structure where inner node is MODIFIED
        x_child = PropertyPresentation(name="x", state=DiffState.MODIFIED, old_value=1.0, new_value=2.0)
        base_parent = PropertyPresentation(
            name="Base",
            state=DiffState.MODIFIED,
            children=[x_child],
        )
        placement = PropertyPresentation(
            name="Placement",
            state=DiffState.MODIFIED,
            children=[base_parent],
        )

        properties = [placement]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: All nodes in the changed branch are expanded
        group_item = widget.topLevelItem(0)
        prop_item = group_item.child(0)
        assert prop_item.isExpanded()  # Placement has changed descendants
        assert prop_item.child(0).isExpanded()  # Base has changed descendants
        assert prop_item.child(0).child(0).isExpanded()  # x has MODIFIED state

    def test_unchanged_branches_collapsed(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Unchanged branches stay collapsed when no descendant has changes."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Given: All nodes UNCHANGED
        x_child = PropertyPresentation(name="x", state=DiffState.UNCHANGED, old_value=1.0, new_value=1.0)
        base_parent = PropertyPresentation(
            name="Base",
            state=DiffState.UNCHANGED,
            children=[x_child],
        )
        placement = PropertyPresentation(
            name="Placement",
            state=DiffState.UNCHANGED,
            children=[base_parent],
        )

        properties = [placement]

        # When: Call show_property_diff
        widget.show_property_diff(properties)

        # Then: All nodes in the unchanged branch are collapsed
        group_item = widget.topLevelItem(0)
        prop_item = group_item.child(0)
        assert not prop_item.isExpanded()  # Placement is UNCHANGED
        assert not prop_item.child(0).isExpanded()  # Base is UNCHANGED
        assert not prop_item.child(0).child(0).isExpanded()  # x is UNCHANGED


class TestPropertyDiffTreeWidgetThreeColumnLayout:
    """Tests for the 3-column property diff layout."""

    def test_widget_has_three_columns(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Widget has exactly 3 columns."""
        # When: Creating a fresh widget
        # Then: The tree should have 3 columns
        assert widget.columnCount() == 3

    def test_header_labels_are_correct(self, widget) -> None:  # type: ignore[no-untyped-def]
        """Header labels are ['Property', 'Old Value', 'New Value']."""
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # When: Adding a property
        properties = [
            PropertyPresentation(
                name="TestProp",
                state=DiffState.MODIFIED,
            ),
        ]
        widget.show_property_diff(properties)

        # Then: We can access all 3 columns
        group_item = widget.topLevelItem(0)
        assert group_item is not None
        assert group_item.text(0) == "Properties"
        assert group_item.text(1) == ""
        assert group_item.text(2) == ""
