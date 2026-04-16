# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for CreateDocumentSnapshotForCommitAction stub implementation.
# Tests verify that the stub action returns Result with None and accepts the correct parameters.
"""Unit tests for CreateDocumentSnapshotForCommitAction."""

from freecad.diff_wb.application.actions.create_document_snapshot_commit import (
    CreateDocumentSnapshotForCommitAction,
)
from freecad.diff_wb.domain.git.git_service import GitService
from freecad.diff_wb.domain.git.models import GitRepository
from tests.fakes.fake_git_port import FakeGitPort


class TestCreateDocumentSnapshotForCommitActionStub:
    """Tests for the stub implementation of CreateDocumentSnapshotForCommitAction."""

    def test_execute_returns_result_with_none_for_stub(self) -> None:
        """Test that action returns Result with None (for stub implementation)."""
        # Setup
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)
        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = CreateDocumentSnapshotForCommitAction(git_service)

        # Execute
        result = action.execute(repo, "abc123", "src/doc.FCStd")

        # Assert
        assert result.is_success is True
        assert result.data is None
        assert result.message is None

    def test_action_signature_accepts_repo_commit_git_path_parameters(self) -> None:
        """Test that action signature accepts repo, commit, git_path parameters."""
        # Setup
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)
        repo = GitRepository(name="my_project", absolute_path="/home/user/my_project")
        action = CreateDocumentSnapshotForCommitAction(git_service)

        # Execute - verify all parameters are accepted
        result = action.execute(repo=repo, commit="def456", git_path="path/to/file.FCStd")

        # Assert - should return success with None data
        assert result.is_success is True
        assert result.data is None


class TestCreateDocumentSnapshotForCommitActionDependencies:
    """Tests for action dependency injection and initialization."""

    def test_action_accepts_and_stores_git_service_dependency(self) -> None:
        """Test that action can be initialized with and stores GitService dependency."""
        fake_git_port = FakeGitPort()
        git_service = GitService(fake_git_port)

        action = CreateDocumentSnapshotForCommitAction(git_service)

        assert action._git_service is git_service
