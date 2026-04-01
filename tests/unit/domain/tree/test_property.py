# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the Property class including creation, equality,
# expression support, and type detection functionality.
"""Unit tests for the Property class."""

from freecad.diff_wb.domain import Placement, Property, PropertyType, Rotation, Vector


class MockConstraint:
    """Mock constraint simulating FreeCAD C++ wrapped object without __eq__."""

    def __init__(self, name: str, constraint_type: str):
        self.Name = name
        self.Type = constraint_type

    def __str__(self):
        return f"<Constraint '{self.Name}' type={self.Type}>"


class TestProperty:
    """Tests for the Property class."""

    # =====================================================================
    # Property.create() Tests
    # =====================================================================

    def test_bool_creation(self):
        """Test boolean property value creation."""
        pv = Property.create(PropertyType.BOOL, True)
        assert pv.type_ == PropertyType.BOOL
        assert pv.value is True

    def test_int_creation(self):
        """Test integer property value creation."""
        pv = Property.create(PropertyType.INT, 42)
        assert pv.type_ == PropertyType.INT
        assert pv.value == 42

    def test_float_creation(self):
        """Test float property value creation."""
        pv = Property.create(PropertyType.FLOAT, 3.14)
        assert pv.type_ == PropertyType.FLOAT
        assert pv.value == 3.14

    def test_string_creation(self):
        """Test string property value creation."""
        pv = Property.create(PropertyType.STRING, "hello")
        assert pv.type_ == PropertyType.STRING
        assert pv.value == "hello"

    def test_vector_creation(self):
        """Test vector property value creation."""
        pv = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        assert pv.type_ == PropertyType.VECTOR
        assert isinstance(pv.value, Vector)
        assert pv.value.x == 1.0
        assert pv.value.y == 2.0
        assert pv.value.z == 3.0

    def test_vector_with_expression(self):
        """Test vector with expression."""
        pv = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch001.X")
        assert pv.expression == "Sketch001.X"
        assert str(pv) == "(1.0, 2.0, 3.0)"

    def test_placement_creation(self):
        """Test placement property value creation."""
        pv = Property.create(PropertyType.PLACEMENT, {"position": (0, 0, 0), "rotation": (0, 0, 1, 90)})
        assert pv.type_ == PropertyType.PLACEMENT
        assert isinstance(pv.value, Placement)
        assert pv.value.position == Vector(0, 0, 0)
        assert pv.value.rotation == Rotation(0, 0, 1, 90)

    def test_placement_with_expression(self):
        """Test placement with expression."""
        pv = Property.create(
            PropertyType.PLACEMENT, {"position": (0, 0, 0), "rotation": (0, 0, 1, 45)}, expression="Body.Placement"
        )
        assert pv.type_ == PropertyType.PLACEMENT
        assert pv.expression == "Body.Placement"

    # =====================================================================
    # Equality Tests
    # =====================================================================

    def test_equality_same_type(self):
        """Test equality for same type values."""
        pv1 = Property.create(PropertyType.INT, 42)
        pv2 = Property.create(PropertyType.INT, 42)
        assert pv1 == pv2

    def test_inequality_different_type(self):
        """Test inequality for different types."""
        pv1 = Property.create(PropertyType.INT, 42)
        pv2 = Property.create(PropertyType.FLOAT, 42.0)
        assert pv1 != pv2

    def test_float_approximate_equality(self):
        """Test approximate equality for floats."""
        pv1 = Property.create(PropertyType.FLOAT, 1.0)
        pv2 = Property.create(PropertyType.FLOAT, 1.0 + 1e-10)
        assert pv1 == pv2

    # =====================================================================
    # Expression Support Tests
    # =====================================================================

    def test_bool_with_expression(self):
        """Test boolean property with expression."""
        pv = Property.create(PropertyType.BOOL, True, expression="Sketch001.Constrain")
        assert pv.type_ == PropertyType.BOOL
        assert pv.value is True
        assert pv.expression == "Sketch001.Constrain"
        assert str(pv) == "True"

    def test_int_with_expression(self):
        """Test integer property with expression."""
        pv = Property.create(PropertyType.INT, 10, expression="Sketch001.Count")
        assert pv.type_ == PropertyType.INT
        assert pv.value == 10
        assert pv.expression == "Sketch001.Count"
        assert str(pv) == "10"

    def test_float_with_expression(self):
        """Test float property with expression."""
        pv = Property.create(PropertyType.FLOAT, 5.5, expression="Body.Length")
        assert pv.type_ == PropertyType.FLOAT
        assert pv.value == 5.5
        assert pv.expression == "Body.Length"
        assert str(pv) == "5.5"

    def test_string_with_expression(self):
        """Test string property with expression."""
        pv = Property.create(PropertyType.STRING, "test", expression="Document.Name")
        assert pv.type_ == PropertyType.STRING
        assert pv.value == "test"
        assert pv.expression == "Document.Name"
        assert str(pv) == "test"

    def test_equality_same_value_different_expression(self):
        """Test that same values with different expressions are NOT equal."""
        pv1 = Property.create(PropertyType.FLOAT, 10.0)
        pv2 = Property.create(PropertyType.FLOAT, 10.0, expression="Sketch001.X")
        assert pv1 != pv2

    def test_equality_expression_vs_no_expression(self):
        """Test that value with expression differs from value without."""
        pv1 = Property.create(PropertyType.INT, 42, expression="Some.Expression")
        pv2 = Property.create(PropertyType.INT, 42)
        assert pv1 != pv2

    def test_equality_same_expression(self):
        """Test that same value and expression are equal."""
        pv1 = Property.create(PropertyType.STRING, "hello", expression="Doc.Name")
        pv2 = Property.create(PropertyType.STRING, "hello", expression="Doc.Name")
        assert pv1 == pv2

    def test_equality_different_expressions(self):
        """Test that same value with different expressions are NOT equal."""
        pv1 = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch001.X")
        pv2 = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch002.X")
        assert pv1 != pv2

    def test_equality_both_none_expressions(self):
        """Test equality when both have no expressions."""
        pv1 = Property.create(PropertyType.BOOL, False)
        pv2 = Property.create(PropertyType.BOOL, False)
        assert pv1 == pv2


class TestVectorHandler:
    """Tests for Vector handler class."""

    def test_vector_handles_known_properties(self):
        """Test Vector.handles() returns True for known property names."""
        assert Vector.handles("Position") is True
        assert Vector.handles("Axis") is True
        assert Vector.handles("Direction") is True
        assert Vector.handles("Normal") is True
        assert Vector.handles("Translation") is True
        assert Vector.handles("StartPoint") is True
        assert Vector.handles("EndPoint") is True

    def test_vector_handles_unknown_properties(self):
        """Test Vector.handles() returns False for unknown property names."""
        assert Vector.handles("Placement") is False
        assert Vector.handles("Length") is False
        assert Vector.handles("Label") is False

    def test_vector_from_freecad_value(self):
        """Test Vector.from_freecad_value() converts FreeCAD object to Property."""

        class MockVector:
            x, y, z = 1.0, 2.0, 3.0

        prop = Vector.from_freecad_value(MockVector())
        assert prop.type_ == PropertyType.VECTOR
        assert isinstance(prop.value, Vector)
        assert prop.value.x == 1.0
        assert prop.value.y == 2.0
        assert prop.value.z == 3.0

    def test_vector_from_freecad_value_with_expression(self):
        """Test Vector.from_freecad_value() with expression."""

        class MockVector:
            x, y, z = 1.0, 2.0, 3.0

        prop = Vector.from_freecad_value(MockVector(), expression="Sketch001.X")
        assert prop.expression == "Sketch001.X"


class TestPlacementHandler:
    """Tests for Placement handler class."""

    def test_placement_handles_placement_property(self):
        """Test Placement.handles() returns True for Placement property."""
        assert Placement.handles("Placement") is True

    def test_placement_handles_other_properties(self):
        """Test Placement.handles() returns False for other properties."""
        assert Placement.handles("Position") is False
        assert Placement.handles("Length") is False
        assert Placement.handles("Label") is False

    def test_placement_from_freecad_value(self):
        """Test Placement.from_freecad_value() converts FreeCAD object to Property."""

        class MockAxis:
            x, y, z = 0.0, 0.0, 1.0

        class MockRotation:
            Axis = MockAxis()
            Angle = 90.0

        class MockBase:
            x, y, z = 1.0, 2.0, 3.0

        class MockPlacement:
            Base = MockBase()
            Rotation = MockRotation()

        prop = Placement.from_freecad_value(MockPlacement())
        assert prop.type_ == PropertyType.PLACEMENT
        assert isinstance(prop.value, Placement)
        assert prop.value.position == Vector(1.0, 2.0, 3.0)
        assert prop.value.rotation == Rotation(0.0, 0.0, 1.0, 90.0)

    def test_placement_from_freecad_value_with_expression(self):
        """Test Placement.from_freecad_value() with expression."""

        class MockAxis:
            x, y, z = 0.0, 0.0, 1.0

        class MockRotation:
            Axis = MockAxis()
            Angle = 45.0

        class MockBase:
            x, y, z = 0.0, 0.0, 0.0

        class MockPlacement:
            Base = MockBase()
            Rotation = MockRotation()

        prop = Placement.from_freecad_value(MockPlacement(), expression="Body.Placement")
        assert prop.expression == "Body.Placement"


class TestPropertyListComparison:
    """Tests for LIST type property comparison (e.g., sketch Constraints)."""

    def test_list_with_custom_objects_same_content(self):
        """Lists with identical custom object content should be equal."""
        constraints1 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
        ]
        constraints2 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
        ]

        prop1 = Property.create(PropertyType.LIST, constraints1)
        prop2 = Property.create(PropertyType.LIST, constraints2)

        # Different objects but same string representation -> should be equal
        assert prop1 == prop2

    def test_list_with_custom_objects_different_content(self):
        """Lists with different custom object content should not be equal."""
        constraints1 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
        ]
        constraints2 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance2", "Distance"),  # Different name
        ]

        prop1 = Property.create(PropertyType.LIST, constraints1)
        prop2 = Property.create(PropertyType.LIST, constraints2)

        # Different string representations -> should not be equal
        assert prop1 != prop2

    def test_list_with_different_lengths(self):
        """Lists with different lengths should not be equal."""
        constraints1 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
        ]
        constraints2 = [
            MockConstraint("Coincident1", "Coincident"),
            MockConstraint("Distance1", "Distance"),
            MockConstraint("Angle1", "Angle"),  # Extra constraint
        ]

        prop1 = Property.create(PropertyType.LIST, constraints1)
        prop2 = Property.create(PropertyType.LIST, constraints2)

        assert prop1 != prop2

    def test_list_with_simple_values(self):
        """Lists with simple values (strings, ints) should work correctly."""
        prop1 = Property.create(PropertyType.LIST, ["a", "b", "c"])
        prop2 = Property.create(PropertyType.LIST, ["a", "b", "c"])

        assert prop1 == prop2

    def test_list_with_mixed_types(self):
        """Lists with mixed types should compare correctly."""
        prop1 = Property.create(PropertyType.LIST, [1, "a", 3.14])
        prop2 = Property.create(PropertyType.LIST, [1, "a", 3.14])

        assert prop1 == prop2

    def test_list_creation_preserves_objects(self):
        """LIST type creation should preserve the actual objects."""

        class MockObj:
            def __init__(self, value):
                self.value = value

        obj1 = MockObj(1)
        obj2 = MockObj(2)
        props = Property.create(PropertyType.LIST, [obj1, obj2])

        assert isinstance(props.value, list)
        assert len(props.value) == 2
        assert props.value[0].value == 1
        assert props.value[1].value == 2


class TestRegistry:
    """Tests for the handler registry."""

    def test_handlers_are_registered(self):
        """Test that Vector and Placement handlers are registered."""
        from freecad.diff_wb.domain.tree.property import _PROPERTY_HANDLERS

        assert len(_PROPERTY_HANDLERS) >= 2
        handler_classes = [h.__name__ for h in _PROPERTY_HANDLERS]
        assert "Vector" in handler_classes
        assert "Placement" in handler_classes


class TestPropertyGetChildren:
    """Tests for the Property.get_children() method."""

    def test_get_children_placement(self):
        """Placement returns Position + Rotation."""
        pv = Property.create(PropertyType.PLACEMENT, {"position": (1.0, 2.0, 3.0), "rotation": (0, 0, 1, 90)})
        children = pv.get_children()

        assert len(children) == 2
        names = [name for name, _ in children]
        assert "Position" in names
        assert "Rotation" in names

    def test_get_children_rotation(self):
        """Rotation returns Angle + Axis."""

        # Create a Rotation-like object with angle/axis attributes
        class MockAxis:
            x, y, z = 0.0, 0.0, 1.0

        class MockRotation:
            Angle = 90.0
            Axis = MockAxis()

        # Create a Property with type that has angle/axis (not Placement)
        pv = Property(type_=PropertyType.UNKNOWN, value=MockRotation())
        children = pv.get_children()

        assert len(children) == 2
        names = [name for name, _ in children]
        assert "Angle" in names
        assert "Axis" in names

    def test_get_children_vector(self):
        """Vector returns x, y, z."""
        pv = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        children = pv.get_children()

        assert len(children) == 3
        names = [name for name, _ in children]
        assert "x" in names
        assert "y" in names
        assert "z" in names

    def test_get_children_list(self):
        """List returns indexed items."""
        pv = Property.create(PropertyType.LIST, ["a", "b", "c"])
        children = pv.get_children()

        assert len(children) == 3
        assert children[0] == ("0", "a")
        assert children[1] == ("1", "b")
        assert children[2] == ("2", "c")

    def test_get_children_dict(self):
        """Dict returns key-value pairs."""
        pv = Property(type_=PropertyType.UNKNOWN, value={"key1": "val1", "key2": "val2"})
        children = pv.get_children()

        assert len(children) == 2
        child_dict = dict(children)
        assert child_dict["key1"] == "val1"
        assert child_dict["key2"] == "val2"

    def test_get_children_primitive(self):
        """Primitive returns empty list."""
        pv_int = Property.create(PropertyType.INT, 42)
        assert pv_int.get_children() == []

        pv_float = Property.create(PropertyType.FLOAT, 3.14)
        assert pv_float.get_children() == []

        pv_string = Property.create(PropertyType.STRING, "hello")
        assert pv_string.get_children() == []

        pv_bool = Property.create(PropertyType.BOOL, True)
        assert pv_bool.get_children() == []

    def test_get_children_none(self):
        """None value returns empty list."""
        pv = Property(type_=PropertyType.INT, value=None)
        assert pv.get_children() == []

    def test_get_children_empty_list(self):
        """Empty list returns empty list."""
        pv = Property.create(PropertyType.LIST, [])
        assert pv.get_children() == []

    def test_get_children_empty_dict(self):
        """Empty dict returns empty list."""
        pv = Property(type_=PropertyType.UNKNOWN, value={})
        assert pv.get_children() == []

    def test_get_children_vector_with_lowercase_attributes(self):
        """Vector-like objects with lowercase x,y,z attributes work."""

        class MockVector:
            def __init__(self):
                self.x = 1.0
                self.y = 2.0
                self.z = 3.0

        pv = Property(type_=PropertyType.UNKNOWN, value=MockVector())
        children = pv.get_children()

        assert len(children) == 3
        child_dict = dict(children)
        assert child_dict["x"] == 1.0
        assert child_dict["y"] == 2.0
        assert child_dict["z"] == 3.0

    def test_get_children_rotation_with_lowercase_attributes(self):
        """Rotation with lowercase angle/axis attributes works."""

        class MockAxis:
            def __init__(self):
                self.x = 0.0
                self.y = 0.0
                self.z = 1.0

        class MockRotation:
            def __init__(self):
                self.angle = 45.0
                self.axis = MockAxis()

        pv = Property(type_=PropertyType.UNKNOWN, value=MockRotation())
        children = pv.get_children()

        assert len(children) == 2
        names = [name for name, _ in children]
        assert "Angle" in names
        assert "Axis" in names
