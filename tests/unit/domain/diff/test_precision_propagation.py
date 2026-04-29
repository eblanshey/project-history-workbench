# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for float precision propagation from settings through
# diff computation and presentation layers. Tests verify that runtime precision settings
# affect float equality comparisons and display formatting consistently.
"""Tests for float precision propagation from settings."""

from unittest.mock import MagicMock

from freecad.diff_wb.domain.config import FLOAT_PRECISION as DEFAULT_FLOAT_PRECISION
from freecad.diff_wb.domain.diff.engine import DiffEngine
from freecad.diff_wb.domain.diff.models import (
    DiffState,
    NodeDiff,
    PropertyDiff,
    PropertyPathDiff,
    _path_values_equal,
)
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.domain.snapshots.models import SnapshotObject, SnapshotOccurrence
from freecad.diff_wb.domain.tree.data_path import (
    PrimitiveData,
    PropertyPathType,
    PropertyPathValue,
)
from freecad.diff_wb.domain.tree.property import Property


def _snapshot_from_parts(
    snapshot_id: str,
    document_name: str,
    objects: list[SnapshotObject],
    occurrences: list[SnapshotOccurrence],
) -> Snapshot:
    return Snapshot(
        snapshot_id=snapshot_id,
        document_name=document_name,
        timestamp=__import__("datetime").datetime.now(),
        objects=objects,
        occurrences=occurrences,
    )


class TestPrecisionPropagationPropertyPathEqual:
    """Tests that precision parameter affects _path_values_equal function."""

    def test_default_precision_2_floats_at_boundary(self) -> None:
        """With default precision 2, values rounding to same are equal."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.567)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.569)
        # At precision 2, both round to 1.57
        assert _path_values_equal(pv1, pv2, precision=2) is True

    def test_default_precision_2_floats_different_at_boundary(self) -> None:
        """With default precision 2, values rounding differently are not equal."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.567)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.579)
        # At precision 2: 1.57 vs 1.58 - different
        assert _path_values_equal(pv1, pv2, precision=2) is False

    def test_higher_precision_5_tighter_tolerance(self) -> None:
        """With precision 5, more decimal places matter."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.56789)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.56791)
        # At precision 5, these differ: 1.56789 vs 1.56791
        assert _path_values_equal(pv1, pv2, precision=5) is False
        # But at precision 2, they would be equal too (both 1.57)
        assert _path_values_equal(pv1, pv2, precision=2) is True

    def test_lower_precision_0_coarser_tolerance(self) -> None:
        """With precision 0, only integer part matters."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.4)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.5)
        # At precision 0, 1.4 rounds to 1, 1.5 rounds to 2 (banker's rounding)
        assert _path_values_equal(pv1, pv2, precision=0) is False
        # Use values that clearly round to same integer
        pv3 = PropertyPathValue(PropertyPathType.FLOAT, 1.4)
        pv4 = PropertyPathValue(PropertyPathType.FLOAT, 1.2)
        # Both round to 1 at precision 0
        assert _path_values_equal(pv3, pv4, precision=0) is True
        # At precision 1, they differ: 1.4 vs 1.2
        assert _path_values_equal(pv3, pv4, precision=1) is False

    def test_precision_affects_property_path_diff_state(self) -> None:
        """Precision parameter affects PropertyPathDiff value_state calculation."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.567)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.569)

        # With precision 2, these are considered equal -> UNCHANGED
        diff_at_2 = PropertyPathDiff(path="x", old_value=pv1, new_value=pv2, precision=2)
        assert diff_at_2.value_state == DiffState.UNCHANGED

        # With precision 3, these are different -> MODIFIED
        diff_at_3 = PropertyPathDiff(path="x", old_value=pv1, new_value=pv2, precision=3)
        assert diff_at_3.value_state == DiffState.MODIFIED


class TestPrecisionPropagationPropertyDiff:
    """Tests that precision affects PropertyDiff state calculation."""

    def test_property_diff_uses_precision_for_float_comparison(self) -> None:
        """PropertyDiff computes state based on precision parameter."""
        from freecad.diff_wb.domain.tree.data_path import PrimitiveData

        # Create Property objects with float values using PrimitiveData
        old_prop = Property(
            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 1.567)}), group="Test"
        )
        new_prop = Property(
            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 1.569)}), group="Test"
        )

        # With precision 2, values are equal -> UNCHANGED
        diff_at_2 = PropertyDiff(property_name="TestProp", old_value=old_prop, new_value=new_prop, precision=2)
        assert diff_at_2.state == DiffState.UNCHANGED

        # With precision 3, values differ -> MODIFIED
        diff_at_3 = PropertyDiff(property_name="TestProp", old_value=old_prop, new_value=new_prop, precision=3)
        assert diff_at_3.state == DiffState.MODIFIED


class TestPrecisionPropagationNodeDiff:
    """Tests that precision affects NodeDiff state through property diffs."""

    def test_node_diff_state_affected_by_precision(self) -> None:
        """NodeDiff state reflects precision-based property comparison."""
        from freecad.diff_wb.domain.tree.data_path import PrimitiveData

        # Create Property objects with float values using PrimitiveData
        old_prop = Property(
            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 1.567)}), group="Test"
        )
        new_prop = Property(
            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 1.569)}), group="Test"
        )

        # With precision 2, property is unchanged -> node is UNCHANGED
        node_at_2 = NodeDiff(
            path="TestNode",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="TestProp", old_value=old_prop, new_value=new_prop, precision=2)
            ],
        )
        assert node_at_2.state == DiffState.UNCHANGED

        # With precision 3, property is modified -> node is MODIFIED
        node_at_3 = NodeDiff(
            path="TestNode",
            type_id="Part::Feature",
            property_diffs=[
                PropertyDiff(property_name="TestProp", old_value=old_prop, new_value=new_prop, precision=3)
            ],
        )
        assert node_at_3.state == DiffState.MODIFIED


class TestPrecisionRegressionDefaultBehavior:
    """Regression tests for default precision behavior (precision=2)."""

    def test_default_precision_matches_config_default(self) -> None:
        """Default precision of 2 matches config.FLOAT_PRECISION."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.0 + 1e-8)
        # These should be equal at default precision 2
        assert _path_values_equal(pv1, pv2, precision=DEFAULT_FLOAT_PRECISION) is True

    def test_regression_small_float_differences_ignored_at_default(self) -> None:
        """Small float differences (< 0.005) are ignored at default precision."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 0.0)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 0.004)
        assert _path_values_equal(pv1, pv2, precision=2) is True

    def test_regression_larger_float_differences_captured_at_default(self) -> None:
        """Larger float differences (>= 0.01) are captured at default precision."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 0.0)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 0.01)
        assert _path_values_equal(pv1, pv2, precision=2) is False


class TestFloatValuesEqualEdgeCases:
    """Tests for edge cases in float comparison with varying precision."""

    def test_very_large_numbers_with_precision(self) -> None:
        """Large numbers work correctly with precision parameter."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1e6)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1e6 + 0.001)
        # At precision 2, both round to 1000000.00
        assert _path_values_equal(pv1, pv2, precision=2) is True

    def test_very_small_numbers_with_precision(self) -> None:
        """Very small numbers work correctly with precision parameter."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1e-10)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 2e-10)
        # At precision 2, both round to 0.00
        assert _path_values_equal(pv1, pv2, precision=2) is True
        # At precision 9, they both still round to 0.0 (round(1e-10, 9) = 0.0)
        assert _path_values_equal(pv1, pv2, precision=9) is True
        # At precision 10, they differ: 0.0000000001 vs 0.0000000002
        assert _path_values_equal(pv1, pv2, precision=10) is False

    def test_negative_numbers_with_precision(self) -> None:
        """Negative numbers work correctly with precision parameter."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, -1.567)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, -1.569)
        # At precision 2, both round to -1.57
        assert _path_values_equal(pv1, pv2, precision=2) is True

    def test_zero_precision_only_integer_part(self) -> None:
        """Precision 0 compares only integer parts."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 3.4)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 3.1)
        # At precision 0, both round to 3
        assert _path_values_equal(pv1, pv2, precision=0) is True
        pv3 = PropertyPathValue(PropertyPathType.FLOAT, 4.0)
        # But 3 vs 4 are different
        assert _path_values_equal(pv1, pv3, precision=0) is False

    def test_max_precision_12_tight_tolerance(self) -> None:
        """Maximum precision 12 provides very tight tolerance."""
        # Test with values that have clear differences at various precisions
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.123456789012)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.123456789013)
        # At precision 12, these differ in the last digit
        assert _path_values_equal(pv1, pv2, precision=12) is False
        # At precision 11, they round to the same
        assert _path_values_equal(pv1, pv2, precision=11) is True
        # Same value is always equal
        assert _path_values_equal(pv1, pv1, precision=12) is True


class TestPrecisionInPropertyPathValues:
    """Tests for precision in PropertyPathValue comparisons."""

    def test_path_values_equal_at_different_precisions(self) -> None:
        """Same values compare differently at different precisions."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.234)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.236)

        # At precision 1: both round to 1.2 -> equal
        assert _path_values_equal(pv1, pv2, precision=1) is True

        # At precision 2: 1.23 vs 1.24 -> not equal
        assert _path_values_equal(pv1, pv2, precision=2) is False

        # At precision 3: 1.234 vs 1.236 -> not equal
        assert _path_values_equal(pv1, pv2, precision=3) is False


class TestPrecisionPropagationDiffEngine:
    """Integration tests for precision propagation through DiffEngine.compute_diff()."""

    def test_compute_diff_with_custom_precision_produces_different_results_than_default(
        self,
    ) -> None:
        """DiffEngine.compute_diff() with custom precision produces different results than default precision.

        This test verifies that:
        1. With precision=2 (default), values 1.567 and 1.569 are considered equal (both round to 1.57)
        2. With precision=3, the same values are considered different (1.567 vs 1.569)
        """
        # Create mock settings repos with different precision values
        settings_repo_default = MagicMock()
        settings_repo_default.get_excluded_types.return_value = []
        settings_repo_default.get_excluded_properties.return_value = []
        settings_repo_default.get_excluded_properties_by_type.return_value = {}
        settings_repo_default.get_float_precision.return_value = 2  # Default precision

        settings_repo_high_precision = MagicMock()
        settings_repo_high_precision.get_excluded_types.return_value = []
        settings_repo_high_precision.get_excluded_properties.return_value = []
        settings_repo_high_precision.get_excluded_properties_by_type.return_value = {}
        settings_repo_high_precision.get_float_precision.return_value = 3  # Higher precision

        # Create snapshots with nodes that have float properties at the precision boundary
        # Value 1.567 vs 1.569 - equal at precision 2, different at precision 3
        old_snapshot = _snapshot_from_parts(
            "test-id-1",
            "Test",
            objects=[
                SnapshotObject(
                    name="TestNode",
                    id=1,
                    type_id="Part::Feature",
                    properties={
                        "Value": Property(
                            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 1.567)}),
                            group="Test",
                        )
                    },
                )
            ],
            occurrences=[SnapshotOccurrence(path="TestNode", after=None)],
        )
        new_snapshot = _snapshot_from_parts(
            "test-id-2",
            "Test",
            objects=[
                SnapshotObject(
                    name="TestNode",
                    id=1,
                    type_id="Part::Feature",
                    properties={
                        "Value": Property(
                            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 1.569)}),
                            group="Test",
                        )
                    },
                )
            ],
            occurrences=[SnapshotOccurrence(path="TestNode", after=None)],
        )

        # Compute diff with default precision (2)
        engine_default = DiffEngine(settings_repo=settings_repo_default)
        result_default = engine_default.compute_diff(old_snapshot, new_snapshot)

        # Compute diff with higher precision (3)
        engine_high = DiffEngine(settings_repo=settings_repo_high_precision)
        result_high = engine_high.compute_diff(old_snapshot, new_snapshot)

        # At precision 2: values are equal -> no modification
        root_node_default = result_default.hierarchy.roots[0]
        assert root_node_default.state == DiffState.UNCHANGED
        prop_diff_default = root_node_default.property_diffs[0]
        assert prop_diff_default.state == DiffState.UNCHANGED

        # At precision 3: values are different -> modification detected
        root_node_high = result_high.hierarchy.roots[0]
        assert root_node_high.state == DiffState.MODIFIED
        prop_diff_high = root_node_high.property_diffs[0]
        assert prop_diff_high.state == DiffState.MODIFIED

    def test_compute_diff_uses_settings_repo_precision(self) -> None:
        """DiffEngine.compute_diff() uses precision from settings repo."""
        # Create mock settings repo with precision=0 (only integer part matters)
        settings_repo = MagicMock()
        settings_repo.get_excluded_types.return_value = []
        settings_repo.get_excluded_properties.return_value = []
        settings_repo.get_excluded_properties_by_type.return_value = {}
        settings_repo.get_float_precision.return_value = 0  # Only integer part

        # Create snapshots with float values that differ only in decimal part
        old_snapshot = _snapshot_from_parts(
            "test-id-3",
            "Test",
            objects=[
                SnapshotObject(
                    name="TestNode",
                    id=1,
                    type_id="Part::Feature",
                    properties={
                        "Value": Property(
                            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 3.4)}),
                            group="Test",
                        )
                    },
                )
            ],
            occurrences=[SnapshotOccurrence(path="TestNode", after=None)],
        )
        new_snapshot = _snapshot_from_parts(
            "test-id-4",
            "Test",
            objects=[
                SnapshotObject(
                    name="TestNode",
                    id=1,
                    type_id="Part::Feature",
                    properties={
                        "Value": Property(
                            value=PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.FLOAT, 3.2)}),
                            group="Test",
                        )
                    },
                )
            ],
            occurrences=[SnapshotOccurrence(path="TestNode", after=None)],
        )

        # Compute diff with precision=0
        engine = DiffEngine(settings_repo=settings_repo)
        result = engine.compute_diff(old_snapshot, new_snapshot)

        # At precision 0: both round to 3 -> unchanged (round(3.4, 0) = 3, round(3.2, 0) = 3)
        root_node = result.hierarchy.roots[0]
        assert root_node.state == DiffState.UNCHANGED
