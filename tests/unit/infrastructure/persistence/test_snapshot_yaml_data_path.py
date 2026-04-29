# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for YAML persistence wiring with the DataPath-based
# Property model. Verifies serialization envelopes, list payloads, unknown payloads,
# and complete snapshot round-trips.
"""Tests for YAML persistence with DataPath-based Property model.

Phase 4: YAML Persistence Wiring.

Verifies that:
- Property serialization uses Property.to_serialized() envelope (kind, paths, group)
- List payload uses items with per-item paths envelopes
- Unknown payload preserves path-level freecad_type + display root
- Complete snapshot round-trip equality for mixed property types
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

import pytest
import yaml

from freecad.diff_wb.domain import Property, Snapshot, SnapshotObject, SnapshotOccurrence
from freecad.diff_wb.domain.tree.data_path import (
    ListData,
    PrimitiveData,
    PropertyPathType,
    PropertyPathValue,
    UnknownData,
)
from freecad.diff_wb.infrastructure.persistence import SnapshotYamlSerializer


class _NodeFixture(TypedDict, total=False):
    id: int
    name: str
    type_id: str
    label: str
    path: str
    after: str | None
    properties: dict[str, Property]


def _snapshot_from_rows(nodes: list[_NodeFixture], snapshot_id: str, document_name: str = "") -> Snapshot:
    """Build normalized snapshot test fixture from flat node rows."""
    objects_by_name: dict[str, SnapshotObject] = {}
    occurrences: list[SnapshotOccurrence] = []
    for node in nodes:
        name = str(node["name"])
        objects_by_name.setdefault(
            name,
            SnapshotObject(
                name=name,
                id=int(node["id"]),
                type_id=str(node["type_id"]),
                properties=node.get("properties", {}),  # type: ignore[arg-type]
            ),
        )
        occurrences.append(
            SnapshotOccurrence(
                path=str(node["path"]),
                after=(str(node["after"]) if node["after"] is not None else None),
            )
        )
    return Snapshot(
        snapshot_id=snapshot_id,
        document_name=document_name,
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        objects=list(objects_by_name.values()),
        occurrences=occurrences,
    )


def _first_object(snapshot: Snapshot) -> SnapshotObject:
    assert snapshot.occurrences
    occ = snapshot.occurrences[0]
    obj = snapshot.find_object(occ.object_name)
    assert obj is not None
    return obj


class TestSerializePropertiesEnvelope:
    """Tests for _serialize_properties using Property.to_serialized() envelope."""

    def test_primitive_property_envelope(self):
        """A primitive property should serialize with kind, paths, and group keys."""
        prop = Property.from_freecad(10.0, {}, group="Base")
        result = SnapshotYamlSerializer._serialize_properties({"Length": prop})

        assert "Length" in result
        length_data = result["Length"]
        assert "kind" in length_data
        assert length_data["kind"] == "Primitive"
        assert "paths" in length_data
        assert "." in length_data["paths"]
        assert "group" in length_data
        assert length_data["group"] == "Base"

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_placement_property_envelope(self):
        """A placement property should serialize with kind, paths, and group keys."""
        from FreeCAD import Base

        placement = Base.Placement()
        prop = Property.from_freecad(placement, {}, group="Base")
        result = SnapshotYamlSerializer._serialize_properties({"Placement": prop})

        placement_data = result["Placement"]
        assert placement_data["kind"] == "Placement"
        assert "paths" in placement_data
        assert "group" in placement_data
        assert placement_data["group"] == "Base"
        # Verify sub-paths are present
        assert "Base.x" in placement_data["paths"]
        assert "Base.y" in placement_data["paths"]
        assert "Base.z" in placement_data["paths"]

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_vector_property_envelope(self):
        """A vector property should serialize with kind, paths, and group keys."""
        from FreeCAD import Base

        vec = Base.Vector(1.0, 2.0, 3.0)
        prop = Property.from_freecad(vec, {}, group="Data")
        result = SnapshotYamlSerializer._serialize_properties({"Position": prop})

        vec_data = result["Position"]
        assert vec_data["kind"] == "Vector"
        assert "paths" in vec_data
        assert "x" in vec_data["paths"]
        assert "y" in vec_data["paths"]
        assert "z" in vec_data["paths"]
        assert vec_data["group"] == "Data"

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_quantity_property_envelope(self):
        """A quantity property should serialize as primitive with single QUANTITY path."""
        from FreeCAD import Base

        qty = Base.Quantity("10 mm")
        prop = Property.from_freecad(qty, {}, group="Base")
        result = SnapshotYamlSerializer._serialize_properties({"Length": prop})

        qty_data = result["Length"]
        assert qty_data["kind"] == "Primitive"
        assert "paths" in qty_data
        assert set(qty_data["paths"].keys()) == {"."}
        assert qty_data["paths"]["."]["type"] == "QUANTITY"
        assert qty_data["paths"]["."]["value"] == "10.0 mm"
        assert "unit" not in qty_data["paths"]["."]

    def test_string_property_envelope(self):
        """A string property should serialize with kind, paths, and group keys."""
        prop = Property.from_freecad("TestString", {}, group="View")
        result = SnapshotYamlSerializer._serialize_properties({"Label": prop})

        str_data = result["Label"]
        assert str_data["kind"] == "Primitive"
        assert str_data["paths"]["."]["type"] == "STRING"
        assert str_data["paths"]["."]["value"] == "TestString"
        assert str_data["group"] == "View"


class TestListPayloadWithItems:
    """Tests for list property serialization using items with per-item paths envelopes."""

    def test_list_property_serializes_items(self):
        """A list property should serialize with kind, paths, and items keys."""
        # Build a ListData manually with primitive items
        items = [
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.INT, 1)}),
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.INT, 2)}),
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.INT, 3)}),
        ]
        list_data = ListData(paths={}, items=items)
        prop = Property(value=list_data, group="Sketch")

        result = SnapshotYamlSerializer._serialize_properties({"Constraints": prop})
        list_payload = result["Constraints"]

        assert list_payload["kind"] == "List"
        assert "items" in list_payload
        assert len(list_payload["items"]) == 3
        assert list_payload["group"] == "Sketch"

    def test_list_items_have_paths_envelopes(self):
        """Each list item should have its own kind and paths envelope."""
        items = [
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.STRING, "A")}),
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.STRING, "B")}),
        ]
        list_data = ListData(paths={}, items=items)
        prop = Property(value=list_data, group="Base")

        result = SnapshotYamlSerializer._serialize_properties({"Items": prop})
        items_data = result["Items"]["items"]

        assert items_data[0]["kind"] == "Primitive"
        assert "paths" in items_data[0]
        assert items_data[0]["paths"]["."]["value"] == "A"

        assert items_data[1]["kind"] == "Primitive"
        assert items_data[1]["paths"]["."]["value"] == "B"

    def test_list_with_constraint_items(self):
        """A list of constraint-like items should serialize each item with paths."""
        items = [
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.STRING, "DistanceX")}),
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.STRING, "Coincident")}),
        ]
        list_data = ListData(paths={}, items=items)
        prop = Property(value=list_data, group="Sketch")

        result = SnapshotYamlSerializer._serialize_properties({"Constraints": prop})
        list_payload = result["Constraints"]

        assert list_payload["kind"] == "List"
        assert len(list_payload["items"]) == 2
        assert list_payload["items"][0]["paths"]["."]["value"] == "DistanceX"
        assert list_payload["items"][1]["paths"]["."]["value"] == "Coincident"

    def test_list_with_expression_root_path(self):
        """A list with a root expression should include it in the paths envelope."""
        list_paths = {
            ".": PropertyPathValue(PropertyPathType.NULL, None, "SomeExpr"),
        }
        items = [
            PrimitiveData(paths={".": PropertyPathValue(PropertyPathType.INT, 1)}),
        ]
        list_data = ListData(paths=list_paths, items=items)
        prop = Property(value=list_data, group="Base")

        result = SnapshotYamlSerializer._serialize_properties({"Constraints": prop})
        assert result["Constraints"]["paths"]["."]["type"] == "NULL"
        assert result["Constraints"]["paths"]["."]["expression"] == "SomeExpr"


class TestUnknownPayloadPreservation:
    """Tests for unknown payload preserving path-level freecad_type and display root."""

    def test_unknown_payload_has_freecad_type(self):
        """An unknown property should preserve freecad_type in the root path entry."""
        prop = Property.from_freecad(object(), {}, group="Data")
        result = SnapshotYamlSerializer._serialize_properties({"UnknownProp": prop})

        unknown_data = result["UnknownProp"]
        assert unknown_data["kind"] == "Unknown"
        assert "paths" in unknown_data
        assert "." in unknown_data["paths"]
        assert "freecad_type" in unknown_data["paths"]["."]

    def test_unknown_payload_has_display_value(self):
        """An unknown property should store display value in the root path."""
        prop = Property.from_freecad(object(), {}, group="Data")
        result = SnapshotYamlSerializer._serialize_properties({"UnknownProp": prop})

        unknown_data = result["UnknownProp"]
        assert unknown_data["paths"]["."]["type"] == "STRING"
        assert "value" in unknown_data["paths"]["."]

    def test_unknown_roundtrip_preserves_freecad_type(self):
        """Serializing and deserializing an unknown should preserve freecad_type."""
        original = Property.from_freecad(object(), {}, group="Data")
        serialized = original.to_serialized()
        restored = Property.from_serialized(serialized)

        assert isinstance(restored.value, UnknownData)
        assert restored.value.paths["."].freecad_type is not None
        assert restored.value.paths["."].freecad_type == original.value.paths["."].freecad_type

    def test_unknown_roundtrip_preserves_display_value(self):
        """Serializing and deserializing an unknown should preserve display value."""
        original = Property.from_freecad(object(), {}, group="Data")
        serialized = original.to_serialized()
        restored = Property.from_serialized(serialized)

        assert restored.value.paths["."].value == original.value.paths["."].value


class TestSnapshotRoundTrip:
    """Tests for complete snapshot round-trip equality with mixed property types."""

    def test_roundtrip_serialization_deserialization(self):
        """A snapshot with mixed properties should round-trip through YAML."""
        props = {
            "Length": Property.from_freecad(10.0, {}, group="Base"),
            "Name": Property.from_freecad("TestPad", {}, group="Data"),
            "Enabled": Property.from_freecad(True, {}, group="View"),
            "Count": Property.from_freecad(42, {}, group="Data"),
            "Ratio": Property.from_freecad(0.75, {}, group="Base"),
        }
        node = {
            "id": 1,
            "name": "TestPad",
            "type_id": "PartDesign::Pad",
            "label": "TestPad",
            "path": "TestPad",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="roundtrip-test", document_name="RoundTripDoc")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "snapshot.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)

            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        # Verify structure
        assert len(restored.occurrences) == 1
        restored_obj = _first_object(restored)
        assert restored_obj.id == 1
        assert len(restored_obj.properties) == len(props)

    def test_roundtrip_preserves_primitive_values(self):
        """Primitive property values should survive round-trip unchanged."""
        props = {
            "FloatVal": Property.from_freecad(3.14, {}, group="Base"),
            "IntVal": Property.from_freecad(42, {}, group="Data"),
            "StrVal": Property.from_freecad("hello", {}, group="View"),
            "BoolVal": Property.from_freecad(False, {}, group="View"),
        }
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="prim")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_props = _first_object(restored).properties
        assert isinstance(restored_props["FloatVal"].value, PrimitiveData)
        assert restored_props["FloatVal"].value.paths["."].value == pytest.approx(3.14)
        assert restored_props["IntVal"].value.paths["."].value == 42
        assert restored_props["StrVal"].value.paths["."].value == "hello"
        assert restored_props["BoolVal"].value.paths["."].value is False

    def test_roundtrip_preserves_group(self):
        """Property groups should survive round-trip unchanged."""
        props = {
            "A": Property.from_freecad(1.0, {}, group="Base"),
            "B": Property.from_freecad(2.0, {}, group="Data"),
            "C": Property.from_freecad(3.0, {}, group="View"),
        }
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="grp")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        assert _first_object(restored).properties["A"].group == "Base"
        assert _first_object(restored).properties["B"].group == "Data"
        assert _first_object(restored).properties["C"].group == "View"

    def test_roundtrip_preserves_expression(self):
        """Expressions stored in path entries should survive round-trip."""
        props = {
            "Length": Property.from_freecad(10.0, {".": "5 mm"}, group="Base"),
        }
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="expr")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = _first_object(restored).properties["Length"]
        assert isinstance(restored_prop.value, PrimitiveData)
        assert restored_prop.value.paths["."].expression == "5 mm"

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_roundtrip_preserves_vector(self):
        """Vector property values should survive round-trip with correct coordinates."""
        from FreeCAD import Base

        from freecad.diff_wb.domain.tree.data_path import VectorData

        vec = Base.Vector(1.5, 2.5, 3.5)
        props = {"Position": Property.from_freecad(vec, {}, group="Base")}
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="vec")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = _first_object(restored).properties["Position"]
        assert isinstance(restored_prop.value, VectorData)
        assert restored_prop.value.paths["x"].value == pytest.approx(1.5)
        assert restored_prop.value.paths["y"].value == pytest.approx(2.5)
        assert restored_prop.value.paths["z"].value == pytest.approx(3.5)

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_roundtrip_preserves_placement(self):
        """Placement property values should survive round-trip with correct components."""
        from FreeCAD import Base

        from freecad.diff_wb.domain.tree.data_path import PlacementData

        placement = Base.Placement(Base.Vector(1.0, 2.0, 3.0), Base.Rotation(0, 0, 1, 45))
        props = {"Placement": Property.from_freecad(placement, {}, group="Base")}
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="plc")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = _first_object(restored).properties["Placement"]
        assert isinstance(restored_prop.value, PlacementData)
        assert restored_prop.value.paths["Base.x"].value == pytest.approx(1.0)
        assert restored_prop.value.paths["Base.y"].value == pytest.approx(2.0)
        assert restored_prop.value.paths["Base.z"].value == pytest.approx(3.0)

    @pytest.mark.skip(reason="Requires FreeCAD runtime; move to integration tests")
    def test_roundtrip_preserves_quantity_value_and_unit(self):
        """Quantity property values should survive round-trip with QUANTITY path."""
        from FreeCAD import Base

        from freecad.diff_wb.domain.tree.data_path import PrimitiveData, PropertyPathType

        qty = Base.Quantity("10 mm")
        props = {"Amount": Property.from_freecad(qty, {}, group="Base")}
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="qty")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = _first_object(restored).properties["Amount"]
        assert isinstance(restored_prop.value, PrimitiveData)
        assert set(restored_prop.value.paths.keys()) == {"."}
        assert restored_prop.value.paths["."].type_ == PropertyPathType.QUANTITY
        assert restored_prop.value.paths["."].value == pytest.approx(10.0)
        assert restored_prop.value.paths["."].unit == "mm"

    def test_roundtrip_preserves_list(self):
        """List property values should survive round-trip with correct items."""
        props = {"Items": Property.from_freecad([1, 2, 3], {}, group="Base")}
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="lst")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = _first_object(restored).properties["Items"]
        assert isinstance(restored_prop.value, ListData)
        assert len(restored_prop.value.items) == 3
        assert restored_prop.value.items[0].paths["."].value == 1
        assert restored_prop.value.items[1].paths["."].value == 2
        assert restored_prop.value.items[2].paths["."].value == 3

    def test_roundtrip_with_empty_properties(self):
        """A snapshot with empty properties should round-trip correctly."""
        node = {
            "id": 1,
            "name": "Empty",
            "type_id": "Test",
            "label": "Empty",
            "path": "Empty",
            "after": None,
            "properties": {},
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="empty")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        assert len(_first_object(restored).properties) == 0

    def test_roundtrip_with_unknown_property(self):
        """An unknown property should survive round-trip with freecad_type preserved."""
        props = {"Unknown": Property.from_freecad(object(), {}, group="Data")}
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="unknown")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        restored_prop = _first_object(restored).properties["Unknown"]
        assert isinstance(restored_prop.value, UnknownData)
        assert restored_prop.value.paths["."].freecad_type is not None
        assert restored_prop.value.paths["."].freecad_type == props["Unknown"].value.paths["."].freecad_type

    def test_yaml_output_format_matches_spec(self):
        """The YAML output should match the DataPath-based envelope spec."""
        props = {"Length": Property.from_freecad(10.0, {}, group="Base")}
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="fmt")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            content = yaml_path.read_text()
            data = yaml.safe_load(content)

        # Check the property envelope structure
        prop_data = data["objects"][0]["properties"]["Length"]
        assert "kind" in prop_data
        assert prop_data["kind"] == "Primitive"
        assert "paths" in prop_data
        assert "group" in prop_data
        assert prop_data["group"] == "Base"
        # Should NOT have old-style "value" or "expression" at property level
        assert "value" not in prop_data
        assert "expression" not in prop_data

    def test_yaml_output_has_paths_not_value(self):
        """Serialized properties should use 'paths' key, not 'value' key."""
        props = {"Length": Property.from_freecad(10.0, {}, group="Base")}
        node = {
            "id": 1,
            "name": "Test",
            "type_id": "Test",
            "label": "Test",
            "path": "Test",
            "after": None,
            "properties": props,
        }
        snapshot = _snapshot_from_rows([node], snapshot_id="paths")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            data = yaml.safe_load(yaml_path.read_text())

        prop_data = data["objects"][0]["properties"]["Length"]
        assert "paths" in prop_data
        assert "value" not in prop_data

    def test_multiple_nodes_with_different_property_types(self):
        """A snapshot with multiple nodes having different property types should round-trip."""
        nodes = [
            {
                "id": 1,
                "name": "Pad",
                "type_id": "PartDesign::Pad",
                "label": "Pad",
                "path": "Pad",
                "after": None,
                "properties": {
                    "Length": Property.from_freecad(10.0, {}, group="Base"),
                    "Enabled": Property.from_freecad(True, {}, group="View"),
                },
            },
            {
                "id": 2,
                "name": "Sketch",
                "type_id": "Sketcher::SketchObject",
                "label": "Sketch",
                "path": "Sketch",
                "after": "Pad",
                "properties": {
                    "Name": Property.from_freecad("MySketch", {}, group="Data"),
                    "Count": Property.from_freecad(5, {}, group="Data"),
                },
            },
        ]
        snapshot = _snapshot_from_rows(nodes, snapshot_id="multi", document_name="MultiDoc")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "s.yaml"
            SnapshotYamlSerializer.to_yaml(snapshot, yaml_path)
            restored = SnapshotYamlSerializer.from_yaml_file(yaml_path)

        assert len(restored.occurrences) == 2
        pad_obj = restored.find_object("Pad")
        sketch_obj = restored.find_object("Sketch")
        assert pad_obj is not None
        assert sketch_obj is not None
        assert "Length" in pad_obj.properties
        assert "Enabled" in pad_obj.properties
        assert "Name" in sketch_obj.properties
        assert "Count" in sketch_obj.properties
