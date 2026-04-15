# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the GitPort protocol using a fake
# implementation. These tests verify that the protocol contract works correctly
# with both successful cases (finding git roots) and failing cases (no git repo).
"""Unit tests for the GitPort protocol."""

from typing import Protocol

from freecad.diff_wb.domain.git import GitCommit, GitPort, GitRepository


class FakeGitPort:
    """Fake implementation of GitPort for testing purposes.

    This fake implementation simulates git repository detection without
    requiring actual git repositories or subprocess calls. It uses an
    in-memory mapping of paths to their git roots.
    """

    def __init__(self) -> None:
        """Initialize the fake git port with empty mappings."""
        # Maps paths to their git root paths
        self._git_roots: dict[str, str] = {}
        # Maps git root paths to lists of commits
        self._commits: dict[str, list[GitCommit]] = {}

    def add_git_repo(self, root_path: str) -> None:
        """Add a simulated git repository root.

        Args:
            root_path: The absolute path to the git repository root.
        """
        self._git_roots[root_path] = root_path
        # Initialize empty commit list for this repo
        self._commits[root_path] = []

    def add_commit(
        self,
        root_path: str,
        commit_id: str,
        message: str,
        author: str,
        timestamp: str,
    ) -> None:
        """Add a simulated commit to a repository.

        Commits are added in order (oldest first). The get_commits method
        will return them in DESC order (newest first).

        Args:
            root_path: The absolute path to the git repository root.
            commit_id: The commit hash.
            message: The commit message.
            author: The author name.
            timestamp: ISO format timestamp.
        """
        if root_path not in self._commits:
            self._commits[root_path] = []
        commit = GitCommit(
            id=commit_id,
            message=message,
            author=author,
            timestamp=timestamp,
        )
        self._commits[root_path].append(commit)

    def get_commits(self, path: str, limit: int = 20) -> list[GitCommit]:
        """Get recent commits from the fake git repository.

        This implementation returns the configured commits in DESC order
        (newest first), limited by the specified limit parameter.

        Args:
            path: Starting path (file or directory) to check.
            limit: Maximum number of commits to return (default 20).

        Returns:
            List of GitCommit objects in DESC order (newest first).
        """
        # Find the git root for this path
        git_root = self.find_top_level_git_path(path)

        if git_root is None or git_root not in self._commits:
            return []

        # Get all commits for this repository
        all_commits = self._commits[git_root]

        # Return in DESC order (newest first) - reverse the list
        # and apply the limit
        reversed_commits = list(reversed(all_commits))
        return reversed_commits[:limit]

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


class TestGitPortProtocol:
    """Tests for the GitPort protocol using the fake implementation."""

    def test_protocol_definition_exists(self):
        """Test that GitPort Protocol is properly defined."""
        assert isinstance(GitPort, type(Protocol))

    def test_fake_port_implements_protocol(self):
        """Test that FakeGitPort implements the GitPort protocol."""
        fake_port = FakeGitPort()

        # Verify the method exists and is callable
        assert hasattr(fake_port, "find_top_level_git_path")
        assert callable(fake_port.find_top_level_git_path)

    def test_find_top_level_git_path_returns_none_for_nonexistent_repo(self):
        """Test that find_top_level_git_path returns None when no git repo exists."""
        fake_port = FakeGitPort()

        result = fake_port.find_top_level_git_path("/some/random/path")

        assert result is None

    def test_find_top_level_git_path_returns_root_when_path_is_git_root(self):
        """Test that find_top_level_git_path returns the root when path IS the git root."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        result = fake_port.find_top_level_git_path("/home/user/my_project")

        assert result == "/home/user/my_project"

    def test_find_top_level_git_path_returns_root_for_subdirectory(self):
        """Test that find_top_level_git_path returns root when path is a subdirectory."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        result = fake_port.find_top_level_git_path("/home/user/my_project/src")

        assert result == "/home/user/my_project"

    def test_find_top_level_git_path_returns_root_for_nested_subdirectory(self):
        """Test that find_top_level_git_path works with deeply nested paths."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        result = fake_port.find_top_level_git_path("/home/user/my_project/src/module/submodule")

        assert result == "/home/user/my_project"

    def test_find_top_level_git_path_returns_root_for_file_in_repo(self):
        """Test that find_top_level_git_path works for files within the repo."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        result = fake_port.find_top_level_git_path("/home/user/my_project/src/main.py")

        assert result == "/home/user/my_project"

    def test_find_top_level_git_path_with_trailing_slash(self):
        """Test that find_top_level_git_path handles trailing slashes correctly."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        result = fake_port.find_top_level_git_path("/home/user/my_project/")

        assert result == "/home/user/my_project"

    def test_find_top_level_git_path_with_multiple_repos(self):
        """Test behavior when multiple git repos are configured."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project_a")
        fake_port.add_git_repo("/home/user/project_b")

        result_a = fake_port.find_top_level_git_path("/home/user/project_a/src")
        result_b = fake_port.find_top_level_git_path("/home/user/project_b/src")

        assert result_a == "/home/user/project_a"
        assert result_b == "/home/user/project_b"

    def test_find_top_level_git_path_nearest_repo_wins(self):
        """Test that the nearest git root is found when nested repos exist."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user")
        fake_port.add_git_repo("/home/user/my_project")

        # Should find the more specific (nested) repo first
        result = fake_port.find_top_level_git_path("/home/user/my_project/src")

        assert result == "/home/user/my_project"


class TestGitPortIntegrationWithGitRepository:
    """Tests for GitPort protocol integration with GitRepository model."""

    def test_can_create_repository_from_port_result(self):
        """Test that GitRepository can be created from GitPort results."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        git_root = fake_port.find_top_level_git_path("/home/user/my_project/src")

        if git_root is not None:
            # Extract name from path
            name = git_root.split("/")[-1]
            repo = GitRepository(name=name, absolute_path=git_root)

            assert repo.name == "my_project"
            assert repo.absolute_path == "/home/user/my_project"

    def test_none_result_handled_gracefully(self):
        """Test that None results from GitPort are handled gracefully."""
        fake_port = FakeGitPort()

        git_root = fake_port.find_top_level_git_path("/nonexistent/path")

        # Should be able to check for None without errors
        if git_root is None:
            pass  # Expected behavior - no exception raised

    def test_workflow_detect_repository(self):
        """Test the complete workflow of detecting a repository using GitPort."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/workbench_project")

        def get_repository(path: str) -> GitRepository | None:
            """Helper function to get a GitRepository from a path."""
            git_root = fake_port.find_top_level_git_path(path)
            if git_root is None:
                return None
            name = git_root.split("/")[-1]
            return GitRepository(name=name, absolute_path=git_root)

        # Test with path inside repo
        repo = get_repository("/home/user/workbench_project/freecad/diff_wb")
        assert repo is not None
        assert repo.name == "workbench_project"
        assert repo.absolute_path == "/home/user/workbench_project"

        # Test with path outside any repo
        repo = get_repository("/tmp/unsaved_file")
        assert repo is None


class TestGitPortEdgeCases:
    """Tests for edge cases in GitPort protocol implementation."""

    def test_empty_path(self):
        """Test handling of empty path."""
        fake_port = FakeGitPort()

        result = fake_port.find_top_level_git_path("")

        # Should return None for empty path
        assert result is None

    def test_root_directory(self):
        """Test handling of root directory."""
        fake_port = FakeGitPort()

        result = fake_port.find_top_level_git_path("/")

        # Should return None unless root is explicitly added as a git repo
        assert result is None

    def test_single_character_path(self):
        """Test handling of single character path."""
        fake_port = FakeGitPort()

        result = fake_port.find_top_level_git_path("a")

        assert result is None

    def test_path_with_special_characters(self):
        """Test handling of paths with special characters."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my-project_v2.0")

        result = fake_port.find_top_level_git_path("/home/user/my-project_v2.0/src/file-name.py")

        assert result == "/home/user/my-project_v2.0"

    def test_relative_path_handling(self):
        """Test handling of relative paths (should work but may not find repo)."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        # Relative paths won't match absolute git roots
        result = fake_port.find_top_level_git_path("src/main.py")

        # This should return None since relative path doesn't match absolute root
        assert result is None

    def test_symlink_like_paths(self):
        """Test handling of paths that look like symlinks.

        Note: This fake implementation doesn't normalize paths with '..'.
        Real implementation should use os.path.normpath or os.path.realpath.
        """
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project")

        result = fake_port.find_top_level_git_path("/home/user/project/../project/src")

        # Current behavior: traverses up and finds /home/user/project
        # This is acceptable for a simple fake - real impl should normalize paths
        assert result == "/home/user/project"


class TestGitPortGetCommits:
    """Tests for the get_commits method of GitPort protocol."""

    def test_fake_port_implements_get_commits_method(self):
        """Test that FakeGitPort implements the get_commits method."""
        fake_port = FakeGitPort()

        # Verify the method exists and is callable
        assert hasattr(fake_port, "get_commits")
        assert callable(fake_port.get_commits)

    def test_get_commits_returns_empty_list_when_no_commits_configured(self):
        """Test that get_commits returns an empty list when no commits are configured."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        result = fake_port.get_commits("/home/user/my_project")

        assert result == []
        assert isinstance(result, list)

    def test_get_commits_returns_single_commit(self):
        """Test that get_commits returns a single commit when one is configured."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="abc123def456",
            message="Initial commit",
            author="John Doe",
            timestamp="2024-01-15T10:30:00Z",
        )

        result = fake_port.get_commits("/home/user/my_project")

        assert len(result) == 1
        assert result[0].id == "abc123def456"
        assert result[0].message == "Initial commit"
        assert result[0].author == "John Doe"
        assert result[0].timestamp == "2024-01-15T10:30:00Z"

    def test_get_commits_returns_multiple_commits(self):
        """Test that get_commits returns multiple commits when configured."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="commit1",
            message="First commit",
            author="Alice",
            timestamp="2024-01-01T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="commit2",
            message="Second commit",
            author="Bob",
            timestamp="2024-01-02T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="commit3",
            message="Third commit",
            author="Charlie",
            timestamp="2024-01-03T00:00:00Z",
        )

        result = fake_port.get_commits("/home/user/my_project")

        assert len(result) == 3
        # Commits should be in DESC order (newest first)
        assert result[0].id == "commit3"
        assert result[1].id == "commit2"
        assert result[2].id == "commit1"

    def test_get_commits_limit_parameter_works_correctly(self):
        """Test that the limit parameter correctly limits the number of commits returned."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        # Add 10 commits
        for i in range(10):
            fake_port.add_commit(
                root_path="/home/user/my_project",
                commit_id=f"commit{i}",
                message=f"Commit {i}",
                author=f"Author {i}",
                timestamp=f"2024-01-{i + 1:02d}T00:00:00Z",
            )

        # Test with limit=5
        result = fake_port.get_commits("/home/user/my_project", limit=5)
        assert len(result) == 5

        # Test with default limit (20) - should return all 10
        result_default = fake_port.get_commits("/home/user/my_project")
        assert len(result_default) == 10

        # Test with limit=0 - should return empty list
        result_zero = fake_port.get_commits("/home/user/my_project", limit=0)
        assert result_zero == []

    def test_get_commits_returns_commits_in_desc_order_newest_first(self):
        """Test that get_commits returns commits in DESC order (newest first)."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="oldest",
            message="Oldest commit",
            author="Old Author",
            timestamp="2024-01-01T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="middle",
            message="Middle commit",
            author="Middle Author",
            timestamp="2024-01-02T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="newest",
            message="Newest commit",
            author="New Author",
            timestamp="2024-01-03T00:00:00Z",
        )

        result = fake_port.get_commits("/home/user/my_project")

        # Should be in reverse order (newest first)
        assert len(result) == 3
        assert result[0].id == "newest"
        assert result[1].id == "middle"
        assert result[2].id == "oldest"

    def test_get_commits_commit_properties_are_accessible(self):
        """Test that all GitCommit properties are accessible from returned commits."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="test-commit-hash-12345",
            message="Test commit message\n\nThis is the commit body.",
            author="Test Author <test@example.com>",
            timestamp="2024-06-15T14:30:45Z",
        )

        result = fake_port.get_commits("/home/user/my_project")

        assert len(result) == 1
        commit = result[0]

        # Verify all properties are accessible
        assert commit.id == "test-commit-hash-12345"
        assert commit.message == "Test commit message\n\nThis is the commit body."
        assert commit.author == "Test Author <test@example.com>"
        assert commit.timestamp == "2024-06-15T14:30:45Z"

    def test_get_commits_returns_empty_list_for_nonexistent_repo(self):
        """Test that get_commits returns empty list for paths outside any git repo."""
        fake_port = FakeGitPort()

        result = fake_port.get_commits("/nonexistent/path")

        assert result == []

    def test_get_commits_works_with_subdirectory_paths(self):
        """Test that get_commits works when called with subdirectory paths."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="abc123",
            message="Test commit",
            author="Test Author",
            timestamp="2024-01-01T00:00:00Z",
        )

        # Call with subdirectory path
        result = fake_port.get_commits("/home/user/my_project/src/module")

        assert len(result) == 1
        assert result[0].id == "abc123"


class TestGitPortGetCommitsMultipleRepos:
    """Tests for get_commits with multiple git repositories."""

    def test_get_commits_separates_commits_by_repository(self):
        """Test that get_commits correctly separates commits by repository."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project_a")
        fake_port.add_git_repo("/home/user/project_b")

        fake_port.add_commit(
            root_path="/home/user/project_a",
            commit_id="commit_a1",
            message="Project A commit 1",
            author="Author A",
            timestamp="2024-01-01T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/project_b",
            commit_id="commit_b1",
            message="Project B commit 1",
            author="Author B",
            timestamp="2024-01-02T00:00:00Z",
        )

        result_a = fake_port.get_commits("/home/user/project_a")
        result_b = fake_port.get_commits("/home/user/project_b")

        assert len(result_a) == 1
        assert result_a[0].id == "commit_a1"
        assert len(result_b) == 1
        assert result_b[0].id == "commit_b1"
