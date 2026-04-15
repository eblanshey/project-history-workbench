# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: This module provides the GitRepository and GitCommit models
# representing a git repository and commit respectively, the GitPort protocol
# interface for git repository operations, and the GitService class that
# combines these to provide convenient repository detection. It is part of the
# domain layer and has no external dependencies.
"""Git domain module."""

from .git_service import GitService
from .models import GitCommit, GitRepository
from .ports import GitPort


__all__ = ["GitRepository", "GitCommit", "GitPort", "GitService"]
