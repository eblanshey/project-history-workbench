# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tree comparison algorithm with path-based indexing.

File responsibility: This module provides efficient tree comparison algorithms
that use path-based indexing for O(n+m) performance. It compares two document
snapshots and produces a hierarchical structure of NodeDiff objects representing
added, deleted, and modified nodes.

The algorithm:
1. Build path index for old snapshot (O(n))
2. Build path index for new snapshot (O(m))
3. Find added paths (in new but not old)
4. Find deleted paths (in old but not new)
5. Find common paths and compare nodes
6. Reconstruct hierarchical structure from flat list
"""

from dataclasses import dataclass

from .diff_result import DiffState, NodeDiff, PropertyDiff
from ..domain.snapshot import Snapshot, TreeNode
from ..domain.property_value import PropertyValue, PropertyType
from .property_diff import compare_properties


@dataclass(frozen=True)
class TreeDiffResult:
    """Result of comparing two tree snapshots.

    Attributes:
        old_snapshot: The old snapshot that was compared
        new_snapshot: The new snapshot that was compared
        added_paths: Set of paths that exist only in the new snapshot
        deleted_paths: Set of paths that exist only in the old snapshot
        common_paths: Set of paths that exist in both snapshots
        node_diffs: Hierarchical list of NodeDiff objects
    """

    old_snapshot: Snapshot
    new_snapshot: Snapshot
    added_paths: set[str]
    deleted_paths: set[str]
    common_paths: set[str]
    node_diffs: list[NodeDiff]


def build_path_index(root_nodes: list[TreeNode]) -> dict[str, TreeNode]:
    """Build a path-based index for O(1) node lookups.

    Traverses the tree recursively and creates a dictionary mapping each
    node's path to the node itself. This enables efficient comparison
    without nested iteration.

    Args:
        root_nodes: List of root tree nodes to index

    Returns:
        Dictionary mapping path strings to TreeNode objects
    """
    index: dict[str, TreeNode] = {}

    def _index_nodes(node: TreeNode) -> None:
        index[node.path] = node
        for child in node.children:
            _index_nodes(child)

    for root in root_nodes:
        _index_nodes(root)

    return index


def find_added_paths(old_index: dict[str, TreeNode], new_index: dict[str, TreeNode]) -> set[str]:
    """Find paths that exist only in the new snapshot.

    Args:
        old_index: Path index for the old snapshot
        new_index: Path index for the new snapshot

    Returns:
        Set of paths that are in new but not in old
    """
    return set(new_index.keys()) - set(old_index.keys())


def find_deleted_paths(old_index: dict[str, TreeNode], new_index: dict[str, TreeNode]) -> set[str]:
    """Find paths that exist only in the old snapshot.

    Args:
        old_index: Path index for the old snapshot
        new_index: Path index for the new snapshot

    Returns:
        Set of paths that are in old but not in new
    """
    return set(old_index.keys()) - set(new_index.keys())


def find_common_paths(old_index: dict[str, TreeNode], new_index: dict[str, TreeNode]) -> set[str]:
    """Find paths that exist in both snapshots.

    Args:
        old_index: Path index for the old snapshot
        new_index: Path index for the new snapshot

    Returns:
        Set of paths that exist in both snapshots
    """
    return set(old_index.keys()) & set(new_index.keys())


def compare_nodes_by_path(
    path: str,
    old_index: dict[str, TreeNode],
    new_index: dict[str, TreeNode],
) -> NodeDiff | None:
    """Compare two nodes at the same path and produce a NodeDiff.

    This function compares the properties of two nodes using the property_diff
    module and determines if they have been modified. If no properties differ
    (after filtering excluded properties), returns None.

    Args:
        path: The path to compare
        old_index: Path index for the old snapshot
        new_index: Path index for the new snapshot

    Returns:
        NodeDiff if properties differ, None otherwise
    """
    old_node = old_index.get(path)
    new_node = new_index.get(path)

    if old_node is None or new_node is None:
        return None

    # Use property_diff module to compare properties with exclusion filtering
    property_diffs = compare_properties(old_node.properties, new_node.properties)

    # If no property differences (all excluded or identical), return None
    if not property_diffs:
        return None

    # Return NodeDiff with populated property diffs
    # State will be automatically calculated in __post_init__ based on property_diffs
    return NodeDiff(
        path=path,
        type_id=new_node.type_id,
        property_diffs=property_diffs,
        children=[],  # Will be populated recursively by reconstruct_hierarchy
    )


def create_added_node_diff(path: str, node: TreeNode) -> NodeDiff:
    """Create a NodeDiff for an added node.

    This is called for nodes that exist only in the new snapshot (not in old).
    The entire node is considered ADDED, regardless of its properties.

    Args:
        path: The path of the added node
        node: The TreeNode from the new snapshot

    Returns:
        NodeDiff with ADDED state
    """
    # For added nodes, all properties are "added" (old_value=None)
    property_diffs = compare_properties({}, node.properties)

    return NodeDiff(
        path=path,
        type_id=node.type_id,
        property_diffs=property_diffs,
        children=[],  # Will be populated recursively
        _force_state=DiffState.ADDED,
    )


def create_deleted_node_diff(path: str, node: TreeNode) -> NodeDiff:
    """Create a NodeDiff for a deleted node.

    This is called for nodes that exist only in the old snapshot (not in new).
    The entire node is considered DELETED, regardless of its properties.

    Args:
        path: The path of the deleted node
        node: The TreeNode from the old snapshot

    Returns:
        NodeDiff with DELETED state
    """
    # For deleted nodes, all properties are "deleted" (new_value=None)
    property_diffs = compare_properties(node.properties, {})

    return NodeDiff(
        path=path,
        type_id=node.type_id,
        property_diffs=property_diffs,
        children=[],  # Will be populated recursively
        _force_state=DiffState.DELETED,
    )


def reconstruct_hierarchy(node_diffs: list[NodeDiff]) -> list[NodeDiff]:
    """Reconstruct hierarchical structure from a flat list of NodeDiff objects.

    Takes a list of NodeDiff objects (which may be at various depths) and
    organizes them into a proper tree structure based on path hierarchy.
    The result is sorted so that parents appear before their children,
    and siblings are sorted alphabetically by path.

    Args:
        node_diffs: Flat list of NodeDiff objects

    Returns:
        Hierarchical list of NodeDiff objects with children properly nested
        and sorted in tree order (parents before children, siblings alphabetically)
    """
    if not node_diffs:
        return []

    # Sort node_diffs by path to ensure consistent ordering:
    # - Parents before children (shorter paths first when they are prefixes)
    # - Siblings sorted alphabetically
    sorted_node_diffs = sorted(node_diffs, key=lambda d: d.path.split("/"))

    # Build a lookup dictionary for quick access
    diff_by_path: dict[str, NodeDiff] = {diff.path: diff for diff in sorted_node_diffs}

    # Track which nodes have been added as children
    has_parent: set[str] = set()

    # First pass: establish parent-child relationships
    # Iterate over sorted_node_diffs to ensure children are added in sorted order
    for diff in sorted_node_diffs:
        path_parts = diff.path.split("/")
        if len(path_parts) > 1:
            # This node has a potential parent
            parent_path = "/".join(path_parts[:-1])
            if parent_path in diff_by_path:
                parent_diff = diff_by_path[parent_path]
                # Add this node as a child of its parent
                # Since NodeDiff is frozen, we need to use object.__setattr__
                object.__setattr__(parent_diff, "children", parent_diff.children + [diff])
                has_parent.add(diff.path)

    # Second pass: collect root nodes (nodes without parents in the diff list)
    # Use sorted_node_diffs to maintain consistent ordering
    root_diffs: list[NodeDiff] = []
    for diff in sorted_node_diffs:
        if diff.path not in has_parent:
            root_diffs.append(diff)

    return root_diffs


def compare_snapshots(old_snapshot: Snapshot, new_snapshot: Snapshot) -> TreeDiffResult:
    """Compare two snapshots and produce a hierarchical diff result.

    This is the main entry point for tree comparison. It uses path-based
    indexing to achieve O(n+m) performance where n and m are the number
    of nodes in each snapshot.

    Args:
        old_snapshot: The old snapshot to compare
        new_snapshot: The new snapshot to compare

    Returns:
        TreeDiffResult containing all comparison results
    """
    # Build path indices for both snapshots
    old_index = build_path_index(old_snapshot.root_nodes)
    new_index = build_path_index(new_snapshot.root_nodes)

    # Find added, deleted, and common paths
    added_paths = find_added_paths(old_index, new_index)
    deleted_paths = find_deleted_paths(old_index, new_index)
    common_paths = find_common_paths(old_index, new_index)

    # Collect all NodeDiff objects
    all_node_diffs: list[NodeDiff] = []

    # Create NodeDiff for added paths
    for path in added_paths:
        node = new_index[path]
        all_node_diffs.append(create_added_node_diff(path, node))

    # Create NodeDiff for deleted paths
    for path in deleted_paths:
        node = old_index[path]
        all_node_diffs.append(create_deleted_node_diff(path, node))

    # Compare common paths
    for path in common_paths:
        node_diff = compare_nodes_by_path(path, old_index, new_index)
        if node_diff is not None:
            all_node_diffs.append(node_diff)

    # Reconstruct hierarchy
    hierarchical_diffs = reconstruct_hierarchy(all_node_diffs)

    return TreeDiffResult(
        old_snapshot=old_snapshot,
        new_snapshot=new_snapshot,
        added_paths=added_paths,
        deleted_paths=deleted_paths,
        common_paths=common_paths,
        node_diffs=hierarchical_diffs,
    )
