"""Tests for spec bundling and schema classification in :mod:`allotrope_gen.schema`."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from allotrope_gen.config import SPECS
from allotrope_gen.schema import (
    bundle_spec,
    generates_model,
    load_yaml,
    merged_commons_schemas,
    nan_capable_properties,
)


def _write(path: Path, schemas: dict) -> Path:
    """Write a minimal OpenAPI document with *schemas* to *path*."""
    path.write_text(
        yaml.dump({"openapi": "3.1.0", "info": {"title": "t", "version": "1"},
                   "components": {"schemas": schemas}}),
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def commons(tmp_path: Path) -> list[Path]:
    """Two commons files with cross-file, nested and alias schemas."""
    common = _write(tmp_path / "common.yaml", {
        "Value": {
            "type": "object",
            "properties": {"value": {"type": "number", "x-asm-nan": True},
                           "unit": {"type": "string"}},
        },
        "Seconds": {"allOf": [
            {"$ref": "#/components/schemas/Value"},
            {"type": "object", "properties": {"unit": {"type": "string", "enum": ["s"]}}},
        ]},
        "Either": {"oneOf": [
            {"type": "number"},
            {"type": "object", "properties": {"@type": {"type": "string"}}},
        ]},
        "Unused": {"type": "object", "properties": {"x": {"type": "string"}}},
    })
    core = _write(tmp_path / "core.yaml", {
        "Named": {"type": "string"},
        "Doc": {"type": "object", "properties": {
            "duration": {"$ref": "./common.yaml#/components/schemas/Seconds"},
            "label": {"$ref": "#/components/schemas/Named"},
            "either": {"$ref": "./common.yaml#/components/schemas/Either"},
        }},
    })
    return [common, core]


def _spec(tmp_path: Path) -> Path:
    return _write(tmp_path / "gc.yaml", {
        "Root": {"type": "object", "properties": {
            "doc": {"$ref": "./core.yaml#/components/schemas/Doc"},
        }},
    })


class TestBundleSpec:
    def test_references_become_local(self, tmp_path: Path, commons: list[Path]):
        bundled, _ = bundle_spec(_spec(tmp_path), tmp_path / "out", commons)
        root = load_yaml(bundled)["components"]["schemas"]["Root"]
        assert root["properties"]["doc"] == {"$ref": "#/components/schemas/Doc"}

    def test_transitive_closure_is_copied(self, tmp_path: Path, commons: list[Path]):
        bundled, _ = bundle_spec(_spec(tmp_path), tmp_path / "out", commons)
        schemas = load_yaml(bundled)["components"]["schemas"]
        assert {"Doc", "Seconds", "Value", "Named", "Either"} <= set(schemas)
        assert "Unused" not in schemas

    def test_primitive_aliases_are_not_mapped(self, tmp_path: Path, commons: list[Path]):
        _, mapped = bundle_spec(_spec(tmp_path), tmp_path / "out", commons)
        assert mapped == {"Doc", "Seconds", "Value", "Either"}

    def test_nested_inline_objects_of_mapped_schemas_are_hollowed(
        self, tmp_path: Path, commons: list[Path],
    ):
        bundled, _ = bundle_spec(_spec(tmp_path), tmp_path / "out", commons)
        schemas = load_yaml(bundled)["components"]["schemas"]
        # The oneOf shape is kept, but its inline object no longer has
        # properties the generator could turn into a helper class.
        assert schemas["Either"]["oneOf"] == [{"type": "number"}, {"type": "object"}]
        assert schemas["Seconds"]["allOf"][0] == {"$ref": "#/components/schemas/Value"}
        assert schemas["Seconds"]["allOf"][1] == {"type": "object"}
        # Top-level properties stay intact.
        assert "value" in schemas["Value"]["properties"]

    def test_nested_inline_unions_of_mapped_schemas_are_hollowed(self, tmp_path: Path):
        common = _write(tmp_path / "common.yaml", {
            "Component": {"type": "object", "properties": {
                "fill": {"anyOf": [{"type": "string"}, {"type": "number"}]},
                "unit": {"type": "string"},
            }},
        })
        spec = _write(tmp_path / "gc.yaml", {
            "Root": {"type": "object", "properties": {"c": {"$ref": "./common.yaml#/components/schemas/Component"}}},
        })
        bundled, mapped = bundle_spec(spec, tmp_path / "out", [common])
        component = load_yaml(bundled)["components"]["schemas"]["Component"]
        assert mapped == {"Component"}
        assert component["properties"] == {"fill": {"type": "object"}, "unit": {"type": "string"}}

    def test_commons_name_clash_is_an_error(self, tmp_path: Path, commons: list[Path]):
        spec = _write(tmp_path / "gc.yaml", {"Doc": {"type": "object"}})
        with pytest.raises(SystemExit):
            bundle_spec(spec, tmp_path / "out", commons)

    def test_source_spec_is_not_modified(self, tmp_path: Path, commons: list[Path]):
        spec = _spec(tmp_path)
        before = spec.read_text(encoding="utf-8")
        bundle_spec(spec, tmp_path / "out", commons)
        assert spec.read_text(encoding="utf-8") == before

    @pytest.mark.parametrize("spec", sorted(SPECS))
    def test_real_specs_map_only_class_producing_commons(self, spec: str, tmp_path: Path):
        _, mapped = bundle_spec(SPECS[spec], tmp_path)
        commons = merged_commons_schemas()
        assert mapped
        assert all(generates_model(commons[name]) for name in mapped)
        assert "CoreTNamed" not in mapped  # string alias: no commons class


class TestGeneratesModel:
    @pytest.mark.parametrize("schema", [
        {"type": "object", "properties": {"a": {"type": "string"}}},
        {"oneOf": [{"type": "number"}, {"type": "string"}]},
        {"allOf": [{"$ref": "#/components/schemas/X"}]},
        {"type": "string", "enum": ["a"]},
        {"type": "object"},
    ])
    def test_models(self, schema: dict):
        assert generates_model(schema)

    @pytest.mark.parametrize("schema", [
        {"type": "string"},
        {"type": "number", "format": "double"},
        {"type": ["integer", "null"]},
        {"type": "array", "items": {"type": "string"}},
    ])
    def test_aliases(self, schema: dict):
        assert not generates_model(schema)


class TestNanCapableProperties:
    def test_direct_and_inherited(self, commons: list[Path]):
        result = nan_capable_properties(merged_commons_schemas(commons))
        assert result == {"Value": ["value"], "Seconds": ["value"]}

    def test_real_commons_quantity_values(self):
        result = nan_capable_properties(merged_commons_schemas())
        assert result["QuantityValue"] == ["value"]
        assert result["SecondsQuantityValue"] == ["value"]
        assert all(name.endswith("QuantityValue") for name in result)
