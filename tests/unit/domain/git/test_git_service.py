# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the GitService class using fake GitPort
# implementations. These tests verify that GitService correctly creates
# GitRepository objects from paths and handles edge cases properly.
"""Unit tests for the GitService class."""

import dataclasses
import os

from freecad.diff_wb.domain.git import GitRepository, GitService
from tests.unit.domain.git.test_git_port import FakeGitPort


class TestGitServiceInitialization:
    """Tests for GitService initialization and dependency injection."""

    def test_initialization_with_git_port(self):
        """Test that GitService can be initialized with a GitPort."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert service is not None

    def test_git_port_is_stored(self):
        """Test that the GitPort is stored in the service."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert service._git_port == fake_port


class TestGitServiceGetRepository:
    """Tests for GitService.get_repository() method."""

    def test_get_repository_returns_none_for_nonexistent_repo(self):
        """Test that get_repository returns None when path is not in a git repo."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("/some/random/path")

        assert result is None

    def test_get_repository_returns_repository_when_path_is_git_root(self):
        """Test that get_repository returns GitRepository when path IS the git root."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_returns_repository_for_subdirectory(self):
        """Test that get_repository returns GitRepository when path is a subdirectory."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/src")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_returns_repository_for_nested_subdirectory(self):
        """Test that get_repository works with deeply nested paths."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/src/module/submodule")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_returns_repository_for_file_in_repo(self):
        """Test that get_repository works for files within the repo."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/src/main.py")

        assert result is not None
        assert isinstance(result, GitRepository)
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_handles_trailing_slash(self):
        """Test that get_repository handles trailing slashes correctly."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my_project/")

        assert result is not None
        assert result.name == "my_project"
        assert result.absolute_path == "/home/user/my_project"

    def test_get_repository_with_multiple_repos(self):
        """Test behavior when multiple git repos are configured."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project_a")
        fake_port.add_git_repo("/home/user/project_b")
        service = GitService(git_port=fake_port)

        result_a = service.get_repository("/home/user/project_a/src")
        result_b = service.get_repository("/home/user/project_b/src")

        assert result_a is not None
        assert result_b is not None
        assert result_a.name == "project_a"
        assert result_a.absolute_path == "/home/user/project_a"
        assert result_b.name == "project_b"
        assert result_b.absolute_path == "/home/user/project_b"


class TestGitServiceGetRepositoryEdgeCases:
    """Tests for edge cases in GitService.get_repository()."""

    def test_get_repository_with_empty_path(self):
        """Test handling of empty path."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("")

        assert result is None

    def test_get_repository_with_root_directory(self):
        """Test handling of root directory."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("/")

        assert result is None

    def test_get_repository_with_single_character_path(self):
        """Test handling of single character path."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        result = service.get_repository("a")

        assert result is None

    def test_get_repository_with_special_characters_in_name(self):
        """Test handling of repository names with special characters."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my-project_v2.0")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/my-project_v2.0/src/file-name.py")

        assert result is not None
        assert result.name == "my-project_v2.0"
        assert result.absolute_path == "/home/user/my-project_v2.0"

    def test_get_repository_with_relative_path(self):
        """Test handling of relative paths (should return None)."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        result = service.get_repository("src/main.py")

        # Relative paths won't match absolute git roots
        assert result is None


class TestGitServiceGetRepositoryIntegration:
    """Integration tests for GitService with realistic scenarios."""

    def test_workflow_detect_active_repository(self):
        """Test the complete workflow of detecting an active repository."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/workbench_project")
        service = GitService(git_port=fake_port)

        # Simulate checking a FreeCAD document path
        doc_path = "/home/user/workbench_project/freecad/diff_wb/document.FCStd"
        repo = service.get_repository(doc_path)

        assert repo is not None
        assert repo.name == "workbench_project"
        assert repo.absolute_path == "/home/user/workbench_project"

    def test_workflow_no_repository_for_unsaved_document(self):
        """Test workflow when document is not in a git repo."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        # Simulate checking an unsaved or temporary document
        doc_path = "/tmp/unsaved_file.FCStd"
        repo = service.get_repository(doc_path)

        assert repo is None

    def test_get_repository_returns_frozen_dataclass(self):
        """Test that returned GitRepository is immutable (frozen)."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/project/src")

        assert repo is not None
        # Try to modify - should raise FrozenInstanceError
        try:
            repo.name = "modified"  # type: ignore
            raise AssertionError("Expected FrozenInstanceError")
        except dataclasses.FrozenInstanceError:
            pass  # Expected behavior


class TestGitServiceWithRealPathOperations:
    """Tests that verify GitService correctly uses os.path operations."""

    def test_get_repository_uses_os_path_basename(self):
        """Test that service correctly extracts name using os.path.basename."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/test-repo")
        service = GitService(git_port=fake_port)

        result = service.get_repository("/home/user/test-repo")

        # Verify the name matches what os.path.basename would return
        expected_name = os.path.basename("/home/user/test-repo")
        assert result is not None
        assert result.name == expected_name

    def test_get_repository_preserves_absolute_path(self):
        """Test that service preserves the absolute path as-is."""
        fake_port = FakeGitPort()
        test_path = "/absolute/path/to/repository"
        fake_port.add_git_repo(test_path)
        service = GitService(git_port=fake_port)

        result = service.get_repository(test_path + "/subdir")

        assert result is not None
        assert result.absolute_path == test_path


class TestGitServiceGetCommitsInitialization:
    """Tests for GitService.get_commits() initialization."""

    def test_get_commits_method_exists(self):
        """Test that get_commits method exists on GitService."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        assert hasattr(service, "get_commits")
        assert callable(service.get_commits)

    def test_get_commits_method_signature(self):
        """Test that get_commits has correct signature with limit parameter."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        # Verify the method accepts repo and limit parameters
        import inspect

        sig = inspect.signature(service.get_commits)
        params = list(sig.parameters.keys())

        assert "repo" in params
        assert "limit" in params


class TestGitServiceGetCommitsWithEmptyCommits:
    """Tests for GitService.get_commits() with empty commit lists."""

    def test_get_commits_returns_empty_list_when_no_commits(self):
        """Test that get_commits returns empty list when repo has no commits."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        assert result == []
        assert isinstance(result, list)

    def test_get_commits_returns_empty_list_for_nonexistent_repo(self):
        """Test that get_commits returns empty list for non-existent repository."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        # Create a repo object for a path that doesn't exist in fake port
        repo = GitRepository(name="nonexistent", absolute_path="/nonexistent/path")

        result = service.get_commits(repo=repo)

        assert result == []


class TestGitServiceGetCommitsWithSingleCommit:
    """Tests for GitService.get_commits() with a single commit."""

    def test_get_commits_returns_single_commit(self):
        """Test that get_commits returns one commit when only one exists."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="abc123def456",
            message="Initial commit",
            author="John Doe",
            timestamp="2024-01-15T10:30:00Z",
        )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        assert len(result) == 1
        assert result[0].id == "abc123def456"
        assert result[0].message == "Initial commit"
        assert result[0].author == "John Doe"
        assert result[0].timestamp == "2024-01-15T10:30:00Z"


class TestGitServiceGetCommitsWithMultipleCommits:
    """Tests for GitService.get_commits() with multiple commits."""

    def test_get_commits_returns_all_commits(self):
        """Test that get_commits returns all commits when limit is high enough."""
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
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        assert len(result) == 3

    def test_get_commits_returns_all_commit_properties(self):
        """Test that all commit properties are accessible from returned commits."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="test-commit-hash-12345",
            message="Test commit message\n\nThis is the commit body.",
            author="Test Author <test@example.com>",
            timestamp="2024-06-15T14:30:45Z",
        )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        assert len(result) == 1
        commit = result[0]

        assert commit.id == "test-commit-hash-12345"
        assert commit.message == "Test commit message\n\nThis is the commit body."
        assert commit.author == "Test Author <test@example.com>"
        assert commit.timestamp == "2024-06-15T14:30:45Z"


class TestGitServiceGetCommitsLimitParameter:
    """Tests for GitService.get_commits() limit parameter."""

    def test_get_commits_respects_limit_parameter(self):
        """Test that get_commits respects the limit parameter."""
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
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        # Test with limit=5
        result = service.get_commits(repo=repo, limit=5)
        assert len(result) == 5

        # Test with default limit (20) - should return all 10
        result_default = service.get_commits(repo=repo)
        assert len(result_default) == 10

        # Test with limit=0 - should return empty list
        result_zero = service.get_commits(repo=repo, limit=0)
        assert result_zero == []

    def test_get_commits_default_limit_is_20(self):
        """Test that the default limit is 20 commits."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        # Add 25 commits
        for i in range(25):
            fake_port.add_commit(
                root_path="/home/user/my_project",
                commit_id=f"commit{i}",
                message=f"Commit {i}",
                author=f"Author {i}",
                timestamp=f"2024-01-{i + 1:02d}T00:00:00Z",
            )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        # Default limit should be 20
        result = service.get_commits(repo=repo)
        assert len(result) == 20


class TestGitServiceGetCommitsDESCOrder:
    """Tests for GitService.get_commits() DESC order."""

    def test_get_commits_returns_commits_in_desc_order(self):
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
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        result = service.get_commits(repo=repo)

        # Should be in reverse order (newest first)
        assert len(result) == 3
        assert result[0].id == "newest"
        assert result[1].id == "middle"
        assert result[2].id == "oldest"

    def test_get_commits_limit_applied_after_reversing(self):
        """Test that limit is applied after reversing for DESC order."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/my_project")

        # Add commits in chronological order
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="first",
            message="First",
            author="Author",
            timestamp="2024-01-01T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="second",
            message="Second",
            author="Author",
            timestamp="2024-01-02T00:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/my_project",
            commit_id="third",
            message="Third",
            author="Author",
            timestamp="2024-01-03T00:00:00Z",
        )
        service = GitService(git_port=fake_port)

        repo = service.get_repository("/home/user/my_project")
        assert repo is not None

        # With limit=2, should get newest 2 (third and second)
        result = service.get_commits(repo=repo, limit=2)

        assert len(result) == 2
        assert result[0].id == "third"
        assert result[1].id == "second"


class TestGitServiceGetCommitsIntegration:
    """Integration tests for GitService.get_commits()."""

    def test_workflow_get_commits_for_realistic_scenario(self):
        """Test complete workflow of getting commits for a project."""
        fake_port = FakeGitPort()
        fake_port.add_git_repo("/home/user/freecad_workbench")

        # Simulate realistic commit history - add in chronological order (oldest first)
        # Commits will be returned in DESC order (newest first)
        fake_port.add_commit(
            root_path="/home/user/freecad_workbench",
            commit_id="c3d4e5f6a1b2",
            message="docs: update README with installation instructions",
            author="Developer One",
            timestamp="2024-06-13T09:00:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/freecad_workbench",
            commit_id="b2c3d4e5f6a1",
            message="fix: resolve merge conflict in utils.py",
            author="Developer Two",
            timestamp="2024-06-14T15:30:00Z",
        )
        fake_port.add_commit(
            root_path="/home/user/freecad_workbench",
            commit_id="a1b2c3d4e5f6",
            message="feat: add diff comparison feature",
            author="Developer One",
            timestamp="2024-06-15T10:00:00Z",
        )
        service = GitService(git_port=fake_port)

        # Get repository from a file path within the project
        doc_path = "/home/user/freecad_workbench/freecad/diff_wb/document.FCStd"
        repo = service.get_repository(doc_path)
        assert repo is not None

        # Get recent commits
        commits = service.get_commits(repo=repo, limit=3)

        assert len(commits) == 3
        # Most recent commit should be first (DESC order)
        assert "diff comparison feature" in commits[0].message
        assert commits[0].author == "Developer One"
