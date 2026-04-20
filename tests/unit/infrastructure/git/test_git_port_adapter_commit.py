# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains unit tests for the GitPortAdapter.commit() method.
# Tests use subprocess mocking to verify git commit invocation, error handling,
# and logging behavior without actual git commands.
"""Unit tests for GitPortAdapter.commit()."""

import subprocess
from unittest.mock import patch

import pytest

from freecad.diff_wb.infrastructure.git import GitPortAdapter
from freecad.diff_wb.utils import Log


class TestGitPortAdapterCommit:
    """Tests for the commit method of GitPortAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()

    def test_commit_success(self) -> None:
        """Test successful commit returns True.

        When git commit returns exit code 0, the adapter should return True.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Add feature"],
            returncode=0,
            stdout=" 1 file changed, 10 insertions(+)\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.commit("/path/to/repo", "Add feature")

            assert result is True

    def test_commit_failure_logs_warning(self) -> None:
        """Test that git commit failure logs the stderr message.

        When git commit returns non-zero exit code, the adapter should log
        a warning with the stderr content and return False.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Empty message"],
            returncode=1,
            stdout="",
            stderr="error: pathspec 'commit' did not match any file(s) known to git",
        )

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/path/to/repo", "Empty message")

            assert result is False
            mock_warning.assert_called_once_with(
                "Git commit failed: error: pathspec 'commit' did not match any file(s) known to git"
            )

    def test_commit_handles_timeout(self) -> None:
        """Test that subprocess timeout returns False.

        When git commit times out, the adapter should log a warning and return False.
        """
        with (
            patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30)),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/path/to/repo", "Add feature")

            assert result is False
            mock_warning.assert_called_once_with("Git commit command timed out")

    def test_commit_handles_git_not_found(self) -> None:
        """Test that FileNotFoundError returns False.

        When git executable is not found, the adapter should log a warning and return False.
        """
        with (
            patch.object(subprocess, "run", side_effect=FileNotFoundError("git")),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/path/to/repo", "Add feature")

            assert result is False
            mock_warning.assert_called_once_with("Git command not found")

    def test_commit_passes_correct_command_args(self) -> None:
        """Test that subprocess.run receives the correct command arguments.

        The commit method should invoke git with: ["git", "commit", "-m", "<message>"]
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "My commit message"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.commit("/path/to/repo", "My commit message")

            mock_run.assert_called_once_with(
                ["git", "commit", "-m", "My commit message"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                timeout=30,
            )

    def test_commit_passes_git_root_as_cwd(self) -> None:
        """Test that cwd parameter is set to git_root.

        The commit method should pass git_root as the cwd to subprocess.run.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "test"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.commit("/custom/repo/path", "test")

            mock_run.assert_called_once_with(
                ["git", "commit", "-m", "test"],
                cwd="/custom/repo/path",
                capture_output=True,
                text=True,
                timeout=30,
            )

    def test_commit_success_logs_debug_message(self) -> None:
        """Test that successful commit logs a debug message with stdout.

        When git commit succeeds, the adapter should log the stdout content.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Add feature"],
            returncode=0,
            stdout=" 1 file changed, 10 insertions(+)\n",
            stderr="",
        )

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "debug") as mock_debug,
        ):
            self.adapter.commit("/path/to/repo", "Add feature")

            mock_debug.assert_called_once_with("Commit successful: 1 file changed, 10 insertions(+)")

    def test_commit_handles_no_staged_files(self) -> None:
        """Test git returns False when nothing is staged.

        When git commit fails because there are no staged files (exit code 1),
        the adapter should return False and log the error.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Add feature"],
            returncode=1,
            stdout="",
            stderr="error: nothing added to commit but untracked files present\n",
        )

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/path/to/repo", "Add feature")

            assert result is False
            mock_warning.assert_called_once()
            assert "nothing added to commit" in mock_warning.call_args[0][0]

    def test_commit_handles_not_a_directory(self) -> None:
        """Test handling of NotADirectoryError.

        When git_root is not a valid directory, the adapter should return False.
        """
        with (
            patch.object(subprocess, "run", side_effect=NotADirectoryError),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/not/a/directory", "Add feature")

            assert result is False
            assert mock_warning.called

    def test_commit_handles_os_error(self) -> None:
        """Test handling of generic OSError.

        When git commit encounters a generic OS error, the adapter should return False.
        """
        with (
            patch.object(subprocess, "run", side_effect=OSError("Permission denied")),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/path/to/repo", "Add feature")

            assert result is False
            mock_warning.assert_called_once()
            assert "Permission denied" in mock_warning.call_args[0][0]

    @pytest.mark.parametrize(
        "returncode",
        [1, 2, 128],
    )
    def test_commit_various_error_codes(self, returncode: int) -> None:
        """Test handling of various non-zero exit codes.

        Any non-zero exit code should result in False being returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "test"],
            returncode=returncode,
            stdout="",
            stderr=f"error {returncode}",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.commit("/path/to/repo", "test")

            assert result is False

    def test_commit_with_message_containing_special_characters(self) -> None:
        """Test commit with special characters in message.

        The commit message is passed directly to git without escaping,
        which is the expected behavior for subprocess.run with text mode.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Fix: update | value in config"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.commit("/path/to/repo", "Fix: update | value in config")

            mock_run.assert_called_once_with(
                ["git", "commit", "-m", "Fix: update | value in config"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                timeout=30,
            )
