# SPDX-License-Identifier: LGPL-3.0-or-later
"""Diff computation module for comparing document snapshots.

Module responsibility: This package provides pure Python algorithms for computing
differences between two document snapshots. It has ZERO FreeCAD dependencies and
uses path-based indexing for efficient O(n+m) comparison performance.

Public API:
    - compute_diff: Main entry point for computing diffs between snapshots (Phase 3)
    - compare_snapshots: Tree comparison with path-based indexing (Phase 1)
"""

# Phase 1: Tree diff algorithm (available now)
from .tree_diff import compare_snapshots, TreeDiffResult

# Phase 3: Diff engine orchestration (will be available later)
# from .diff_engine import compute_diff

__all__ = ["compare_snapshots", "TreeDiffResult"]
