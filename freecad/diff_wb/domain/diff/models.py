# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides models for representing the differences between two
# document snapshots, including property-level and node-level comparisons.
#
# This module contains pure data models with embedded state calculation logic.
# It depends on domain/tree/property.py but has no circular dependencies.
"""Domain models for diff results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from ...utils import Log
from ..tree import Property, PropertyType


class DiffState(Enum):
    """The state of a node or property in a diff comparison.

    This is used for UI highlighting to show changes:
    - ADDED: Node/property exists only in the new snapshot
    - DELETED: Node/property exists only in the old snapshot
    - MODIFIED: Node/property exists in both but has different values
    - UNCHANGED: Node/property is identical in both snapshots
    """

    ADDED = auto()
    DELETED = auto()
    MODIFIED = auto()
    UNCHANGED = auto()


# TODO: The generic attribute-based comparison for UNKNOWN types works for many FreeCAD
# objects (Constraint, Vector, Placement, etc.), but may need refinement for specific types.
# Known edge cases and potential improvements:
# - Some FreeCAD objects may have attributes that aren't captured by dir()/getattr()
# - Nested objects may need deep comparison instead of just attribute comparison
# - Performance: The current implementation iterates all attributes for each comparison,
#   which may be slow for objects with many attributes
# Future work: Consider type-specific comparison strategies for known FreeCAD types


def _unknown_values_equal(old_obj: Any, new_obj: Any, float_tolerance: float = 1e-9, prop_name: str = "") -> bool:
    """Compare two UNKNOWN type objects by their attribute values.

    This provides a generic comparison that works for FreeCAD objects like
    Constraint, Vector, Placement, etc., where string representation alone
    doesn't capture actual value differences.

    Args:
        old_obj: The old object value
        new_obj: The new object value
        float_tolerance: Tolerance for comparing float values
        prop_name: The property name for logging purposes

    Returns:
        True if objects have equal attribute values
    """
    if old_obj is new_obj:
        return True
    if old_obj is None or new_obj is None:
        return old_obj is new_obj

    # Get all public attributes (not starting with underscore, not callable)
    old_attrs = _get_comparable_attrs(old_obj)
    new_attrs = _get_comparable_attrs(new_obj)

    # Must have the same attributes
    if old_attrs.keys() != new_attrs.keys():
        return False

    # Compare each attribute value
    for attr_name in old_attrs:
        old_val = old_attrs[attr_name]
        new_val = new_attrs[attr_name]

        if not _attribute_values_equal(old_val, new_val, float_tolerance, prop_name, attr_name):
            return False

    return True


def _get_comparable_attrs(obj: Any) -> dict[str, Any]:
    """Get a dict of comparable public attributes from an object.

    Filters out methods, private attributes, and built-in properties.

    Args:
        obj: The object to inspect

    Returns:
        Dict of attribute name -> value for comparable attributes
    """
    attrs = {}
    for attr_name in dir(obj):
        # Skip private/magic attributes
        if attr_name.startswith("_"):
            continue
        # Skip methods and callables
        try:
            attr_val = getattr(obj, attr_name)
        except AttributeError:
            continue
        if callable(attr_val) and not isinstance(attr_val, type):
            continue
        # Skip non-comparable types (some FreeCAD objects have complex internal state)
        if hasattr(attr_val, "__dict__") and not hasattr(attr_val, "__iter__"):
            # Skip objects that are themselves complex (like other FreeCAD objects)
            continue
        attrs[attr_name] = attr_val
    return attrs


def _attribute_values_equal(  # noqa: C901
    old_val: Any, new_val: Any, float_tolerance: float, prop_name: str = "", attr_name: str = ""
) -> bool:
    """Compare two attribute values for equality.

    Handles floats with tolerance, and iterables by element comparison.

    Args:
        old_val: First value
        new_val: Second value
        float_tolerance: Tolerance for float comparison
        prop_name: The top-level property name for logging
        attr_name: The attribute name being compared

    Returns:
        True if values are equal
    """
    # Same object identity
    if old_val is new_val:
        return True

    # None check
    if old_val is None or new_val is None:
        if old_val is None and new_val is None:
            return True
        # Log the difference
        if prop_name and attr_name:
            Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val!r} -> {new_val!r}")
        return False

    # Float comparison with tolerance
    if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
        if isinstance(old_val, float) or isinstance(new_val, float):
            if abs(old_val - new_val) >= float_tolerance:
                if prop_name and attr_name:
                    Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val} -> {new_val}")
                return False
            return True
        if old_val != new_val:
            if prop_name and attr_name:
                Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val} -> {new_val}")
            return False
        return True

    # Bool comparison (must be exact)
    if isinstance(old_val, bool) or isinstance(new_val, bool):
        if old_val != new_val:
            if prop_name and attr_name:
                Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val} -> {new_val}")
            return False
        return True

    # Iterable comparison (lists, tuples)
    if isinstance(old_val, (list, tuple)) and isinstance(new_val, (list, tuple)):
        if len(old_val) != len(new_val):
            if prop_name and attr_name:
                Log.debug(
                    f"[DIFF] Property '{prop_name}' attribute '{attr_name}' "
                    f"length changed: {len(old_val)} -> {len(new_val)}"
                )
            return False
        for i, (old_item, new_item) in enumerate(zip(old_val, new_val, strict=True)):
            if not _attribute_values_equal(old_item, new_item, float_tolerance, prop_name, f"{attr_name}[{i}]"):
                return False
        return True

    # Direct equality for other types (str, int, etc.)
    try:
        if old_val == new_val:
            return True
        if prop_name and attr_name:
            Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val!r} -> {new_val!r}")
        return False
    except TypeError:
        # Some objects don't support direct comparison
        return False


def _values_are_equal_ignoring_expression(old_value: Property, new_value: Property, prop_name: str = "") -> bool:
    """Compare two property values ignoring expressions.

    Args:
        old_value: Value in the old snapshot
        new_value: Value in the new snapshot
        prop_name: The property name for logging purposes

    Returns:
        True if values are equal ignoring expression differences
    """
    if old_value.type_ != new_value.type_:
        return False
    if old_value.type_ == PropertyType.FLOAT:
        tolerance = 1e-9
        return bool(abs(old_value.value - new_value.value) < tolerance)
    if old_value.type_ == PropertyType.LIST:
        return Property._compare_lists_as_strings(old_value.value, new_value.value)
    # For UNKNOWN types, compare using a generic attribute-based approach
    # that handles FreeCAD objects (e.g., Constraint, Vector, Placement, etc.)
    if old_value.type_ == PropertyType.UNKNOWN:
        return _unknown_values_equal(old_value.value, new_value.value, prop_name=prop_name)
    return bool(old_value.value == new_value.value)


def _calculate_property_diff_state(
    old_value: Property | None, new_value: Property | None, prop_name: str = ""
) -> DiffState:
    """Calculate the diff state for a property based on old and new values.

    Note: Expression changes are tracked separately. This function compares
    only the actual values (ignoring expressions) to determine if the value changed.

    Args:
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        prop_name: The property name for logging purposes

    Returns:
        The appropriate DiffState based on the values
    """
    # If old_value is None, property was added
    if old_value is None:
        return DiffState.ADDED
    # If new_value is None, property was deleted
    if new_value is None:
        return DiffState.DELETED
    # If values are equal (ignoring expressions), unchanged
    values_equal = _values_are_equal_ignoring_expression(old_value, new_value, prop_name)
    if values_equal:
        return DiffState.UNCHANGED
    # Otherwise, modified
    return DiffState.MODIFIED


def _is_vector_like(value: Any) -> bool:
    """Check if value is Vector-like (has x, y, z attributes)."""
    return hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z") and not isinstance(value, (int, float))


def _is_rotation_like(value: Any) -> bool:
    """Check if value is Rotation-like (has angle and axis)."""
    has_angle = hasattr(value, "angle") or hasattr(value, "Angle")
    has_axis = hasattr(value, "axis") or hasattr(value, "Axis")
    return has_angle and has_axis


def _is_placement_like(value: Any) -> bool:
    """Check if value is Placement-like (has position and rotation)."""
    return hasattr(value, "position") and hasattr(value, "rotation")


def _get_property_type_for_primitive(value: Any) -> PropertyType:
    """Infer PropertyType for primitive Python types."""
    if isinstance(value, bool):
        return PropertyType.BOOL
    if isinstance(value, int):
        return PropertyType.INT
    if isinstance(value, float):
        return PropertyType.FLOAT
    if isinstance(value, str):
        return PropertyType.STRING
    return PropertyType.UNKNOWN


def _create_property_from_child_value(value: Any, group: str = "Base") -> Property:
    """Create a Property from a raw child value.

    This wraps raw values from get_children() into Property objects.
    The type is inferred from the value structure.

    Args:
        value: The raw value (Vector, float, Rotation, etc.)
        group: The property group

    Returns:
        A Property object with inferred type
    """
    if value is None:
        return Property(type_=PropertyType.UNKNOWN, value=None, group=group)

    # Check if it's a Vector object
    if _is_vector_like(value):
        return Property(type_=PropertyType.VECTOR, value=value, group=group)

    # Check if it's a Rotation-like object (has angle and axis)
    if _is_rotation_like(value):
        return Property(type_=PropertyType.PLACEMENT, value=value, group=group)

    # Check if it's a Placement object
    if _is_placement_like(value):
        return Property(type_=PropertyType.PLACEMENT, value=value, group=group)

    # Check if it's a list or tuple
    if isinstance(value, (list, tuple)):
        return Property(type_=PropertyType.LIST, value=value, group=group)

    # Check if it's a dict
    if isinstance(value, dict):
        return Property(type_=PropertyType.UNKNOWN, value=value, group=group)

    # For primitives, infer type from Python type
    prop_type = _get_property_type_for_primitive(value)
    return Property(type_=prop_type, value=value, group=group)


def _compute_property_children(
    old_value: Property | None, new_value: Property | None, parent_prop_name: str = ""
) -> list[PropertyDiff]:
    """Compute child property diffs for expandable properties.

    Args:
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        parent_prop_name: The parent property name for logging purposes

    Returns:
        List of PropertyDiff for child properties
    """
    children: list[PropertyDiff] = []

    old_children = old_value.get_children() if old_value else []
    new_children = new_value.get_children() if new_value else []

    old_child_map = dict(old_children)
    new_child_map = dict(new_children)

    all_child_names = set(old_child_map.keys()) | set(new_child_map.keys())

    for child_name in sorted(all_child_names):
        raw_old_child = old_child_map.get(child_name)
        raw_new_child = new_child_map.get(child_name)

        # Wrap raw values in Property objects
        old_child_prop = _create_property_from_child_value(raw_old_child) if raw_old_child is not None else None
        new_child_prop = _create_property_from_child_value(raw_new_child) if raw_new_child is not None else None

        # For child properties, prepend parent name to create a full path for logging
        full_prop_name = f"{parent_prop_name}[{child_name}]" if parent_prop_name else child_name

        child_diff = PropertyDiff(
            property_name=child_name,
            old_value=old_child_prop,
            new_value=new_child_prop,
            _parent_prop_name=full_prop_name,
        )

        children.append(child_diff)

    return children


def _has_expression_change(old_value: Property | None, new_value: Property | None) -> bool:
    """Check if there's an expression change between two property values."""
    if old_value is None or new_value is None:
        return True
    return old_value.expression != new_value.expression


def _are_properties_modified(property_diffs: list[PropertyDiff], children: list[NodeDiff]) -> bool:
    """Check if any properties or children have modifications.

    A node's properties are considered modified if:
    - Any child node has state != DiffState.UNCHANGED
    - Any property has state != DiffState.UNCHANGED (includes ADDED, DELETED, MODIFIED)
    - Any property has children with state != DiffState.UNCHANGED (e.g., constraint items)
    - Any property has an expression change (even if value is unchanged)

    Args:
        property_diffs: List of property diffs for this node
        children: List of child node diffs

    Returns:
        True if any properties or children are modified, False otherwise
    """
    # Check child node states - if any child node has changes, properties are modified
    if any(child.state != DiffState.UNCHANGED for child in children):
        return True

    # Check if any property has changed (ADDED, DELETED, or MODIFIED)
    if any(prop_diff.state != DiffState.UNCHANGED for prop_diff in property_diffs):
        return True

    # Check if any property has children with changes (e.g., individual constraint items)
    for prop_diff in property_diffs:
        if prop_diff.children and any(child.state != DiffState.UNCHANGED for child in prop_diff.children):
            return True

    # Check if any property has expression changes (value may be unchanged but expression changed)
    return any(_has_expression_change(prop_diff.old_value, prop_diff.new_value) for prop_diff in property_diffs)


@dataclass(frozen=True)
class PropertyDiff:
    """The difference between two property values.

    The state is automatically calculated based on the old and new values
    (including their expressions). This ensures consistency and prevents
    invalid states where the state doesn't match the actual values.

    Attributes:
        property_name: Name of the property
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        state: The diff state (ADDED, DELETED, MODIFIED, UNCHANGED) - auto-calculated
        children: List of child property diffs for expandable properties
        _parent_prop_name: Internal field for full property path (e.g., "Constraints[0]")
    """

    property_name: str
    old_value: Property | None
    new_value: Property | None
    state: DiffState = field(init=False)
    children: list[PropertyDiff] = field(default_factory=list)
    _parent_prop_name: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        """Calculate state and children based on old and new values."""
        # Use object.__setattr__ since the dataclass is frozen
        # Use _parent_prop_name if set (for child properties), otherwise use property_name
        full_prop_name = self._parent_prop_name or self.property_name
        object.__setattr__(
            self, "state", _calculate_property_diff_state(self.old_value, self.new_value, full_prop_name)
        )
        # Compute children for expandable properties (pass property_name as parent)
        object.__setattr__(
            self, "children", _compute_property_children(self.old_value, self.new_value, self.property_name)
        )

    def __str__(self) -> str:
        if self.state == DiffState.ADDED:
            return f"{self.property_name}: +{self.new_value}"
        elif self.state == DiffState.DELETED:
            return f"{self.property_name}: -{self.old_value}"
        elif self.state == DiffState.MODIFIED:
            return f"{self.property_name}: {self.old_value} -> {self.new_value}"
        return f"{self.property_name}: {self.old_value}"


@dataclass(frozen=True)
class NodeDiff:
    """The difference between two tree nodes.

    Represents the diff result for a single node in the document tree,
    including its properties and children.

    The state is automatically calculated based on property diffs and children:
    - If `_force_state` is set (by factory functions), that state is used
    - Otherwise, state is MODIFIED if any property/child has changes, UNCHANGED otherwise

    This separates node-level changes (entire node added/deleted) from
    property-level changes (properties modified/added/deleted).

    Attributes:
        path: The path to this node (for backward compatibility, same as new_path)
        type_id: The TypeID of the node
        state: The overall state of this node - auto-calculated or forced
        property_diffs: List of property-level differences
        children: List of child node diffs
        old_path: Path in old snapshot (None for added nodes). Used for move detection.
        new_path: Path in new snapshot (None for deleted nodes). Used for move detection.
        old_after: The 'after' field in old snapshot (None for added/root nodes).
            Used for reorder detection.
        new_after: The 'after' field in new snapshot (None for deleted/root nodes).
            Used for reorder detection.
        _force_state: Internal override for state calculation. Only used by
            factory functions (`create_added_node_diff`, `create_deleted_node_diff`)
            to indicate node-level changes (ADDED/DELETED). When None, state is
            calculated from property_diffs (MODIFIED/UNCHANGED). Not included in
            repr or comparison.
    """

    path: str
    type_id: str
    state: DiffState = field(init=False)
    property_diffs: list[PropertyDiff] = field(default_factory=list)
    children: list[NodeDiff] = field(default_factory=list)
    old_path: str | None = field(default=None)
    new_path: str | None = field(default=None)
    old_after: str | None = field(default=None)
    new_after: str | None = field(default=None)
    _force_state: DiffState | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Calculate state based on _force_state or property diffs.

        State calculation logic:
        1. If _force_state is set (node-level change), use that state
        2. Otherwise, check if any properties/children are modified
        3. Return MODIFIED if changes exist, UNCHANGED otherwise
        """
        # Use object.__setattr__ since the dataclass is frozen
        if self._force_state is not None:
            object.__setattr__(self, "state", self._force_state)
        elif _are_properties_modified(self.property_diffs, self.children):
            object.__setattr__(self, "state", DiffState.MODIFIED)
        else:
            object.__setattr__(self, "state", DiffState.UNCHANGED)

    def __str__(self) -> str:
        state_str = self.state.name
        prop_count = len(self.property_diffs)
        child_count = len(self.children)
        return f"NodeDiff({self.path}, {state_str}, {prop_count} props, {child_count} children)"

    @property
    def has_changes(self) -> bool:
        """Check if this node or any children have changes."""
        if self.state != DiffState.UNCHANGED:
            return True
        # Check if any property diff has changes (not just if property_diffs exists)
        if any(p.state != DiffState.UNCHANGED for p in self.property_diffs):
            return True
        return any(child.has_changes for child in self.children)

    @property
    def changed_properties(self) -> list[PropertyDiff]:
        """Get only the properties that actually changed."""
        return [p for p in self.property_diffs if p.state != DiffState.UNCHANGED]


@dataclass(frozen=True)
class DiffResult:
    """The complete result of comparing two snapshots.

    Represents all differences between an old and new snapshot, organized
    as a tree structure that mirrors the original document hierarchy.

    Attributes:
        old_snapshot_name: Name/identifier of the old snapshot
        new_snapshot_name: Name/identifier of the new snapshot
        added_count: Number of added nodes
        deleted_count: Number of deleted nodes
        modified_count: Number of modified nodes
        hierarchy: The DiffHierarchy containing the node diffs in tree form
    """

    old_snapshot_name: str
    new_snapshot_name: str
    added_count: int = 0
    deleted_count: int = 0
    modified_count: int = 0
    hierarchy: DiffHierarchy = field(default_factory=lambda: DiffHierarchy())

    def __str__(self) -> str:
        return (
            f"DiffResult({self.old_snapshot_name} vs {self.new_snapshot_name}): "
            f"{self.added_count} added, {self.deleted_count} deleted, {self.modified_count} modified"
        )

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes in this diff."""
        return (self.added_count > 0 or self.deleted_count > 0 or self.modified_count > 0) or any(
            node.has_changes for node in self.hierarchy.roots
        )

    def get_all_changed_paths(self) -> list[str]:
        """Get all paths that have changes (for UI highlighting)."""
        changed_paths: list[str] = []
        for node_diff in self.hierarchy.roots:
            self._collect_changed_paths(node_diff, changed_paths)
        return changed_paths

    def _collect_changed_paths(self, node: NodeDiff, result: list[str]) -> None:
        """Recursively collect paths with changes."""
        if node.has_changes:
            result.append(node.path)
        for child in node.children:
            self._collect_changed_paths(child, result)


class DiffHierarchy:
    """Holds hierarchical node diffs as a tree structure.

    This class manages the hierarchical organization of NodeDiff objects,
    providing efficient path-based lookups and parent-child relationships.

    Attributes:
        _hierarchy: Nested dict mapping path segments to NodeDiff objects
        _roots: List of top-level NodeDiff objects
    """

    def __init__(self) -> None:
        """Initialize an empty hierarchy."""
        self._hierarchy: dict[str, Any] = {}
        self._roots: list[NodeDiff] = []

    @property
    def roots(self) -> list[NodeDiff]:
        """Get list of top-level NodeDiff objects."""
        return self._roots

    def find_by_path(self, path: str) -> NodeDiff | None:
        """Find a NodeDiff by its path.

        Args:
            path: The path to search for (e.g., "Body/Pad")

        Returns:
            The NodeDiff at the given path, or None if not found
        """
        if not path:
            return None

        # Split path into segments
        segments = path.split("/")

        # Traverse the hierarchy
        current: dict[str, Any] | None = self._hierarchy
        for i, segment in enumerate(segments):
            if not segment:
                continue
            if isinstance(current, dict) and segment in current:
                value = current[segment]

                if i == len(segments) - 1:
                    # This is the final segment, return the NodeDiff
                    if isinstance(value, NodeDiff):
                        return value
                    elif isinstance(value, dict):
                        # Might have __node__ key
                        return value.get("__node__")
                    return None

                # Move to children
                if isinstance(value, dict):
                    current = value.get("__children__")
                else:
                    # It's a NodeDiff, its children are in NodeDiff.children
                    return None
            else:
                return None
        return None

    def add_node(self, node_diff: NodeDiff) -> None:
        """Add a NodeDiff to the hierarchy.

        Handles parent linking automatically - if the parent exists in the
        hierarchy, the node is added as a child. If no parent exists,
        the node is added to roots.

        Args:
            node_diff: The NodeDiff to add
        """
        path = node_diff.path
        if not path:
            return

        segments = path.split("/")

        if len(segments) == 1:
            # Root level node
            self._roots.append(node_diff)
            self._hierarchy[segments[0]] = node_diff
            return

        # Find or create parent path
        parent_segments = segments[:-1]
        parent_path = "/".join(parent_segments)

        # Try to find parent in hierarchy
        parent_node = self.find_by_path(parent_path)

        if parent_node is not None:
            # Add as child to existing parent, but only if not already present
            # (to avoid infinite loops when node_diffs already has children set)
            if node_diff not in parent_node.children:
                parent_node.children.append(node_diff)
        else:
            # No parent found, add to roots
            self._roots.append(node_diff)

        # Store in hierarchy dict
        self._ensure_parent_segments(path, segments, parent_node)
        self._store_node_in_hierarchy(segments, node_diff)

    def _ensure_parent_segments(self, path: str, segments: list[str], parent_node: NodeDiff | None) -> None:
        """Ensure parent segment dict containers exist in hierarchy.

        Args:
            path: Full path of the node being added
            segments: Path segments
            parent_node: Parent NodeDiff if found, None otherwise
        """
        current = self._hierarchy
        for segment in segments[:-1]:  # Process all but last segment
            if segment not in current:
                # Only raise error if parent NodeDiff was supposed to exist
                if parent_node is not None:
                    raise ValueError(
                        f"Parent segment '{segment}' not found in hierarchy for path '{path}'. "
                        f"Parent paths must be created before adding child nodes."
                    )
                # Create dict container for orphaned child (no parent NodeDiff)
                current[segment] = {"__children__": {}}
            elif isinstance(current[segment], NodeDiff):
                existing_node = current[segment]
                current[segment] = {"__children__": {}, "__node__": existing_node}

            # Move to children dict
            if isinstance(current[segment], dict):
                current = current[segment].get("__children__", {})
            else:
                break

    def _store_node_in_hierarchy(self, segments: list[str], node_diff: NodeDiff) -> None:
        """Store the final node in the hierarchy dict.

        Args:
            segments: Path segments
            node_diff: The node to store
        """
        current = self._hierarchy
        # Navigate to parent dict
        for segment in segments[:-1]:
            if isinstance(current.get(segment), dict):
                current = current[segment].get("__children__", {})
            else:
                break

        # Store the final node
        final_segment = segments[-1]
        if final_segment not in current:
            current[final_segment] = node_diff


__all__ = ["DiffResult", "DiffHierarchy", "NodeDiff", "PropertyDiff", "DiffState"]
