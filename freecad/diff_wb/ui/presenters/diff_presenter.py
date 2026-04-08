"""File responsibility: Diff result presenter for UI."""

from typing import Any

from ...domain.diff.engine import DiffResult
from ...domain.diff.models import DiffState, NodeDiff, PropertyDiff
from ...domain.tree import Property
from ...utils import Log
from ..protocols.diff_view import DiffView
from .presentation_models import NodePresentation, PropertyPresentation


class DiffPresenter:
    """Transform DiffResult into presentation models and call view methods.

    This presenter transforms domain-level diff results into UI-friendly
    presentation models, then calls view protocol methods to trigger
    the actual UI rendering.

    Dependencies are injected for testability.
    """

    def __init__(self, view: DiffView) -> None:
        """Initialize with required dependencies.

        Args:
            view: DiffView implementation to display diff results
        """
        self._view = view

    def present_diff(self, diff_result: DiffResult) -> None:
        """Transform domain data and call view methods to render UI.

        Args:
            diff_result: DiffResult from CompareSnapshotsAction.execute()
        """
        # Store diff result for property lookup
        self._diff_result = diff_result

        # Transform domain objects to presentation models
        nodes = [self._format_node(node) for node in diff_result.hierarchy.roots]

        # Call view methods to trigger UI rendering
        self._view.show_diff_tree(nodes)
        # Pass raw integers - view handles translation and formatting using
        # individual labels (DIFF_SUMMARY_ADDED_LABEL, etc.) per user decision
        # Use explicit counts from DiffResult
        self._view.show_summary(
            added=diff_result.added_count,
            deleted=diff_result.deleted_count,
            modified=diff_result.modified_count,
        )

    def _format_node(self, node_diff: NodeDiff) -> NodePresentation:
        """Transform domain NodeDiff to presentation model.

        Args:
            node_diff: Domain NodeDiff from diff engine

        Returns:
            NodePresentation suitable for UI display
        """
        return NodePresentation(
            path=node_diff.path,
            type_id=node_diff.type_id,
            state=node_diff.state,
            has_changes=node_diff.has_changes,
            children=[self._format_node(child) for child in node_diff.children],
        )

    def on_node_selected(self, path: str) -> None:
        """Handle tree node selection to display property diffs.

        Called by view when user clicks a node in the diff tree.
        Looks up the property diffs for that path and displays them.

        Args:
            path: The path of the selected node (from QTreeWidgetItem.UserRole)
        """
        # Guard: No diff result stored
        if not hasattr(self, "_diff_result") or self._diff_result is None:
            self._view.show_properties([])
            return

        # Find NodeDiff by path using hierarchy lookup
        node_diff = self._diff_result.hierarchy.find_by_path(path)

        # If not found, clear properties
        if node_diff is None:
            Log.debug(f"[PRESENTER] NodeDiff not found for path: {path}")
            self._view.show_properties([])
            return

        # Transform property diffs to presentations
        properties = self._transform_property_diffs(node_diff)
        Log.debug(f"[PRESENTER] Transformed to {len(properties)} PropertyPresentation")
        self._view.show_properties(properties)

    def _transform_property_diffs(self, node_diff: NodeDiff) -> list[PropertyPresentation]:
        """Transform domain PropertyDiff to presentation format.

        Expression changes appear as separate rows.

        Args:
            node_diff: Domain NodeDiff with property_diffs

        Returns:
            List of PropertyPresentation for UI display
        """
        presentations = []

        for prop_diff in node_diff.property_diffs:
            # Determine group from the property value
            # Use new_value's group if available, otherwise old_value's group
            group = self._extract_property_group(
                prop_diff.new_value if prop_diff.new_value is not None else prop_diff.old_value
            )

            # Extract old_value and new_value for expandable properties
            old_value = self._extract_property_value(prop_diff.old_value)
            new_value = self._extract_property_value(prop_diff.new_value)

            # Transform children recursively from domain PropertyDiff
            children = self._transform_children(prop_diff.children)

            # Create main property row
            presentations.append(
                PropertyPresentation(
                    name=prop_diff.property_name,
                    state=prop_diff.state,
                    old_value=old_value,
                    new_value=new_value,
                    children=children,
                    group=group,
                )
            )

            # Handle expression as separate row
            old_expr = getattr(prop_diff.old_value, "expression", None) if prop_diff.old_value else None
            new_expr = getattr(prop_diff.new_value, "expression", None) if prop_diff.new_value else None

            if old_expr or new_expr:
                # Determine expression state using DiffState enum
                if old_expr and not new_expr:
                    expr_state = DiffState.DELETED
                elif not old_expr and new_expr:
                    expr_state = DiffState.ADDED
                elif old_expr == new_expr:
                    expr_state = DiffState.UNCHANGED
                else:
                    expr_state = DiffState.MODIFIED

                presentations.append(
                    PropertyPresentation(
                        name="-> Expression",
                        state=expr_state,
                        old_value=old_expr,
                        new_value=new_expr,
                        group=group,  # Inherit group from parent property
                    )
                )

        return presentations

    def _extract_property_value(self, prop: Property | None) -> Any:
        """Extract the underlying value from a Property object."""
        return prop.value if prop is not None else None

    def _extract_property_group(self, prop: Property | None) -> str | None:
        """Extract the group attribute from a Property object."""
        return getattr(prop, "group", None) if prop is not None else None

    def _transform_children(self, child_diffs: list[PropertyDiff]) -> list[PropertyPresentation]:
        """Recursively transform child property diffs to presentation format.

        Args:
            child_diffs: List of PropertyDiff children from domain

        Returns:
            List of PropertyPresentation for UI display
        """
        return [
            PropertyPresentation(
                name=child_diff.property_name,
                state=child_diff.state,
                old_value=self._extract_property_value(child_diff.old_value),
                new_value=self._extract_property_value(child_diff.new_value),
                children=self._transform_children(child_diff.children),
                # No group for children
            )
            for child_diff in child_diffs
        ]
