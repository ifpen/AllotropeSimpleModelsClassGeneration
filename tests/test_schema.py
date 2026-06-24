"""Tests for :mod:`allotrope_gen.schema`."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from allotrope_gen.schema import (
    collect_common_schemas,
    load_yaml,
    merged_commons_yaml,
    schema_names,
    schemas_referenced_from_commons,
)


# ---------------------------------------------------------------------------
# load_yaml
# ---------------------------------------------------------------------------


class TestLoadYaml:
    def test_returns_dict(self, tmp_path: Path):
        p = tmp_path / "test.yaml"
        p.write_text("key: value\n", encoding="utf-8")
        result = load_yaml(p)
        assert result == {"key": "value"}

    def test_unicode_preserved(self, tmp_path: Path):
        p = tmp_path / "test.yaml"
        p.write_text("unit: µm\n", encoding="utf-8")
        result = load_yaml(p)
        assert result["unit"] == "µm"


# ---------------------------------------------------------------------------
# schema_names
# ---------------------------------------------------------------------------


class TestSchemaNames:
    def test_returns_set_of_names(self):
        doc = {"components": {"schemas": {"Foo": {}, "Bar": {}}}}
        assert schema_names(doc) == {"Foo", "Bar"}

    def test_empty_when_no_schemas(self):
        assert schema_names({}) == set()
        assert schema_names({"components": {}}) == set()

    def test_empty_schemas_block(self):
        assert schema_names({"components": {"schemas": {}}}) == set()


# ---------------------------------------------------------------------------
# collect_common_schemas
# ---------------------------------------------------------------------------


class TestCollectCommonSchemas:
    def test_collects_from_multiple_files(self, common_yaml: Path, datacube_yaml: Path):
        names = collect_common_schemas([common_yaml, datacube_yaml])
        assert "Foo" in names
        assert "Bar" in names
        assert "Cube" in names

    def test_missing_file_is_skipped(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.yaml"
        names = collect_common_schemas([missing])
        assert names == set()

    def test_single_file(self, common_yaml: Path):
        names = collect_common_schemas([common_yaml])
        assert names == {"Foo", "Bar"}


# ---------------------------------------------------------------------------
# schemas_referenced_from_commons
# ---------------------------------------------------------------------------


class TestSchemasReferencedFromCommons:
    def test_returns_only_referenced_names(
        self, spec_yaml: Path, common_yaml: Path, datacube_yaml: Path
    ):
        # spec_yaml refs Foo from common.yaml; Bar and Cube are not referenced
        referenced = schemas_referenced_from_commons(
            spec_yaml, [common_yaml, datacube_yaml]
        )
        assert referenced == {"Foo"}

    def test_missing_spec_returns_empty(self, tmp_path: Path, common_yaml: Path):
        missing = tmp_path / "no_such_spec.yaml"
        assert schemas_referenced_from_commons(missing, [common_yaml]) == set()

    def test_no_refs_returns_empty(self, tmp_path: Path, common_yaml: Path):
        spec = tmp_path / "spec_no_refs.yaml"
        spec.write_text(
            "openapi: '3.1.0'\ninfo:\n  title: T\n  version: '0'\n"
            "components:\n  schemas:\n    Local: {type: object}\n",
            encoding="utf-8",
        )
        assert schemas_referenced_from_commons(spec, [common_yaml]) == set()

    def test_refs_not_in_commons_are_excluded(self, tmp_path: Path, common_yaml: Path):
        # Ref to a schema that does not exist in common_yaml
        spec = tmp_path / "spec_phantom.yaml"
        spec.write_text(
            "openapi: '3.1.0'\ninfo:\n  title: T\n  version: '0'\n"
            "components:\n  schemas:\n    M:\n      $ref: "
            "'./common.yaml#/components/schemas/Phantom'\n",
            encoding="utf-8",
        )
        result = schemas_referenced_from_commons(spec, [common_yaml])
        assert "Phantom" not in result

    def test_datacube_refs_matched(self, tmp_path: Path, datacube_yaml: Path):
        spec = tmp_path / "spec_dc.yaml"
        spec.write_text(
            "openapi: '3.1.0'\ninfo:\n  title: T\n  version: '0'\n"
            "components:\n  schemas:\n    M:\n      $ref: "
            "'./datacube.yaml#/components/schemas/Cube'\n",
            encoding="utf-8",
        )
        result = schemas_referenced_from_commons(spec, [datacube_yaml])
        assert result == {"Cube"}


# ---------------------------------------------------------------------------
# merged_commons_yaml
# ---------------------------------------------------------------------------


class TestMergedCommonsYaml:
    def test_creates_merged_file(
        self, tmp_path: Path, common_yaml: Path, datacube_yaml: Path
    ):
        out = merged_commons_yaml(tmp_path, [common_yaml, datacube_yaml])
        assert out.exists()
        assert out.name == "commons-merged.yaml"

    def test_merged_contains_all_schemas(
        self, tmp_path: Path, common_yaml: Path, datacube_yaml: Path
    ):
        out = merged_commons_yaml(tmp_path, [common_yaml, datacube_yaml])
        doc = load_yaml(out)
        names = schema_names(doc)
        assert {"Foo", "Bar", "Cube"}.issubset(names)

    def test_identical_duplicate_is_silently_merged(self, tmp_path: Path):
        """The same schema definition in two files should not raise."""
        shared_schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        file_a = tmp_path / "a.yaml"
        file_b = tmp_path / "b.yaml"
        for f in (file_a, file_b):
            f.write_text(
                yaml.dump({
                    "openapi": "3.1.0",
                    "info": {"title": "T", "version": "0"},
                    "components": {"schemas": {"Shared": shared_schema}},
                }),
                encoding="utf-8",
            )
        out = merged_commons_yaml(tmp_path, [file_a, file_b])
        doc = load_yaml(out)
        assert "Shared" in schema_names(doc)

    def test_schema_collision_exits(self, tmp_path: Path):
        """Different definitions for the same name must cause SystemExit."""
        file_a = tmp_path / "a.yaml"
        file_b = tmp_path / "b.yaml"
        file_a.write_text(
            yaml.dump({
                "openapi": "3.1.0",
                "info": {"title": "T", "version": "0"},
                "components": {"schemas": {"Conflict": {"type": "string"}}},
            }),
            encoding="utf-8",
        )
        file_b.write_text(
            yaml.dump({
                "openapi": "3.1.0",
                "info": {"title": "T", "version": "0"},
                "components": {"schemas": {"Conflict": {"type": "integer"}}},
            }),
            encoding="utf-8",
        )
        with pytest.raises(SystemExit):
            merged_commons_yaml(tmp_path, [file_a, file_b])

    def test_missing_file_skipped(self, tmp_path: Path, common_yaml: Path):
        missing = tmp_path / "nonexistent.yaml"
        out = merged_commons_yaml(tmp_path, [common_yaml, missing])
        doc = load_yaml(out)
        assert "Foo" in schema_names(doc)

    def test_output_is_valid_openapi(
        self, tmp_path: Path, common_yaml: Path, datacube_yaml: Path
    ):
        out = merged_commons_yaml(tmp_path, [common_yaml, datacube_yaml])
        doc = load_yaml(out)
        assert doc["openapi"] == "3.1.0"
        assert "info" in doc
        assert "components" in doc
