# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Application action for unstaging reviewed documents from git index only.
"""Application action for removing reviewed documents from git staging."""

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...domain.git.paths import to_git_path
from ...domain.snapshots import get_snapshot_yaml_path_for_document
from .result_models import Result


__all__ = ["UnstageDocumentsAction"]


class UnstageDocumentsAction:
    """Unstage reviewed documents from git index without touching working tree."""

    def __init__(self, git_service: GitService) -> None:
        self._git_service = git_service

    def execute(self, repo: GitRepository, fcstd_paths: list[str] | None = None) -> Result:
        """Unstage selected documents or all staged paths.

        Args:
            repo: Target git repository.
            fcstd_paths: FCStd git paths. None means unstage all staged paths.

        Returns:
            Result.success(True) on success, Result.failure(...) on failure.
        """
        if fcstd_paths is None:
            if self._git_service.unstage_all(repo):
                return Result.success(True)
            return Result.failure("Failed to unstage reviewed files")

        if not fcstd_paths:
            return Result.success(True)

        paths_to_unstage: list[str] = []
        for fcstd_path in fcstd_paths:
            normalized_fcstd = to_git_path(fcstd_path)
            snapshot_path = get_snapshot_yaml_path_for_document(normalized_fcstd)
            paths_to_unstage.append(normalized_fcstd)
            paths_to_unstage.append(snapshot_path.as_posix())

        if self._git_service.unstage_files(repo, paths_to_unstage):
            return Result.success(True)
        return Result.failure("Failed to unstage reviewed files")
