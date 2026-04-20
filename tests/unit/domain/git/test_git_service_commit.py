# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitService.commit() method. These tests verify
# that GitService correctly delegates commit calls to the GitPort with the correct
# arguments and that return values are properly propagated.
"""Unit tests for the GitService.commit() method."""

from freecad.diff_wb.domain.git import GitRepository, GitService
from tests.fakes.fake_git_port import FakeGitPort


class TestGitServiceCommitDelegation:
    """Tests for GitService.commit() delegation to git_port."""

    def test_commit_delegates_to_git_port_with_correct_arguments(self) -> None:
        """Test that commit delegates to git_port with repo.absolute_path and message."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")
        message = "feat: add new feature"

        result = service.commit(repo=repo, message=message)

        assert result is True
        assert fake_port._last_commit_call == ("/home/user/test_repo", "feat: add new feature")

    def test_commit_passes_repo_absolute_path_to_git_port(self) -> None:
        """Test that the repo's absolute_path is passed correctly to git_port."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        test_path = "/home/user/my_project"
        repo = GitRepository(name="my_project", absolute_path=test_path)

        result = service.commit(repo=repo, message="Initial commit")

        assert result is True
        assert fake_port._last_commit_call == (test_path, "Initial commit")


class TestGitServiceCommitReturnValues:
    """Tests for GitService.commit() return value propagation."""

    def test_commit_returns_true_on_success(self) -> None:
        """Test that commit returns True when git_port succeeds."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.commit(repo=repo, message="commit message")

        assert result is True

    def test_commit_returns_false_on_failure(self) -> None:
        """Test that commit returns False when git_port fails."""
        fake_port = FakeGitPort(fail_commit=True)
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.commit(repo=repo, message="commit message")

        assert result is False

    def test_commit_passes_through_git_port_return_value(self) -> None:
        """Test that the git_port return value is passed through unchanged."""
        # Success case
        fake_port_success = FakeGitPort(fail_commit=False)
        service_success = GitService(git_port=fake_port_success)
        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")
        assert service_success.commit(repo=repo, message="msg") is True

        # Failure case
        fake_port_fail = FakeGitPort(fail_commit=True)
        service_fail = GitService(git_port=fake_port_fail)
        assert service_fail.commit(repo=repo, message="msg") is False


class TestGitServiceCommitWithFakeGitPort:
    """Tests for GitService.commit() using FakeGitPort scenarios."""

    def test_commit_with_realistic_repo_and_message(self) -> None:
        """Test commit with a realistic repository and commit message."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(
            name="freecad_diff_workbench",
            absolute_path="/home/user/freecad_diff_workbench",
        )
        message = "feat: add commit staging feature"

        result = service.commit(repo=repo, message=message)

        assert result is True

    def test_commit_with_empty_message(self) -> None:
        """Test commit with an empty message string."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")

        result = service.commit(repo=repo, message="")

        # GitService itself doesn't validate the message; delegation still happens
        assert result is True

    def test_commit_with_multiline_message(self) -> None:
        """Test commit with a multiline commit message."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")
        message = "feat: add feature\n\nThis is the commit body with details."

        result = service.commit(repo=repo, message=message)

        assert result is True

    def test_commit_with_special_characters_in_message(self) -> None:
        """Test commit with special characters in the commit message."""
        fake_port = FakeGitPort()
        service = GitService(git_port=fake_port)

        repo = GitRepository(name="test_repo", absolute_path="/home/user/test_repo")
        message = "fix: resolve #123 - handle edge case with 'quotes' and \"double quotes\""

        result = service.commit(repo=repo, message=message)

        assert result is True
