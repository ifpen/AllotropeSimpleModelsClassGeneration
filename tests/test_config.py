"""Tests for :mod:`allotrope_gen.config`."""

from __future__ import annotations

import pytest

from allotrope_gen.config import (
    LANGUAGES,
    SPECS,
    LanguageConfig,
    csharp_namespace,
    java_package,
    npm_package,
    python_package,
    to_pascal,
)


# ---------------------------------------------------------------------------
# to_pascal
# ---------------------------------------------------------------------------


class TestToPascal:
    def test_single_word(self):
        assert to_pascal("gc") == "Gc"

    def test_already_capitalised(self):
        assert to_pascal("Gc") == "Gc"

    def test_acronym(self):
        assert to_pascal("hplc") == "Hplc"

    def test_empty_string(self):
        assert to_pascal("") == ""

    def test_all_caps_unchanged_after_first(self):
        # capitalize() lowercases the rest — that is intentional for this helper
        assert to_pascal("GC") == "Gc"


# ---------------------------------------------------------------------------
# Package naming helpers
# ---------------------------------------------------------------------------


class TestJavaPackage:
    def test_with_spec(self):
        assert java_package("gc") == "fr.ifpen.allotropeconverters.allotrope_models.gc"

    def test_commons(self):
        assert java_package("") == "fr.ifpen.allotropeconverters.allotrope_models"

    def test_new_spec_appended(self):
        assert java_package("hplc").endswith(".hplc")


class TestCsharpNamespace:
    def test_with_spec(self):
        assert csharp_namespace("gc") == "IFPEN.AllotropeConverters.AllotropeModels.Gc"

    def test_commons(self):
        assert csharp_namespace("") == "IFPEN.AllotropeConverters.AllotropeModels"

    def test_pascal_applied(self):
        # The spec key is Pascal-cased in the C# namespace
        assert csharp_namespace("hplc") == "IFPEN.AllotropeConverters.AllotropeModels.Hplc"


class TestPythonPackage:
    def test_with_spec(self):
        assert python_package("gc") == "ifpen.allotrope_models.gc"

    def test_commons(self):
        assert python_package("") == "ifpen.allotrope_models"


class TestNpmPackage:
    def test_with_spec(self):
        assert npm_package("gc") == "@ifpen/allotrope-models-gc"

    def test_commons(self):
        assert npm_package("") == "@ifpen/allotrope-models-commons"

    def test_scoped(self):
        assert npm_package("hplc").startswith("@ifpen/")


# ---------------------------------------------------------------------------
# LanguageConfig dataclass
# ---------------------------------------------------------------------------


class TestLanguageConfig:
    def test_all_languages_registered(self):
        expected = {"java", "typescript-angular", "csharp", "python"}
        assert set(LANGUAGES.keys()) == expected

    @pytest.mark.parametrize("lang", list(LANGUAGES))
    def test_required_fields_present(self, lang: str):
        cfg = LANGUAGES[lang]
        assert cfg.generator, f"{lang}: generator must be non-empty"
        assert cfg.output_subdir, f"{lang}: output_subdir must be non-empty"
        assert cfg.package_key, f"{lang}: package_key must be non-empty"
        assert cfg.commons_package, f"{lang}: commons_package must be non-empty"
        assert cfg.import_pattern, f"{lang}: import_pattern must be non-empty"
        assert isinstance(cfg.extra_props, dict)
        assert isinstance(cfg.extra_opts, list)

    @pytest.mark.parametrize("lang", list(LANGUAGES))
    def test_package_fn_returns_string(self, lang: str):
        cfg = LANGUAGES[lang]
        result = cfg.package_fn("gc")
        assert isinstance(result, str) and result

    @pytest.mark.parametrize("lang", list(LANGUAGES))
    def test_commons_package_fn_returns_string(self, lang: str):
        cfg = LANGUAGES[lang]
        result = cfg.package_fn("")
        assert isinstance(result, str) and result

    def test_extra_opts_are_list(self):
        for lang, cfg in LANGUAGES.items():
            assert isinstance(cfg.extra_opts, list), lang

    def test_skip_validate_spec_present_everywhere(self):
        """All languages should suppress strict validation (ASM schemas use
        non-standard features that the bundled validator rejects)."""
        for lang, cfg in LANGUAGES.items():
            assert "--skip-validate-spec" in cfg.extra_opts, (
                f"{lang}: missing --skip-validate-spec in extra_opts"
            )


# ---------------------------------------------------------------------------
# SPECS registry
# ---------------------------------------------------------------------------


class TestSpecs:
    def test_gc_registered(self):
        assert "gc" in SPECS

    def test_hplc_registered(self):
        assert "hplc" in SPECS
        assert SPECS["hplc"].name == "hplc.yaml"
        assert SPECS["hplc"].is_file()

    def test_hplc_manifest_and_lc_root_reachable_fields(self):
        from allotrope_gen.schema import load_yaml, schemas_referenced_from_commons

        schemas = load_yaml(SPECS["hplc"])["components"]["schemas"]
        root = schemas["liquidChromatographySimpleModel"]
        assert root["required"] == ["$asm.manifest"]
        assert root["properties"]["$asm.manifest"]["type"] == "string"
        assert root["properties"]["$asm.manifest"]["default"].endswith(
            "/liquid-chromatography.manifest"
        )

        commons = schemas_referenced_from_commons(SPECS["hplc"])
        assert {
            "AsmDatacube",
            "DateTimeValue", "QuantityValue",
        } <= commons
        assert "StringValue" not in commons

        assert LANGUAGES["java"].import_pattern.format(
            class_name="QuantityValue",
            commons_package=LANGUAGES["java"].commons_package,
        ) == "QuantityValue=fr.ifpen.allotropeconverters.allotrope_models.QuantityValue"
        assert LANGUAGES["typescript-angular"].import_pattern.format(
            class_name="QuantityValue",
            commons_package=LANGUAGES["typescript-angular"].commons_package,
        ) == "QuantityValue=@ifpen/allotrope-models-commons"
        assert LANGUAGES["csharp"].import_pattern.format(
            class_name="QuantityValue",
            commons_package=LANGUAGES["csharp"].commons_package,
        ) == "QuantityValue=IFPEN.AllotropeConverters.AllotropeModels.Model.QuantityValue"

        technique_ref = root["properties"]["liquid chromatography aggregate document"]["$ref"]
        assert technique_ref == "#/components/schemas/liquidChromatographyAggregateDocument"
        technique = schemas[technique_ref.rsplit("/", 1)[-1]]
        device_system_ref = technique["properties"]["device system document"]["$ref"]
        assert device_system_ref == "#/components/schemas/deviceSystemDocument"
        device_system = schemas[device_system_ref.rsplit("/", 1)[-1]]["properties"]
        assert {
            "asset management identifier", "brand name", "custom information aggregate document",
            "description", "device document", "device identifier", "equipment serial number",
            "firmware version", "model number", "product manufacturer", "detector model number",
            "pump model number",
        } <= device_system.keys()

        aggregate = schemas[
            root["properties"]["liquid chromatography aggregate document"]["$ref"].rsplit("/", 1)[-1]
        ]
        assert "liquid chromatography document" in aggregate["properties"]
        assert "liquid chromatography document" in aggregate["required"]
        lc_item = aggregate["properties"]["liquid chromatography document"]["items"]
        assert lc_item["$ref"] == "#/components/schemas/liquidChromatographyDocument"
        lc_document = schemas["liquidChromatographyDocument"]
        assert "measurement aggregate document" in lc_document["properties"]
        assert "fraction aggregate document" in lc_document["properties"]
        assert "measurement aggregate document" in lc_document["required"]

        measurement_aggregate = schemas["measurementAggregateDocument"]
        assert lc_document["properties"]["measurement aggregate document"]["$ref"] == (
            "#/components/schemas/measurementAggregateDocument"
        )
        assert measurement_aggregate["type"] == "object"
        assert measurement_aggregate["required"] == ["measurement document"]
        measurement = measurement_aggregate["properties"]["measurement document"]
        assert measurement["minItems"] == 1
        assert measurement["items"]["$ref"] == (
            "#/components/schemas/LiquidChromatographyMeasurementDocument"
        )
        assert {
            "analytical method identifier",
            "calculated data aggregate document",
            "custom information aggregate document",
            "diagnostic trace aggregate document",
            "error aggregate document",
            "experimental data identifier",
            "image aggregate document",
            "method version",
            "processed data aggregate document",
            "statistics aggregate document",
        } <= measurement_aggregate["properties"].keys()

        # Like GC, HPLC has a named measurement item with fields declared
        # directly on the item rather than hidden in a root-level overlay.
        measurement_item = schemas["LiquidChromatographyMeasurementDocument"]
        measurement_properties = measurement_item["properties"]
        sample_ref = measurement_properties["sample document"]["$ref"]
        assert sample_ref == "#/components/schemas/SampleDocument"
        sample_document = schemas[sample_ref.rsplit("/", 1)[-1]]
        assert sample_document["properties"]["sample identifier"] == {
            "type": "string",
            "description": (
                "Sample id is a measurement metadata that identifies a sample being measured."
            ),
        }
        assert "sample identifier" in sample_document["required"]
        assert "chromatogram data cube" in measurement_properties
        assert "chromatography column document" in measurement_properties
        assert "injection document" in measurement_properties
        assert "device control aggregate document" in measurement_properties
        assert "processed data aggregate document" in measurement_properties
        cube_ref = "./datacube.yaml#/components/schemas/AsmDatacube"
        assert measurement_properties["chromatogram data cube"]["$ref"] == cube_ref
        assert "LiquidChromatographyChromatogramDataCube" not in schemas
        assert not any(
            name.startswith("LiquidChromatography")
            and name.endswith(("Dimension", "Measure", "DataCube"))
            for name in schemas
        )
        assert "device control aggregate document" in measurement_item["required"]
        assert "chromatography column document" in measurement_item["required"]
        assert not {"anyOf", "oneOf", "allOf"} & measurement_item.keys()
        assert {
            "chromatogram data cube",
            "three-dimensional ultraviolet spectrum data cube",
            "absorption spectrum data cube",
            "transmittance spectrum data cube",
            "fluorescence emission profile data cube",
            "fluorescence emission spectrum data cube",
            "fluorescence excitation spectrum data cube",
            "mass chromatogram data cube",
            "mass spectrum data cube",
            "three-dimensional mass spectrum data cube",
        } <= measurement_properties.keys()
        column_ref = measurement_properties["chromatography column document"]["$ref"]
        column = schemas[column_ref.rsplit("/", 1)[-1]]
        assert column["properties"]["chromatography column particle size"]["$ref"] == (
            "./common.yaml#/components/schemas/MicrometersQuantityValue"
        )
        assert not any(
            name.endswith("MeasurementDocumentItems")
            or name.startswith("ChromatographyREC202609")
            for name in schemas
        )

    def test_hplc_refs_are_resolvable(self):
        from allotrope_gen.schema import load_yaml

        spec = load_yaml(SPECS["hplc"])
        schemas = spec["components"]["schemas"]
        refs: set[str] = set()

        def visit(node):
            if isinstance(node, dict):
                ref = node.get("$ref")
                if isinstance(ref, str):
                    refs.add(ref)
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)

        visit(spec)
        local_names = set(schemas)
        assert not {
            ref for ref in refs
            if ref.startswith("#/components/schemas/") and ref.rsplit("/", 1)[-1] not in local_names
        }
        assert not {ref for ref in refs if "http://" in ref or "https://" in ref}

        commons = {}
        for filename in ("common.yaml", "datacube.yaml"):
            commons.update(load_yaml(SPECS["hplc"].with_name(filename))["components"]["schemas"])
        assert not {
            ref for ref in refs
            if ref.startswith(("./common.yaml#/", "./datacube.yaml#/"))
            and ref.rsplit("/", 1)[-1] not in commons
        }

    def test_all_values_are_paths(self):
        from pathlib import Path
        for key, path in SPECS.items():
            assert isinstance(path, Path), f"SPECS['{key}'] is not a Path"
