# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for creating snapshot from a git commit (STUB).
# This module provides the CreateDocumentSnapshotForCommitAction which is a placeholder
# for creating Snapshots from documents at specific git commits. Currently returns None
# and will be fully implemented in Phase 7.
"""Application action for creating snapshot from a git commit (STUB)."""

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...utils import Log
from .result_models import Result


__all__ = ["CreateDocumentSnapshotForCommitAction"]


class CreateDocumentSnapshotForCommitAction:
    """Create a snapshot from a document at a specific git commit.

    This is a stub implementation that currently returns None. Phase 7 will implement
    the full functionality to extract a document from a git commit by:
    - Checking out the file content at the specified commit
    - Loading it into a temporary FreeCAD document
    - Extracting a Snapshot using the SnapshotExtractor
    """

    def __init__(self, git_service: GitService) -> None:
        """Initialize the action with a GitService.

        Note: GitService is injected but not used in this stub. It will be required
        in Phase 7 for checking out files from git commits.

        Args:
            git_service: GitService instance for git operations (Phase 7).
        """
        self._git_service = git_service

    def execute(self, repo: GitRepository, commit: str | None, git_path: str) -> Result:
        """STUB: Always returns None until Phase 7 implementation.

        Args:
            repo: GitRepository containing the document.
            commit: Git commit hash to extract the document from. None for working tree.
            git_path: Relative path of the document within the repository.

        Returns:
            Result containing None (stub implementation).
        """
        Log.debug(f"CreateDocumentSnapshotForCommitAction stub invoked for {git_path}")
        return Result.success(None)
