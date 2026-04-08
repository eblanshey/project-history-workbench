# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the DiffEngine class that orchestrates
# diff computation between two snapshots. It coordinates between TreeComparator
# and PropertyComparator, applies filtering based on excluded types and properties,
# and produces a complete DiffResult.
#
# The engine uses dependency injection for SettingsRepository to determine
# configuration at runtime.
"""Diff computation engine."""

from typing import Protocol

from ...config import EXCLUDED_PROPERTIES, EXCLUDED_TYPES
from ..settings import SettingsRepository
from ..snapshots import Snapshot
from ..tree import TreeNode
from .comparator import TreeComparator
from .models import DiffResult


class TreeComparatorProtocol(Protocol):
    """Protocol for TreeComparator to enable dependency injection."""

    def compare_snapshots(
        self,
        old_root_nodes: list[TreeNode],
        new_root_nodes: list[TreeNode],
        excluded_properties: list[str],
        excluded_types: list[str],
    ) -> DiffResult: ...


class DiffEngine:
    """Orchestrates diff computation between two snapshots.

    This class coordinates the tree comparison and property comparison
    processes, applying user-configured filters for excluded types and
    properties.

    The engine uses dependency injection for SettingsRepository and
    TreeComparator, allowing different implementations and easy mocking.

    Attributes:
        _settings_repo: Settings repository for accessing configuration
        _tree_comparator: Tree comparator instance for tree comparison
    """

    def __init__(
        self,
        settings_repo: SettingsRepository | None = None,
        tree_comparator: TreeComparatorProtocol | None = None,
    ) -> None:
        """Initialize the diff engine.

        Args:
            settings_repo: Settings repository for accessing configuration.
                If None, uses default values from config.py.
            tree_comparator: Tree comparator instance. If None, creates
                a default TreeComparator instance.
        """
        self._settings_repo = settings_repo
        self._tree_comparator = tree_comparator or TreeComparator()

    def _get_excluded_node_types(self) -> list[str]:
        """Get list of excluded type IDs.

        Returns:
            List of type IDs to exclude, using settings repo if available
        """
        if self._settings_repo is not None:
            return self._settings_repo.get_excluded_types()
        return EXCLUDED_TYPES

    def _get_excluded_properties(self) -> list[str]:
        """Get list of excluded property names.

        Returns:
            List of property names to exclude, using settings repo if available
        """
        if self._settings_repo is not None:
            return self._settings_repo.get_excluded_properties()
        return EXCLUDED_PROPERTIES

    # Excluded types filtering is handled in TreeComparator during diff building

    def compute_diff(self, old: Snapshot, new: Snapshot) -> DiffResult:
        """Compute diff between two snapshots.

        Steps:
        1. Get settings (excluded types/properties)
        2. Compare trees using TreeComparator (includes type filtering)
        3. Apply property-level exclusions
        4. Return DiffResult

        Args:
            old: The old snapshot to compare
            new: The new snapshot to compare

        Returns:
            DiffResult containing all differences between the snapshots
        """
        # Step 1: Get settings
        excluded_node_types = self._get_excluded_node_types()
        excluded_properties = self._get_excluded_properties()

        # Step 2: Compare trees using TreeComparator (filters excluded types internally)
        return self._tree_comparator.compare_snapshots(old.nodes, new.nodes, excluded_properties, excluded_node_types)

    def compare(
        self,
        old_snapshot: Snapshot,
        new_snapshot: Snapshot,
        excluded_types: list[str],
        excluded_properties: list[str],
    ) -> DiffResult:
        """Compare two snapshot structures directly.

        This method allows comparing Snapshot objects directly. It applies
        filtering based on excluded types and properties, then computes the diff.

        Args:
            old_snapshot: Snapshot from the older version
            new_snapshot: Snapshot from the newer version
            excluded_types: List of type IDs to exclude from comparison
            excluded_properties: List of property names to exclude from comparison

        Returns:
            DiffResult containing all differences between the snapshots
        """
        # compare_snapshots now returns DiffResult with hierarchy and counts
        return self._tree_comparator.compare_snapshots(
            old_snapshot.nodes, new_snapshot.nodes, excluded_properties, excluded_types
        )


__all__ = ["DiffEngine"]
