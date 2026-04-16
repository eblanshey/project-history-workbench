# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for CreateDiffAction using fake DiffEngine.
# Tests cover success scenarios, missing old snapshot warning, and same snapshot warning.
"""Unit tests for CreateDiffAction."""

from datetime import datetime
from typing import Protocol

from freecad.diff_wb.application.actions.create_diff import CreateDiffAction
from freecad.diff_wb.domain.diff.models import WARNING_OLD_SNAPSHOT_MISSING, DiffResult
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.tree.property import Property


class DiffEngineProtocol(Protocol):
    """Protocol for DiffEngine to enable duck-typing in tests."""

    def compute_diff(self, old: Snapshot | None, new: Snapshot) -> DiffResult: ...  # noqa: E704


class FakeDiffEngine:
    """Fake DiffEngine for testing CreateDiffAction."""

    def __init__(self) -> None:
        self._should_raise = False
        self._raise_exception: Exception | None = None

    def set_to_raise(self, exception: Exception) -> None:
        """Configure fake to raise an exception."""
        self._should_raise = True
        self._raise_exception = exception

    def compute_diff(self, old: Snapshot | None, new: Snapshot) -> DiffResult:
        """Fake implementation of compute_diff."""
        if self._should_raise and self._raise_exception is not None:
            raise self._raise_exception

        # Create a simple diff result
        return DiffResult(
            old_snapshot=old if old is not None else new,
            new_snapshot=new,
            warnings=[],
        )


class MockTreeNode:
    """Mock tree node for testing."""

    def __init__(self, name: str, path: str) -> None:
        self.name = name
        self.path = path
        self.type_id = "TestType"
        self.properties: list[Property] = []
        self.children: list[MockTreeNode] = []
        self.parent: MockTreeNode | None = None


def create_test_snapshot(name: str, git_path: str = "") -> Snapshot:
    """Create a test snapshot with minimal data."""
    return Snapshot(
        snapshot_id="test-id",
        document_name=name,
        timestamp=datetime.now(),
        nodes=[],
        git_path=git_path,
    )


class TestCreateDiffActionSuccess:
    """Tests for successful diff creation."""

    def test_execute_returns_result_with_diff_result_on_success(self) -> None:
        """Test that action returns Result with DiffResult on success."""
        # Setup
        fake_engine = FakeDiffEngine()
        action = CreateDiffAction(fake_engine)

        old_snapshot = create_test_snapshot("old_doc")
        new_snapshot = create_test_snapshot("new_doc")

        # Execute
        result = action.execute(old_snapshot, new_snapshot)

        # Assert
        assert result.is_success is True
        assert result.data is not None
        assert isinstance(result.data, DiffResult)
        assert result.message is None

    def test_execute_passes_snapshots_correctly_to_diff_engine(self) -> None:
        """Test that action passes snapshots correctly to DiffEngine."""
        # Setup
        fake_engine = FakeDiffEngine()
        action = CreateDiffAction(fake_engine)

        old_snapshot = create_test_snapshot("old_doc", "path/old.FCStd")
        new_snapshot = create_test_snapshot("new_doc", "path/new.FCStd")

        # Execute
        result = action.execute(old_snapshot, new_snapshot)

        # Assert - the diff result should contain both snapshots
        assert result.is_success is True
        assert result.data is not None
        assert result.data.old_snapshot.document_name == "old_doc"
        assert result.data.new_snapshot.document_name == "new_doc"


class TestCreateDiffActionWithNoneOldSnapshot:
    """Tests for handling missing old snapshot."""

    def test_when_old_snapshot_is_none_diff_result_has_warning(self) -> None:
        """Test that when old_snapshot is None, DiffResult has WARNING_OLD_SNAPSHOT_MISSING."""

        # Setup - use a fake engine that adds the warning when old is None
        # Note: The fake engine creates a DIFFERENT old snapshot to avoid triggering
        # the "same snapshot" warning in DiffResult.__post_init__
        class FakeDiffEngineWithWarning:
            def compute_diff(self, old: Snapshot | None, new: Snapshot) -> DiffResult:
                warnings = []
                if old is None:
                    warnings.append(WARNING_OLD_SNAPSHOT_MISSING)
                    # Create a different old snapshot to avoid "same snapshot" warning
                    old = Snapshot(
                        snapshot_id="different-id",
                        document_name=new.document_name + "_old",
                        timestamp=datetime.now(),
                        nodes=[],
                        git_path=new.git_path,
                    )
                return DiffResult(
                    old_snapshot=old,
                    new_snapshot=new,
                    warnings=warnings,
                )

        action = CreateDiffAction(FakeDiffEngineWithWarning())
        new_snapshot = create_test_snapshot("new_doc")

        # Execute with None as old snapshot
        result = action.execute(None, new_snapshot)

        # Assert - should be success with WARNING_OLD_SNAPSHOT_MISSING
        assert result.is_success is True
        assert result.data is not None
        assert isinstance(result.data, DiffResult)
        assert WARNING_OLD_SNAPSHOT_MISSING in result.data.warnings


class TestCreateDiffActionWithSameSnapshot:
    """Tests for handling same snapshot case."""

    def test_when_old_snapshot_equals_new_snapshot_diff_result_has_no_warning(self) -> None:
        """Test that when old_snapshot equals new_snapshot, DiffResult has no warning."""
        # Setup
        fake_engine = FakeDiffEngine()
        action = CreateDiffAction(fake_engine)

        # Use the same snapshot instance for both
        same_snapshot = create_test_snapshot("same_doc")

        # Execute with same snapshot for both old and new
        result = action.execute(same_snapshot, same_snapshot)

        # Assert - should succeed with no warning (same snapshot is valid)
        assert result.is_success is True
        assert result.data is not None
        assert isinstance(result.data, DiffResult)
        # No warning expected for same snapshot
        assert len(result.data.warnings) == 0


class TestCreateDiffActionFailure:
    """Tests for failure scenarios."""

    def test_execute_returns_failure_result_when_diff_engine_raises_exception(self) -> None:
        """Test that action returns failure Result when DiffEngine raises exception."""
        # Setup
        fake_engine = FakeDiffEngine()
        fake_engine.set_to_raise(ValueError("Test error"))
        action = CreateDiffAction(fake_engine)

        old_snapshot = create_test_snapshot("old_doc")
        new_snapshot = create_test_snapshot("new_doc")

        # Execute
        result = action.execute(old_snapshot, new_snapshot)

        # Assert
        assert result.is_success is False
        assert result.data is None
        assert result.message is not None
        assert "Failed to compute diff" in result.message

    def test_execute_handles_unexpected_errors_gracefully(self) -> None:
        """Test that action handles unexpected errors gracefully."""
        # Setup
        fake_engine = FakeDiffEngine()
        fake_engine.set_to_raise(RuntimeError("Unexpected error"))
        action = CreateDiffAction(fake_engine)

        old_snapshot = create_test_snapshot("old_doc")
        new_snapshot = create_test_snapshot("new_doc")

        # Execute
        result = action.execute(old_snapshot, new_snapshot)

        # Assert - should return failure, not raise exception
        assert result.is_success is False
        assert result.data is None
