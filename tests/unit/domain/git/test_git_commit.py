# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the GitCommit model including creation,
# property access, immutability verification, and string representation.
"""Unit tests for the GitCommit model."""

import dataclasses
from datetime import datetime

from freecad.diff_wb.domain.git import GitCommit


class TestGitCommit:
    """Tests for the GitCommit dataclass."""

    def test_creation_with_valid_values(self) -> None:
        """Test GitCommit creation with valid id, message, author, and timestamp."""
        commit = GitCommit(
            id="abc123def456",
            message="Add new feature\n\nThis implements the new feature.",
            author="John Doe",
            timestamp=datetime.fromisoformat("2024-01-15T10:30:00"),
        )

        assert commit.id == "abc123def456"
        assert commit.message == "Add new feature\n\nThis implements the new feature."
        assert commit.author == "John Doe"
        assert commit.timestamp == datetime.fromisoformat("2024-01-15T10:30:00")

    def test_creation_with_simple_message(self) -> None:
        """Test GitCommit creation with a simple single-line message."""
        commit = GitCommit(
            id="def789ghi012",
            message="Fix bug",
            author="Jane Smith",
            timestamp=datetime.fromisoformat("2024-01-16T14:45:00"),
        )

        assert commit.id == "def789ghi012"
        assert commit.message == "Fix bug"
        assert commit.author == "Jane Smith"
        assert commit.timestamp == datetime.fromisoformat("2024-01-16T14:45:00")

    def test_creation_with_full_commit_message(self) -> None:
        """Test GitCommit creation with subject and body in message."""
        commit = GitCommit(
            id="jkl345mno678",
            message="Refactor authentication module\n\n- Split into smaller classes\n- Add unit tests\n- Improve error handling",
            author="Dev Team <dev@example.com>",
            timestamp=datetime.fromisoformat("2024-01-17T09:00:00+00:00"),
        )

        assert commit.id == "jkl345mno678"
        assert "Refactor authentication module" in commit.message
        assert "Split into smaller classes" in commit.message
        assert commit.author == "Dev Team <dev@example.com>"

    def test_frozen_dataclass_immutability(self) -> None:
        """Test that GitCommit is frozen (immutable)."""
        commit = GitCommit(
            id="pqr901stu234",
            message="Initial commit",
            author="Author Name",
            timestamp=datetime.fromisoformat("2024-01-18T12:00:00"),
        )

        # Attempting to modify should raise an error
        try:
            commit.id = "new_id"
            raise AssertionError("Expected FrozenInstanceError")
        except dataclasses.FrozenInstanceError:
            pass  # Expected behavior

        try:
            commit.message = "New message"
            raise AssertionError("Expected FrozenInstanceError")
        except dataclasses.FrozenInstanceError:
            pass  # Expected behavior

    def test_hash_functionality(self) -> None:
        """Test that GitCommit instances are hashable."""
        commit1 = GitCommit(
            id="vwx567yz890",
            message="Commit one",
            author="Author One",
            timestamp=datetime.fromisoformat("2024-01-19T10:00:00"),
        )
        commit2 = GitCommit(
            id="abc123def456",
            message="Commit two",
            author="Author Two",
            timestamp=datetime.fromisoformat("2024-01-20T11:00:00"),
        )

        # Should be able to use in sets and as dict keys
        commit_set = {commit1, commit2}
        assert len(commit_set) == 2

        commit_dict = {commit1: "value1"}
        assert commit_dict[commit1] == "value1"

    def test_equality_same_values(self) -> None:
        """Test equality of GitCommit instances with same values."""
        commit1 = GitCommit(
            id="same_id",
            message="Same message",
            author="Same Author",
            timestamp=datetime.fromisoformat("2024-01-21T10:00:00"),
        )
        commit2 = GitCommit(
            id="same_id",
            message="Same message",
            author="Same Author",
            timestamp=datetime.fromisoformat("2024-01-21T10:00:00"),
        )

        assert commit1 == commit2
        assert hash(commit1) == hash(commit2)

    def test_inequality_different_ids(self) -> None:
        """Test inequality when ids differ."""
        commit1 = GitCommit(
            id="id_a",
            message="Same message",
            author="Same Author",
            timestamp=datetime.fromisoformat("2024-01-22T10:00:00"),
        )
        commit2 = GitCommit(
            id="id_b",
            message="Same message",
            author="Same Author",
            timestamp=datetime.fromisoformat("2024-01-22T10:00:00"),
        )

        assert commit1 != commit2

    def test_inequality_different_messages(self) -> None:
        """Test inequality when messages differ."""
        commit1 = GitCommit(
            id="same_id",
            message="Message A",
            author="Same Author",
            timestamp=datetime.fromisoformat("2024-01-23T10:00:00"),
        )
        commit2 = GitCommit(
            id="same_id",
            message="Message B",
            author="Same Author",
            timestamp=datetime.fromisoformat("2024-01-23T10:00:00"),
        )

        assert commit1 != commit2

    def test_inequality_different_authors(self) -> None:
        """Test inequality when authors differ."""
        commit1 = GitCommit(
            id="same_id",
            message="Same message",
            author="Author A",
            timestamp=datetime.fromisoformat("2024-01-24T10:00:00"),
        )
        commit2 = GitCommit(
            id="same_id",
            message="Same message",
            author="Author B",
            timestamp=datetime.fromisoformat("2024-01-24T10:00:00"),
        )

        assert commit1 != commit2

    def test_inequality_different_timestamps(self) -> None:
        """Test inequality when timestamps differ."""
        commit1 = GitCommit(
            id="same_id",
            message="Same message",
            author="Same Author",
            timestamp=datetime.fromisoformat("2024-01-25T10:00:00"),
        )
        commit2 = GitCommit(
            id="same_id",
            message="Same message",
            author="Same Author",
            timestamp=datetime.fromisoformat("2024-01-25T11:00:00"),
        )

        assert commit1 != commit2

    def test_string_representation(self) -> None:
        """Test the string representation of GitCommit."""
        commit = GitCommit(
            id="abc123",
            message="Add feature",
            author="John Doe",
            timestamp=datetime.fromisoformat("2024-01-26T10:00:00"),
        )

        expected = "abc123 | John Doe | 2024-01-26T10:00:00 | Add feature"
        assert str(commit) == expected

    def test_string_representation_with_multiline_message(self) -> None:
        """Test string representation with multiline message (truncated)."""
        commit = GitCommit(
            id="def456",
            message="Fix critical bug\n\nDetailed explanation of the fix...",
            author="Jane Smith",
            timestamp=datetime.fromisoformat("2024-01-27T14:30:00"),
        )

        repr_str = str(commit)
        assert "def456" in repr_str
        assert "Jane Smith" in repr_str
        assert "2024-01-27T14:30:00" in repr_str
        assert "Fix critical bug" in repr_str

    def test_repr_output(self) -> None:
        """Test that repr output contains key information."""
        commit = GitCommit(
            id="ghi789",
            message="Update docs",
            author="Doc Writer",
            timestamp=datetime.fromisoformat("2024-01-28T09:15:00"),
        )

        repr_str = repr(commit)
        assert "ghi789" in repr_str
        assert "Doc Writer" in repr_str
        assert "Update docs" in repr_str

    def test_with_empty_message(self) -> None:
        """Test GitCommit creation with empty message (edge case)."""
        commit = GitCommit(
            id="jkl012", message="", author="Author Name", timestamp=datetime.fromisoformat("2024-01-29T12:00:00")
        )

        assert commit.id == "jkl012"
        assert commit.message == ""
        assert commit.author == "Author Name"

    def test_with_empty_author(self) -> None:
        """Test GitCommit creation with empty author (edge case)."""
        commit = GitCommit(
            id="mno345", message="Some message", author="", timestamp=datetime.fromisoformat("2024-01-30T15:45:00")
        )

        assert commit.id == "mno345"
        assert commit.message == "Some message"
        assert commit.author == ""

    def test_property_access_id(self) -> None:
        """Test direct property access for id."""
        commit = GitCommit(
            id="test_commit_hash",
            message="Test commit",
            author="Test Author",
            timestamp=datetime.fromisoformat("2024-02-01T10:00:00"),
        )

        assert commit.id == "test_commit_hash"

    def test_property_access_message(self) -> None:
        """Test direct property access for message."""
        commit = GitCommit(
            id="abc",
            message="Full commit message here",
            author="Author",
            timestamp=datetime.fromisoformat("2024-02-02T11:00:00"),
        )

        assert commit.message == "Full commit message here"

    def test_property_access_author(self) -> None:
        """Test direct property access for author."""
        commit = GitCommit(
            id="def",
            message="Message",
            author="Test User <test@example.com>",
            timestamp=datetime.fromisoformat("2024-02-03T12:00:00"),
        )

        assert commit.author == "Test User <test@example.com>"

    def test_property_access_timestamp(self) -> None:
        """Test direct property access for timestamp."""
        commit = GitCommit(
            id="ghi", message="Message", author="Author", timestamp=datetime.fromisoformat("2024-02-04T13:00:00+00:00")
        )

        assert commit.timestamp == datetime.fromisoformat("2024-02-04T13:00:00+00:00")
