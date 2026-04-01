# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains domain models for representing FreeCAD
# property values, including Vector, Rotation, Placement, and the unified Property
# type. It also includes type detection logic for converting FreeCAD property values
# to domain models.
"""Property value models for FreeCAD document snapshots."""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, ClassVar


logger = logging.getLogger(__name__)


class PropertyType(Enum):
    """Types of FreeCAD properties."""

    # TODO: switch to explicit values; determine which values to use (hard coded, or taken from freecad?)
    # Basic types
    BOOL = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()

    # Vector-based types
    VECTOR = auto()  # x, y, z
    PLACEMENT = auto()  # position + rotation

    # Compound types
    EXPRESSION = auto()  # Expression string
    LIST = auto()  # Lists/tuples (e.g., Constraints)

    # Special types (deferred for later phases)
    SHAPE = auto()  # Geometry data
    MATERIAL = auto()  # Material assignment
    UNKNOWN = auto()  # Fallback for unhandled types


# Registry of property type handlers. Consulted by Property.from_freecad_property() to delegate
# complex type conversion (e.g., "Position" -> Vector, "Placement" -> Placement).
# To add a new type: inherit from PropertyHandler, define PROPERTY_NAMES, implement
# from_freecad_value(), and decorate with @register_handler.
_PROPERTY_HANDLERS: list[type["PropertyHandler"]] = []


def register_handler(cls: type) -> type:
    """Decorator to register a property handler class."""
    _PROPERTY_HANDLERS.append(cls)
    return cls


class PropertyHandler:
    """Base class for property type handlers."""

    PROPERTY_NAMES: ClassVar[frozenset[str]] = frozenset()

    @classmethod
    def handles(cls, prop_name: str) -> bool:
        """Check if a property name is handled by this handler.

        Args:
            prop_name: The name of the property to check

        Returns:
            True if this handler manages the given property name, False otherwise
        """
        return prop_name in cls.PROPERTY_NAMES

    @classmethod
    def from_freecad_value(cls, value: Any, expression: str | None = None, group: str = "Base") -> "Property":
        """Create a Property from a FreeCAD object.

        Args:
            value: The FreeCAD object/property value to extract
            expression: Optional expression that drives this value
            group: The FreeCAD property group

        Returns:
            A Property instance with the extracted value

        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError("Subclasses must implement from_freecad_value")


@register_handler
@dataclass(frozen=True)
class Vector(PropertyHandler):
    """A 3D vector representing position or direction.

    Attributes:
        x: X coordinate
        y: Y coordinate
        z: Z coordinate
    """

    PROPERTY_NAMES: ClassVar[frozenset[str]] = frozenset(
        {"Position", "Axis", "Direction", "Normal", "Translation", "StartPoint", "EndPoint"}
    )

    x: float
    y: float
    z: float

    def __str__(self) -> str:
        return f"({self.x}, {self.y}, {self.z})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector):
            return NotImplemented
        # Use approximate equality for floats
        tolerance = 1e-9
        return (
            abs(self.x - other.x) < tolerance
            and abs(self.y - other.y) < tolerance
            and abs(self.z - other.z) < tolerance
        )

    @classmethod
    def from_freecad_value(cls, value: Any, expression: str | None = None, group: str = "Base") -> "Property":
        """Extract Vector property from FreeCAD object.

        Args:
            value: The FreeCAD object or vector containing x, y, z attributes
            expression: Optional expression that drives this value
            group: The FreeCAD property group

        Returns:
            A Property instance with the extracted Vector value

        Raises:
            ValueError: If the value doesn't have x, y, z attributes
        """
        try:
            return Property(
                type_=PropertyType.VECTOR,
                value=cls(x=float(value.x), y=float(value.y), z=float(value.z)),
                expression=expression,
                group=group,
            )
        except Exception as e:
            logger.warning("Failed to extract Vector property: %s", e)
            raise


@dataclass(frozen=True)
class Rotation:
    """A rotation represented by axis-angle notation.

    FreeCAD uses axis-angle representation internally. A rotation consists of
    an axis (unit vector) and an angle (in degrees).

    Attributes:
        axis_x: X component of rotation axis
        axis_y: Y component of rotation axis
        axis_z: Z component of rotation axis
        angle_degrees: Rotation angle in degrees
    """

    axis_x: float
    axis_y: float
    axis_z: float
    angle_degrees: float

    def __str__(self) -> str:
        return f"Axis=({self.axis_x}, {self.axis_y}, {self.axis_z}), Angle={self.angle_degrees}\u00b0"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rotation):
            return NotImplemented
        # Use approximate equality for floats
        tolerance = 1e-9
        return (
            abs(self.axis_x - other.axis_x) < tolerance
            and abs(self.axis_y - other.axis_y) < tolerance
            and abs(self.axis_z - other.axis_z) < tolerance
            and abs(self.angle_degrees - other.angle_degrees) < tolerance
        )

    @classmethod
    def identity(cls) -> "Rotation":
        """Create an identity rotation (no rotation)."""
        return cls(axis_x=0.0, axis_y=0.0, axis_z=1.0, angle_degrees=0.0)


@register_handler
@dataclass(frozen=True)
class Placement(PropertyHandler):
    """A placement combining position and orientation.

    Represents a transformation in 3D space, combining a position vector
    and a rotation. This is the fundamental way FreeCAD positions objects.

    Attributes:
        position: The position vector
        rotation: The rotation (axis-angle)
    """

    PROPERTY_NAMES: ClassVar[frozenset[str]] = frozenset({"Placement"})

    position: Vector
    rotation: Rotation

    def __str__(self) -> str:
        return f"Pos={self.position}, Rot={self.rotation}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Placement):
            return NotImplemented
        return self.position == other.position and self.rotation == other.rotation

    @classmethod
    def identity(cls) -> "Placement":
        """Create an identity placement (origin, no rotation)."""
        return cls(position=Vector(0.0, 0.0, 0.0), rotation=Rotation.identity())

    @classmethod
    def from_freecad_value(cls, value: Any, expression: str | None = None, group: str = "Base") -> "Property":
        """Extract Placement property from FreeCAD object.

        Args:
            value: The FreeCAD Placement object with Base (position) and Rotation attributes
            expression: Optional expression that drives this value
            group: The FreeCAD property group

        Returns:
            A Property instance with the extracted Placement value

        Raises:
            ValueError: If the value is missing Base or Rotation attributes
        """
        try:
            pos = getattr(value, "Base", None)
            rot = getattr(value, "Rotation", None)
            if not pos or not rot:
                raise ValueError("Placement missing Base or Rotation")
            return Property(
                type_=PropertyType.PLACEMENT,
                value=cls(
                    position=Vector(x=float(pos.x), y=float(pos.y), z=float(pos.z)),
                    rotation=Rotation(
                        axis_x=float(rot.Axis.x),
                        axis_y=float(rot.Axis.y),
                        axis_z=float(rot.Axis.z),
                        angle_degrees=float(rot.Angle),
                    ),
                ),
                expression=expression,
                group=group,
            )
        except Exception as e:
            logger.warning("Failed to extract Placement property: %s", e)
            raise


@dataclass(frozen=True)
class Property:
    """A value of a FreeCAD property.

    This is a union type that can represent any FreeCAD property value.
    It includes type information to enable proper comparison and display.

    Attributes:
        type_: The type of this property value
        value: The actual value (type depends on type_)
        expression: Optional expression if this value is driven by an expression
        group: The FreeCAD property group (e.g., "Base", "Data", "View")
    """

    type_: PropertyType
    value: Any
    expression: str | None = None
    group: str = "Base"

    def __str__(self) -> str:
        """String representation suitable for display."""
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare two property values for equality.

        Two property values are equal if they have the same type, value, and expression.
        Expression differences are considered significant even if values are the same.

        For LIST types (e.g., Constraints), compares string representations of elements
        to handle FreeCAD C++ wrapped objects that lack proper __eq__ implementations.
        """
        if not isinstance(other, Property):
            return NotImplemented

        # Different types are never equal
        if self.type_ != other.type_:
            return False

        # Expressions must match (if one has an expression and the other doesn't, they're different)
        if self.expression != other.expression:
            return False

        # For floats, use approximate equality
        if self.type_ == PropertyType.FLOAT:
            tolerance = 1e-9
            return bool(abs(self.value - other.value) < tolerance)

        # For lists, compare element string representations
        # This handles FreeCAD C++ wrapped objects (e.g., Constraint) that lack __eq__
        if self.type_ == PropertyType.LIST:
            return self._compare_lists_as_strings(self.value, other.value)

        return bool(self.value == other.value)

    @staticmethod
    def _compare_lists_as_strings(list1: Any, list2: Any) -> bool:
        """Compare two lists by string representation of their elements.

        Args:
            list1: First list to compare
            list2: Second list to compare

        Returns:
            True if lists have same length and all corresponding elements
            have equal string representations.
        """
        # Handle None cases
        if list1 is None and list2 is None:
            return True
        if list1 is None or list2 is None:
            return False

        # Must be same type (both lists/tuples)
        if not isinstance(list1, (list, tuple)) or not isinstance(list2, (list, tuple)):
            return False

        # Must have same length
        if len(list1) != len(list2):
            return False

        # Compare each element by string representation
        return all(str(item1) == str(item2) for item1, item2 in zip(list1, list2, strict=True))

    @classmethod
    def create(cls, type_: PropertyType, value: Any, expression: str | None = None, group: str = "Base") -> "Property":
        """Create a Property with proper type handling.

        This factory method accepts structured data (tuples/dicts) as the value
        parameter and internally creates the appropriate domain objects.

        Args:
            type_: The property type
            value: The value in structured form:
                - BOOL, INT, FLOAT, STRING: direct value
                - VECTOR: tuple (x, y, z)
                - PLACEMENT: dict {"position": (x, y, z), "rotation": (ax, ay, az, angle)}
                - LIST: list or tuple (preserved as-is)
            expression: Optional expression that drives this value
            group: The FreeCAD property group (e.g., "Base", "Data", "View")

        Returns:
            A Property instance with properly structured value

        Examples:
            >>> Property.create(PropertyType.BOOL, True)
            >>> Property.create(PropertyType.INT, 42)
            >>> Property.create(PropertyType.FLOAT, 3.14)
            >>> Property.create(PropertyType.STRING, "hello")
            >>> Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
            >>> Property.create(
            ...     PropertyType.PLACEMENT, {"position": (0, 0, 0), "rotation": (0, 0, 1, 90)}
            ... )
            >>> Property.create(PropertyType.LIST, [item1, item2])
        """
        if type_ == PropertyType.BOOL:
            return cls(type_=type_, value=bool(value), expression=expression, group=group)
        elif type_ == PropertyType.INT:
            return cls(type_=type_, value=int(value), expression=expression, group=group)
        elif type_ == PropertyType.FLOAT:
            return cls(type_=type_, value=float(value), expression=expression, group=group)
        elif type_ == PropertyType.STRING:
            return cls(type_=type_, value=str(value), expression=expression, group=group)
        elif type_ == PropertyType.VECTOR:
            # value is expected to be a tuple (x, y, z)
            x, y, z = value
            return cls(type_=type_, value=Vector(x=x, y=y, z=z), expression=expression, group=group)
        elif type_ == PropertyType.PLACEMENT:
            # value is expected to be a dict {"position": (x,y,z), "rotation": (ax,ay,az,angle)}
            pos = value["position"]
            rot = value["rotation"]
            return cls(
                type_=type_,
                value=Placement(
                    position=Vector(x=pos[0], y=pos[1], z=pos[2]),
                    rotation=Rotation(axis_x=rot[0], axis_y=rot[1], axis_z=rot[2], angle_degrees=rot[3]),
                ),
                expression=expression,
                group=group,
            )
        elif type_ == PropertyType.LIST:
            # Preserve list/tuple objects as-is for expandable properties
            return cls(type_=type_, value=value, expression=expression, group=group)
        else:
            # For unknown/expression/shape/material types, store value as-is
            return cls(type_=type_, value=value, expression=expression, group=group)

    @staticmethod
    def from_freecad_property(
        prop_name: str, value: Any, expression: str | None = None, group: str = "Base"
    ) -> "Property":
        """Create a Property from a FreeCAD property value.

        This factory method delegates to registered handlers for complex types
        (VECTOR, PLACEMENT) and falls back to type inference for basic types.

        Args:
            prop_name: The FreeCAD property name (e.g., "Placement", "Position", "Length")
            value: The raw value from the FreeCAD object
            expression: Optional expression that drives this value
            group: The FreeCAD property group (e.g., "Base", "Data", "View")

        Returns:
            A Property with properly detected type and converted value
        """
        # Try registered handlers first
        for handler in _PROPERTY_HANDLERS:
            if handler.handles(prop_name):
                return handler.from_freecad_value(value, expression, group)

        # Fall back to type inference from value
        prop_type = Property._infer_type_from_value(value)
        return Property.create(prop_type, value, expression=expression, group=group)

    @staticmethod
    def _infer_type_from_value(val: Any) -> PropertyType:
        """Infer PropertyType from a Python value."""
        if isinstance(val, bool):
            return PropertyType.BOOL
        elif isinstance(val, int):
            return PropertyType.INT
        elif isinstance(val, float):
            return PropertyType.FLOAT
        elif val is None or isinstance(val, str):
            return PropertyType.STRING
        elif isinstance(val, (list, tuple)):
            # Preserve list/tuple objects for expandable properties like Constraints
            return PropertyType.LIST
        else:
            # For complex types (dict, custom objects), default to UNKNOWN to preserve the object
            return PropertyType.UNKNOWN

    def get_children(self) -> list[tuple[str, Any]]:
        """Get child properties for expandable property types.

        Returns list of (child_name, child_value) tuples for:
        - Placement: [("Position", position), ("Rotation", rotation)]
        - Rotation (inside Placement): [("Angle", angle), ("Axis", axis)]
        - Vector-like (x,y,z): [("x", x), ("y", y), ("z", z)]
        - List/tuple: [("0", item0), ("1", item1), ...]
        - Dict: [("key1", value1), ("key2", value2), ...]

        Returns empty list for primitive types and non-expandable objects.

        Note: Rotation is not a separate PropertyType - it's a value object inside
        Placement. We detect it by checking if the value has angle/axis attributes.
        """
        if self.value is None:
            return []

        if self.type_ == PropertyType.PLACEMENT:
            return self._get_placement_children()

        if self._is_rotation_value():
            return self._get_rotation_children()

        if self._is_vector_like():
            return self._get_vector_children()

        if isinstance(self.value, (list, tuple)) and self.value:
            return [(str(i), v) for i, v in enumerate(self.value)]

        if isinstance(self.value, dict) and self.value:
            return [(str(k), v) for k, v in self.value.items()]

        return []

    def _get_placement_children(self) -> list[tuple[str, Any]]:
        """Get children for Placement type."""
        result = []
        if hasattr(self.value, "position") and self.value.position is not None:
            result.append(("Position", self.value.position))
        elif hasattr(self.value, "Base") and self.value.Base is not None:
            result.append(("Base", self.value.Base))
        if hasattr(self.value, "rotation") and self.value.rotation is not None:
            result.append(("Rotation", self.value.rotation))
        elif hasattr(self.value, "Rotation") and self.value.Rotation is not None:
            result.append(("Rotation", self.value.Rotation))
        return result

    def _is_rotation_value(self) -> bool:
        """Check if value is a Rotation-like object with angle/axis."""
        has_angle = hasattr(self.value, "angle") or hasattr(self.value, "Angle")
        has_axis = hasattr(self.value, "axis") or hasattr(self.value, "Axis")
        return has_angle and has_axis

    def _get_rotation_children(self) -> list[tuple[str, Any]]:
        """Get children for Rotation value object."""
        result = []
        if hasattr(self.value, "angle") and self.value.angle is not None:
            result.append(("Angle", self.value.angle))
        elif hasattr(self.value, "Angle") and self.value.Angle is not None:
            result.append(("Angle", self.value.Angle))
        if hasattr(self.value, "axis") and self.value.axis is not None:
            result.append(("Axis", self.value.axis))
        elif hasattr(self.value, "Axis") and self.value.Axis is not None:
            result.append(("Axis", self.value.Axis))
        return result

    def _is_vector_like(self) -> bool:
        """Check if value has x, y, z attributes."""
        return hasattr(self.value, "x") and hasattr(self.value, "y") and hasattr(self.value, "z")

    def _get_vector_children(self) -> list[tuple[str, Any]]:
        """Get children for Vector-like objects."""
        return [("x", self.value.x), ("y", self.value.y), ("z", self.value.z)]


__all__ = ["Property", "PropertyType", "Vector", "Rotation", "Placement"]
