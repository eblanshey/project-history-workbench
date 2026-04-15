# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Fake GitPort implementation for testing git repository detection
# and commit retrieval. This provides an in-memory simulation of git operations
# without requiring actual git repositories or subprocess calls.
"""Fake GitPort implementation for testing."""

from freecad.diff_wb.domain.git.models import GitCommit


class FakeGitPort:
    """Fake implementation of GitPort for testing purposes.

    This fake implementation simulates git repository detection and commit retrieval
    without requiring actual git repositories or subprocess calls. It uses an
    in-memory mapping of paths to their git roots and commits.

    Attributes:
        _git_roots: Dictionary mapping paths to their git root paths.
        _commits: Dictionary mapping repo paths to lists of GitCommit objects.
    """

    def __init__(self) -> None:
        """Initialize the fake git port with empty mappings."""
        self._git_roots: dict[str, str] = {}
        self._commits: dict[str, list[GitCommit]] = {}

    def add_git_repo(self, root_path: str) -> None:
        """Add a simulated git repository root.

        Args:
            root_path: The absolute path to the git repository root.
        """
        self._git_roots[root_path] = root_path
        # Initialize empty commits list for this repo
        if root_path not in self._commits:
            self._commits[root_path] = []

    def set_commits(self, root_path: str, commits: list[GitCommit]) -> None:
        """Set commits for a simulated git repository.

        Args:
            root_path: The absolute path to the git repository root.
            commits: List of GitCommit objects to return for this repo.
        """
        self._commits[root_path] = commits

    def find_top_level_git_path(self, path: str) -> str | None:
        """Find git root by checking if path is within a known git repo.

        This implementation checks if the given path or any of its parent
        directories match a known git root.

        Args:
            path: Starting path (file or directory) to check.

        Returns:
            Absolute path to git root as string if path is in a known git repo,
            or None if not in a known git repo.
        """
        # Normalize the path
        normalized_path = path.rstrip("/")

        # Check if the path itself is a git root
        if normalized_path in self._git_roots:
            return self._git_roots[normalized_path]

        # Traverse up the directory tree to find a git root
        current_path = normalized_path
        while True:
            # Get parent directory
            parent_path = "/".join(current_path.split("/")[:-1])

            # If we've reached the root, stop searching
            if parent_path == "" or parent_path == "/":
                # Check root explicitly
                if "/" in self._git_roots:
                    return self._git_roots["/"]
                break

            # Check if parent is a git root
            if parent_path in self._git_roots:
                return self._git_roots[parent_path]

            current_path = parent_path

        return None

    def get_commits(self, path: str, limit: int = 20) -> list[GitCommit]:
        """Get commits from a simulated git repository.

        This implementation returns pre-configured commits for the given path,
        respecting the specified limit.

        Args:
            path: Absolute path to git repository root.
            limit: Maximum number of commits to return.

        Returns:
            List of GitCommit objects (up to limit).
        """
        # Find the matching git root for the given path
        git_root = self.find_top_level_git_path(path)
        if git_root is None:
            return []

        # Return commits for this repo, limited to the requested count
        commits = self._commits.get(git_root, [])
        return commits[:limit]
