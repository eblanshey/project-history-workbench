# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains the SnapshotExtractor class which extracts
# tree structure from FreeCAD documents and converts them to Snapshot domain models.
# It uses simplified hierarchy detection (Group + OriginFeatures + InList) instead of
# OutList traversal to correctly build visual containment hierarchy.
"""Snapshot extraction from FreeCAD documents."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from ...utils import Log
from ..ports import DocumentLike, FreeCadPort
from ..tree import Property, TreeNode


if TYPE_CHECKING:
    from .models import Snapshot


def _get_expression_for_property(obj: object, prop_name: str) -> str | None:
    """Extract the expression for a specific property from ExpressionEngine.

    FreeCAD stores expressions (e.g., "Pad.Length * 2") in the ExpressionEngine
    property as a list of [property_name, expression_string] pairs. This function
    searches that list for the given property and returns its expression.

    Example ExpressionEngine value:
        [
            ["Length", "Pad.Length * 2"],
            ["Width", "Sketch.X"],
            ["Height", "10 mm"]
        ]

    Args:
        obj: The FreeCAD object (has ExpressionEngine attribute)
        prop_name: The property name to get expression for

    Returns:
        The expression string if found (e.g., "Pad.Length * 2"), None otherwise
    """
    try:
        expr_engine = getattr(obj, "ExpressionEngine", [])
        if isinstance(expr_engine, list):
            for entry in expr_engine:
                if isinstance(entry, (list, tuple)) and len(entry) >= 2 and entry[0] == prop_name:
                    return str(entry[1])
    except Exception:
        pass
    return None


def _extract_property_value(obj: object, prop_name: str) -> Property | None:
    """Extract a single property value from a FreeCAD object.

    Delegates to Property.from_freecad_property() which handles
    type detection based on property names (e.g., "Placement", "Position")
    and value-based inference for unknown properties.

    Args:
        obj: The FreeCAD object
        prop_name: The property name

    Returns:
        A Property if successful, None if the property couldn't be read
    """
    try:
        # TODO: delay instantiating props until later -- might not even be needed until their raw output is
        #    considered different
        value = getattr(obj, prop_name)
        expression = _get_expression_for_property(obj, prop_name)
        return Property.from_freecad_property(prop_name, value, expression=expression)
    except Exception as e:
        logging.warning("Failed to extract property %s: %s", prop_name, e)
        return None


def _find_parent_via_group_and_origin(doc: DocumentLike, child_name: str, parent_map: dict[str, str]) -> None:
    """Find parent for an object via Group and OriginFeatures properties.

    Args:
        doc: The FreeCAD document
        child_name: Name of the child object to find parent for
        parent_map: Mutable dict to store found parent
    """
    if child_name in parent_map:
        return

    for container_obj in doc.Objects:
        if not hasattr(container_obj, "Name"):
            continue
        container_name = container_obj.Name

        # Check Group property (visual group contents for App::Part, App::VarSet, etc.)
        group = getattr(container_obj, "Group", [])
        group_names = [g.Name for g in group if hasattr(g, "Name")]
        if child_name in group_names:
            parent_map[child_name] = container_name
            return

        # Check OriginFeatures (origin geometry for App::Origin containers)
        origin_features = getattr(container_obj, "OriginFeatures", [])
        origin_feature_names = [f.Name for f in origin_features if hasattr(f, "Name")]
        if child_name in origin_feature_names:
            parent_map[child_name] = container_name
            return


def _find_parent_via_inlist(doc: DocumentLike, parent_map: dict[str, str]) -> None:
    """Find parents for remaining objects via InList property.

    This handles cases where Origins/Orphans reference their parent containers.
    Only assigns parents that are container types (App::Part, PartDesign::Body).

    Args:
        doc: The FreeCAD document
        parent_map: Mutable dict to store found parents
    """
    for obj_without_parent in doc.Objects:
        if not hasattr(obj_without_parent, "Name"):
            continue
        obj_name = obj_without_parent.Name

        if obj_name in parent_map:
            continue

        # Check InList for container references
        in_list = getattr(obj_without_parent, "InList", [])
        for parent_obj in in_list:
            if hasattr(parent_obj, "Name"):
                parent_name = parent_obj.Name
                parent_type = getattr(parent_obj, "TypeId", "")
                # Only assign parent if it's a container type (App::Part, PartDesign::Body)
                if parent_type in ("App::Part", "PartDesign::Body"):
                    parent_map[obj_name] = parent_name
                    break


def _build_children_map(doc: DocumentLike, parent_map: dict[str, str]) -> dict[str, list[str]]:
    """Build children map from parent map, preserving doc.Objects iteration order.

    This ensures children appear in the same order as they were created in the document.

    Args:
        doc: The FreeCAD document
        parent_map: Dict of {child_name: parent_name}

    Returns:
        children_map: {parent_name: [child_name, ...]}
    """
    children_map: dict[str, list[str]] = {}

    for obj_in_order in doc.Objects:
        if not hasattr(obj_in_order, "Name"):
            continue
        obj_name = obj_in_order.Name
        parent_name = parent_map.get(obj_name)

        if parent_name:
            if parent_name not in children_map:
                children_map[parent_name] = []
            children_map[parent_name].append(obj_name)

    return children_map


def _build_hierarchy_map(doc: DocumentLike) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Build parent and children maps using Group, OriginFeatures, and InList.

    This uses simplified hierarchy detection instead of OutList traversal.
    OutList represents ALL object references (dependencies), not visual containment
    hierarchy, which caused bugs where nodes appeared at wrong levels.

    Args:
        doc: The FreeCAD document

    Returns:
        Tuple of (parent_map, children_map) where:
        - parent_map: {child_name: parent_name}
        - children_map: {parent_name: [child_name, ...]} preserving doc.Objects order
    """
    # First pass: determine parent for each object using Group and OriginFeatures
    parent_map: dict[str, str] = {}

    for child_obj in doc.Objects:
        if not hasattr(child_obj, "Name"):
            continue
        child_name = child_obj.Name
        _find_parent_via_group_and_origin(doc, child_name, parent_map)

    # Second pass: check InList for objects still without parent
    _find_parent_via_inlist(doc, parent_map)

    # Third pass: Build children map preserving doc.Objects iteration order
    children_map = _build_children_map(doc, parent_map)

    return parent_map, children_map


def _build_tree_node(
    obj: object,
    port: FreeCadPort,
    doc: DocumentLike,
    parent_path: str,
    children_map: dict[str, list[str]],
    is_root: bool = True,
) -> TreeNode | None:  # noqa: C901
    """Build a TreeNode from a FreeCAD object.

    Uses simplified hierarchy detection based on Group, OriginFeatures, and InList
    instead of OutList traversal. OutList represents ALL object references (dependencies),
    not visual containment hierarchy, which caused bugs where nodes appeared at wrong levels.

    Args:
        obj: The FreeCAD object to convert
        port: The FreeCadPort instance for object resolution
        doc: The FreeCAD document
        parent_path: The path of the parent node (for building full path)
        children_map: Pre-built children map from _build_hierarchy_map().
                     Must be provided - built once in extract_tree() for efficiency.
        is_root: Whether this is a root-level object

    Returns:
        A TreeNode for the object with all properties and children.
    """
    # Get basic attributes
    name = getattr(obj, "Name", "")
    type_id = getattr(obj, "TypeId", "")
    label = getattr(obj, "Label", name)

    # Build the full path
    path = f"{parent_path}/{name}" if parent_path else name
    Log.info(f"[EXTRACTOR] Building node: name={name}, type={type_id}, parent_path='{parent_path}', full_path='{path}'")

    # Extract all properties (no filtering - snapshots capture everything)
    properties: dict[str, Property] = {}
    try:
        properties_list = getattr(obj, "PropertiesList", [])
        for prop_name in properties_list:
            prop_value = _extract_property_value(obj, prop_name)
            if prop_value is not None:
                properties[prop_name] = prop_value
    except Exception:
        # If we can't read properties, continue with empty dict
        pass

    # Build children TreeNodes from the pre-built children map
    children: list[TreeNode] = []
    child_names = children_map.get(name, [])
    for child_name in child_names:
        child_obj = port.get_object(doc, child_name)
        if child_obj is not None:
            child_node = _build_tree_node(child_obj, port, doc, path, children_map, is_root=False)
            if child_node is not None:
                children.append(child_node)

    return TreeNode(
        name=name,
        type_id=type_id,
        label=label,
        path=path,
        is_root=is_root,
        properties=properties,
        children=children,
    )


class SnapshotExtractor:
    """Extracts tree structure from FreeCAD documents.

    This class extracts the document tree structure from a live
    FreeCAD document and converts it to Snapshot domain models. Uses the
    unified Log class from utils for logging.
    """

    def __init__(self) -> None:
        """Initialize the extractor."""
        pass

    def extract_tree(self, port: FreeCadPort | None = None) -> Snapshot:
        """Extract the document tree structure from the active FreeCAD document.

        This function traverses the active FreeCAD document and converts it into
        a Snapshot domain object containing TreeNode hierarchy.

        Args:
            port: Optional FreeCadPort instance. If None, returns empty snapshot.

        Returns:
            A Snapshot object containing the document tree structure.
            Returns an empty Snapshot if no port provided or extraction fails.
        """
        from .models import Snapshot

        if port is None:
            Log.info("No port provided, returning empty snapshot")
            return Snapshot(
                snapshot_id=str(uuid.uuid4()), document_name="NoPort", timestamp=datetime.now(), root_nodes=[]
            )

        doc = port.get_active_document()

        if doc is None:
            # No document open, return empty snapshot
            Log.info("No document open, returning empty snapshot")
            return Snapshot(
                snapshot_id=str(uuid.uuid4()), document_name="NoDocument", timestamp=datetime.now(), root_nodes=[]
            )

        document_name = getattr(doc, "Name", "Unnamed")
        root_nodes: list[TreeNode] = []

        try:
            # Get all top-level objects from the document
            objects = getattr(doc, "Objects", [])
            Log.info(f"[EXTRACTOR] Document '{document_name}' has {len(objects)} top-level objects")

            # Build hierarchy map once - used for both root filtering and child building
            parent_map, children_map = _build_hierarchy_map(doc)

            for obj in objects:
                if not hasattr(obj, "Name"):
                    # Skip invalid objects
                    Log.warning("Skipping object without Name attribute")
                    continue

                name = obj.Name
                # Skip objects that have parents - they will be included as children
                if name in parent_map:
                    Log.info(f"[EXTRACTOR] Skipping {name} - it's a child of {parent_map[name]}")
                    continue

                node = _build_tree_node(obj, port, doc, "", children_map, is_root=True)
                if node is not None:
                    root_nodes.append(node)
                    Log.info(
                        f"[EXTRACTOR] Added root node: {node.path} ({node.type_id}), children={len(node.children)}"
                    )

        except Exception as e:
            Log.error(f"Error extracting document tree: {e}")

        # Use current time for timestamp
        timestamp = datetime.now()
        Log.info(f"[EXTRACTOR] Extracted {len(root_nodes)} root nodes: {[r.path for r in root_nodes]}")

        return Snapshot(
            snapshot_id=str(uuid.uuid4()), document_name=document_name, timestamp=timestamp, root_nodes=root_nodes
        )
