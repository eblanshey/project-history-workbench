# SPDX-License-Identifier: LGPL-3.0-or-later
"""Property value comparison logic.

File responsibility: This module provides type-aware property comparison algorithms
for comparing property values between two snapshots. It handles all FreeCAD property
types with appropriate equality rules (e.g., float tolerance, vector component-wise
comparison).

Comparison rules:
- BOOL, INT, STRING, LINK: Exact equality
- FLOAT: Approximate equality (tolerance=1e-9)
- VECTOR: Component-wise approximate equality
- PLACEMENT: Position + rotation comparison
- EXPRESSION: String equality (expression changes are significant)
"""

from ..config import EXCLUDED_PROPERTIES
from .diff_result import DiffState, PropertyDiff
from ..domain.property_value import PropertyValue


def should_exclude_property(prop_name: str) -> bool:
    """Check if a property should be excluded from comparison.

    Args:
        prop_name: The name of the property to check

    Returns:
        True if the property should be excluded, False otherwise
    """
    return prop_name in EXCLUDED_PROPERTIES


def values_are_equal(old_value: PropertyValue | None, new_value: PropertyValue | None) -> bool:
    """Compare two property values with type-aware equality.

    This function handles all FreeCAD property types with appropriate
    comparison rules:
    - BOOL, INT, STRING, LINK: Exact equality
    - FLOAT: Approximate equality (tolerance=1e-9)
    - VECTOR: Component-wise approximate equality
    - PLACEMENT: Position + rotation comparison
    - EXPRESSION: String equality

    Args:
        old_value: The old property value (or None)
        new_value: The new property value (or None)

    Returns:
        True if values are equal according to type-specific rules
    """
    # Handle None cases
    if old_value is None and new_value is None:
        return True
    if old_value is None or new_value is None:
        return False

    # Use PropertyValue's built-in equality which handles all types correctly
    return old_value == new_value


def compare_properties(old_props: dict[str, PropertyValue], new_props: dict[str, PropertyValue]) -> list[PropertyDiff]:
    """Compare properties between two nodes and produce a list of PropertyDiff objects.

    This function iterates through all properties in both old and new nodes,
    creates PropertyDiff objects for each property, and filters out excluded
    properties.

    Args:
        old_props: Dictionary of property names to values from the old node
        new_props: Dictionary of property names to values from the new node

    Returns:
        List of PropertyDiff objects for non-excluded properties that have differences
    """
    property_diffs: list[PropertyDiff] = []

    # Get all unique property names from both nodes
    all_prop_names = set(old_props.keys()) | set(new_props.keys())

    for prop_name in all_prop_names:
        # Skip excluded properties
        if should_exclude_property(prop_name):
            continue

        old_value = old_props.get(prop_name)
        new_value = new_props.get(prop_name)

        # Create PropertyDiff for this property
        prop_diff = PropertyDiff(
            property_name=prop_name,
            old_value=old_value,
            new_value=new_value,
        )

        # Only include if there's an actual difference
        if prop_diff.state != DiffState.UNCHANGED:
            property_diffs.append(prop_diff)

    return property_diffs
