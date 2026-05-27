# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for UnstageDocumentsAction behavior and path expansion.
"""Unit tests for unstage_documents action."""

from freecad.history_wb.application.actions.result_models import Result
from freecad.history_wb.application.actions.unstage_documents import UnstageDocumentsAction
from freecad.history_wb.domain.git import GitRepository, GitService
from tests.fakes import FakeGitPort


def test_none_unstages_all_paths() -> None:
    fake_port = FakeGitPort()
    service = GitService(git_port=fake_port)
    action = UnstageDocumentsAction(git_service=service)
    repo = GitRepository(name="repo", absolute_path="/repo")

    result = action.execute(repo, None)

    assert isinstance(result, Result)
    assert result.is_success is True
    assert fake_port.get_last_unstage_all_call() == "/repo"


def test_single_fcstd_expands_to_fcstd_and_snapshot_yaml() -> None:
    fake_port = FakeGitPort()
    service = GitService(git_port=fake_port)
    action = UnstageDocumentsAction(git_service=service)
    repo = GitRepository(name="repo", absolute_path="/repo")

    result = action.execute(repo, ["parts/A.FCStd"])

    assert result.is_success is True
    assert fake_port.get_last_unstage_files_call() == (
        "/repo",
        ["parts/A.FCStd", "parts/.snapshots/A.yaml"],
    )


def test_empty_list_returns_success_without_git_call() -> None:
    fake_port = FakeGitPort()
    service = GitService(git_port=fake_port)
    action = UnstageDocumentsAction(git_service=service)
    repo = GitRepository(name="repo", absolute_path="/repo")

    result = action.execute(repo, [])

    assert result.is_success is True
    assert fake_port.get_last_unstage_files_call() is None
    assert fake_port.get_last_unstage_all_call() is None


def test_git_failure_returns_failure_result() -> None:
    fake_port = FakeGitPort(fail_unstage=True)
    service = GitService(git_port=fake_port)
    action = UnstageDocumentsAction(git_service=service)
    repo = GitRepository(name="repo", absolute_path="/repo")

    result = action.execute(repo, ["parts/A.FCStd"])

    assert result.is_success is False
