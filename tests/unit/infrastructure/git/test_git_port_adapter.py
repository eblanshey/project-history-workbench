# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains unit tests for the GitPortAdapter class.
# Tests use subprocess mocking to verify git repository detection without actual
# git commands, ensuring reliable and fast test execution.
"""Unit tests for GitPortAdapter."""

import os
import subprocess
import unittest.mock
from unittest.mock import patch

import pytest

from freecad.diff_wb.infrastructure.git import GitPortAdapter


class TestGitPortAdapter:
    """Tests for the GitPortAdapter class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()

    @pytest.mark.parametrize(
        "path",
        [
            "/home/user/project",
            "/tmp/test_repo",
            "./relative/path",
            "/absolute/path/to/repo",
        ],
    )
    def test_find_top_level_path_success(self, path: str) -> None:
        """Test successful git root detection.

        When git rev-parse returns exit code 0, the adapter should return
        the stripped stdout value.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout="/home/user/project\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.find_top_level_git_path(path)

            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Verify the result is the stripped stdout
            assert result == "/home/user/project"

    def test_find_top_level_path_success_with_extra_whitespace(self) -> None:
        """Test that leading/trailing whitespace is properly stripped."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout="  /home/user/project  \n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.find_top_level_git_path("/some/path")

            assert result == "/home/user/project"

    @patch.object(os.path, "dirname", return_value="/parent/directory")
    @patch.object(os.path, "isfile", return_value=True)
    def test_find_top_level_path_with_file_path(
        self, mock_isfile: unittest.mock.Mock, mock_dirname: unittest.mock.Mock
    ) -> None:
        """Test that file paths are handled correctly by using parent directory as cwd.

        When the input path is a file (not a directory), the adapter should:
        1. Detect that the input is a file using os.path.isfile()
        2. Extract the parent directory using os.path.dirname()
        3. Pass the parent directory to subprocess.run() as cwd

        This ensures git commands work correctly when given a file path.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout="/home/user/project\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = self.adapter.find_top_level_git_path("/parent/directory/file.py")

            # Verify os.path.isfile was called with the original path
            mock_isfile.assert_called_once_with("/parent/directory/file.py")

            # Verify os.path.dirname was called with the original path
            mock_dirname.assert_called_once_with("/parent/directory/file.py")

            # Verify subprocess.run was called with parent directory as cwd
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--show-toplevel"],
                cwd="/parent/directory",
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Verify the result is returned correctly
            assert result == "/home/user/project"

    def test_find_top_level_path_not_in_git_repo(self) -> None:
        """Test handling of path not in a git repository.

        When git rev-parse returns non-zero exit code (not in git repo),
        the adapter should return None.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.find_top_level_git_path("/non/git/path")

            assert result is None

    def test_find_top_level_path_timeout(self) -> None:
        """Test handling of subprocess timeout.

        When git command times out, the adapter should return None.
        """
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5)):
            result = self.adapter.find_top_level_git_path("/some/path")

            assert result is None

    def test_find_top_level_path_git_not_found(self) -> None:
        """Test handling of git command not found.

        When git executable is not found, the adapter should return None.
        """
        with patch.object(subprocess, "run", side_effect=FileNotFoundError("git")):
            result = self.adapter.find_top_level_git_path("/some/path")

            assert result is None

    def test_find_top_level_path_empty_stdout_success(self) -> None:
        """Test handling of empty stdout with success exit code.

        Edge case: git returns 0 but empty output (shouldn't happen normally).
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.find_top_level_git_path("/some/path")

            # Empty string stripped is still empty string
            assert result == ""

    @pytest.mark.parametrize(
        "returncode",
        [1, 2, 128],
    )
    def test_find_top_level_path_various_error_codes(self, returncode: int) -> None:
        """Test handling of various non-zero exit codes.

        Any non-zero exit code should result in None being returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=returncode,
            stdout="",
            stderr=f"error {returncode}",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.find_top_level_git_path("/some/path")

            assert result is None


class TestGitPortAdapterProtocol:
    """Tests to verify GitPortAdapter implements GitPort protocol."""

    def test_adapter_implements_gitport_protocol(self) -> None:
        """Test that GitPortAdapter has the required find_top_level_git_path method.

        This verifies the adapter correctly implements the GitPort protocol.
        """
        adapter = GitPortAdapter()

        # Verify the method exists and is callable
        assert hasattr(adapter, "find_top_level_git_path")
        assert callable(adapter.find_top_level_git_path)


class TestGitPortAdapterGetCommits:
    """Tests for the get_commits method of GitPortAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()

    def test_get_commits_success_single_commit(self) -> None:
        """Test successful commit retrieval with a single commit."""
        # Using null byte (\x00) as separator - format: hash\x00message\x00author\x00timestamp\x00
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="abc123def456\x00Initial commit\x00Author Name\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            commits = self.adapter.get_commits("/path/to/repo")

            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_once_with(
                ["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Verify result
            assert len(commits) == 1
            assert commits[0].id == "abc123def456"
            assert commits[0].message == "Initial commit"
            assert commits[0].author == "Author Name"
            assert commits[0].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_parsing_full_message(self) -> None:
        """Test parsing commit with full message (subject + body)."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="abc123def456\x00Fix bug in module\n\nThis is the body of the commit.\nIt has multiple lines.\x00John Doe\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert len(commits) == 1
            assert commits[0].id == "abc123def456"
            assert commits[0].message == "Fix bug in module\n\nThis is the body of the commit.\nIt has multiple lines."
            assert commits[0].author == "John Doe"
            assert commits[0].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_multiple_commits(self) -> None:
        """Test retrieving multiple commits."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash3\x00Third commit\x00Alice\x002024-01-03T10:00:00+00:00\x00hash2\x00Second commit\x00Bob\x002024-01-02T10:00:00+00:00\x00hash1\x00First commit\x00Charlie\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert len(commits) == 3
            assert commits[0].id == "hash3"
            assert commits[0].author == "Alice"
            assert commits[0].timestamp.isoformat() == "2024-01-03T10:00:00+00:00"
            assert commits[1].id == "hash2"
            assert commits[1].author == "Bob"
            assert commits[1].timestamp.isoformat() == "2024-01-02T10:00:00+00:00"
            assert commits[2].id == "hash1"
            assert commits[2].author == "Charlie"
            assert commits[2].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_limit_parameter(self) -> None:
        """Test that limit parameter is passed correctly to git log."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n5", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash1\x00Commit 1\x00Author\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.get_commits("/path/to/repo", limit=5)

            mock_run.assert_called_once_with(
                ["git", "log", "-n5", "--format=%H%x00%B%x00%an%x00%aI%x00"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                timeout=10,
            )

    def test_get_commits_empty_repository(self) -> None:
        """Test handling of empty repository (no commits)."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert commits == []

    def test_get_commits_timeout(self) -> None:
        """Test handling of subprocess timeout."""
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
            commits = self.adapter.get_commits("/path/to/repo")

            assert commits == []

    def test_get_commits_git_not_found(self) -> None:
        """Test handling of git command not found."""
        with patch.object(subprocess, "run", side_effect=FileNotFoundError("git")):
            commits = self.adapter.get_commits("/path/to/repo")

            assert commits == []

    def test_get_commits_non_zero_exit_code(self) -> None:
        """Test handling of non-zero exit code from git."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert commits == []

    @patch.object(os.path, "dirname", return_value="/parent/directory")
    @patch.object(os.path, "isfile", return_value=True)
    def test_get_commits_with_file_path(
        self, mock_isfile: unittest.mock.Mock, mock_dirname: unittest.mock.Mock
    ) -> None:
        """Test that file paths use parent directory as cwd.

        When the input path is a file (not a directory), the adapter should:
        1. Detect that the input is a file using os.path.isfile()
        2. Extract the parent directory using os.path.dirname()
        3. Pass the parent directory to subprocess.run() as cwd
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash1\x00Commit message\x00Author\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.get_commits("/parent/directory/file.py")

            # Verify os.path.isfile was called with the original path
            mock_isfile.assert_called_once_with("/parent/directory/file.py")

            # Verify os.path.dirname was called with the original path
            mock_dirname.assert_called_once_with("/parent/directory/file.py")

            # Verify subprocess.run was called with parent directory as cwd
            mock_run.assert_called_once_with(
                ["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
                cwd="/parent/directory",
                capture_output=True,
                text=True,
                timeout=10,
            )

    def test_get_commits_message_with_pipe_characters(self) -> None:
        """Test parsing commit message containing pipe characters."""
        # Null byte separator handles pipe characters in messages correctly
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="abc123def456\x00Fix: update | value in config\x00John Doe\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert len(commits) == 1
            assert commits[0].id == "abc123def456"
            assert commits[0].message == "Fix: update | value in config"
            assert commits[0].author == "John Doe"
            assert commits[0].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_multiline_message_with_body(self) -> None:
        """Test parsing commit with multiline message including body."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash123\x00Add new feature\n\nThis is a detailed description of the feature.\n\n- Feature 1\n- Feature 2\x00Developer Name\x002024-01-01T12:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            assert len(commits) == 1
            assert commits[0].id == "hash123"
            # Message includes subject and body (before author field)
            assert "Add new feature" in commits[0].message
            assert "This is a detailed description" in commits[0].message
            assert commits[0].author == "Developer Name"
            assert commits[0].timestamp.isoformat() == "2024-01-01T12:00:00+00:00"

    def test_get_commits_desc_order_newest_first(self) -> None:
        """Test that commits are returned in DESC order (newest first)."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="latest_hash\x00Latest commit\x00Author\x002024-01-15T10:00:00+00:00\x00oldest_hash\x00Oldest commit\x00Author\x002024-01-01T10:00:00+00:00\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            # git log returns newest first by default
            assert len(commits) == 2
            assert commits[0].id == "latest_hash"
            assert commits[0].timestamp.isoformat() == "2024-01-15T10:00:00+00:00"
            assert commits[1].id == "oldest_hash"
            assert commits[1].timestamp.isoformat() == "2024-01-01T10:00:00+00:00"

    def test_get_commits_malformed_data_returns_empty_list(self) -> None:
        """Test handling of malformed commit data (incomplete fields)."""
        # Incomplete data - only has hash and message, missing author and timestamp
        mock_result = subprocess.CompletedProcess(
            args=["git", "log", "-n20", "--format=%H%x00%B%x00%an%x00%aI%x00"],
            returncode=0,
            stdout="hash1\x00Commit message\x00",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            commits = self.adapter.get_commits("/path/to/repo")

            # Incomplete data (less than 4 fields per commit) should be skipped
            assert commits == []
