# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Provide fake implementations for testing including FakeLogger,
# FakeSnapshotRepository, FakeSettingsRepository, FakeDiffEngine, FakeDiffView, and InMemorySnapshotRepository.
"""Fake implementations for testing."""

from .fake_diff_view import FakeDiffView
from .fake_logger import FakeLogger
from .fake_repositories import (
    FakeDiffEngine,
    FakeSettingsRepository,
    FakeSnapshotRepository,
    InMemorySnapshotRepository,
)
from .fake_snapshot_view import FakeSnapshotView


__all__ = [
    "FakeLogger",
    "FakeSnapshotRepository",
    "FakeSettingsRepository",
    "FakeDiffEngine",
    "FakeDiffView",
    "InMemorySnapshotRepository",
    "FakeSnapshotView",
]
