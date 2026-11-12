"""Regression tests for LC root-reachable schema coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from allotrope_gen.config import SPECS
from allotrope_gen.schema import load_yaml


RESOURCES = SPECS["hplc"].parent
OFFICIAL_SCHEMA = RESOURCES / "_official_lc_schema_reference.json"
SAMPLE_PATH = Path.home() / "AppData" / "Local" / "Temp" / "liquid-chromatography.sample.json"


def _schema_paths(
    node: object,
    path: tuple[str, ...] = (),
    schemas: dict | None = None,
    seen_refs: frozenset[str] = frozenset(),
) -> set[tuple[str, ...]]:
    """Collect property paths, following local component refs in context."""
    found: set[tuple[str, ...]] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if (
            schemas is not None
            and isinstance(ref, str)
            and ref.startswith("#/components/schemas/")
            and ref not in seen_refs
        ):
            target = schemas.get(ref.rsplit("/", 1)[-1])
            if target is not None:
                found.update(
                    _schema_paths(target, path, schemas, seen_refs | {ref})
                )
        for name, child in node.get("properties", {}).items():
            child_path = (*path, name)
            found.add(child_path)
            found.update(_schema_paths(child, child_path, schemas, seen_refs))
        for key in ("items", "allOf", "anyOf", "oneOf", "contains"):
            if key in node:
                found.update(_schema_paths(node[key], path, schemas, seen_refs))
    elif isinstance(node, list):
        for child in node:
            found.update(_schema_paths(child, path, schemas, seen_refs))
    return found


def _reachable_local_schemas(root: str, schemas: dict) -> set[str]:
    """Return component schemas reachable from a named root component."""
    reachable: set[str] = set()
    pending = [root]
    while pending:
        name = pending.pop()
        if name in reachable or name not in schemas:
            continue
        reachable.add(name)

        def visit(node: object) -> None:
            if isinstance(node, dict):
                ref = node.get("$ref")
                if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                    target = ref.rsplit("/", 1)[-1]
                    if target not in reachable:
                        pending.append(target)
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)

        visit(schemas[name])
    return reachable


def _reference_store(official: dict) -> dict:
    store = dict(official.get("$defs", {}))
    for document in list(store.values()):
        if isinstance(document, dict) and isinstance(document.get("$id"), str):
            store[document["$id"]] = document
    return store


def _validate_official(document: dict, official: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    resolver = jsonschema.RefResolver.from_schema(official, store=_reference_store(official))
    validator = jsonschema.Draft202012Validator(official, resolver=resolver)
    errors = list(validator.iter_errors(document))
    assert not errors, "\n".join(
        f"{list(error.absolute_path)}: {error.message}" for error in errors[:10]
    )


def _small_full_lc_document() -> dict:
    """A small valid LC instance exercising the complete root hierarchy."""
    return {
        "$asm.manifest": (
            "http://purl.allotrope.org/manifests/liquid-chromatography/REC/2026/09/"
            "liquid-chromatography.manifest"
        ),
        "liquid chromatography aggregate document": {
            "device system document": {
                "asset management identifier": "system-1",
                "brand name": "Acme",
                "description": "LC instrument",
                "device document": [
                    {
                        "@index": 1,
                        "device type": "liquid chromatograph",
                        "device identifier": "pump-1",
                        "model number": "P-100",
                    }
                ],
                "device identifier": "lc-1",
                "equipment serial number": "serial-1",
                "firmware version": "1.0",
                "model number": "LC-100",
                "product manufacturer": "Acme",
                "detector model number": "D-200",
                "pump model number": "P-100",
            },
            "liquid chromatography document": [
                {
                    "analyst": "analyst-1",
                    "measurement aggregate document": {
                        "measurement document": [
                            {
                                "chromatogram data cube": {
                                    "cube-structure": {
                                        "dimensions": [
                                            {
                                                "@componentDatatype": "double",
                                                "concept": "retention time",
                                                "unit": "s",
                                            }
                                        ],
                                        "measures": [
                                            {
                                                "@componentDatatype": "double",
                                                "concept": "absorbance",
                                                "unit": "mAU",
                                            }
                                        ],
                                    },
                                    "data": {
                                        "dimensions": [[0.0, 1.0]],
                                        "measures": [[0.2, 0.8]],
                                    },
                                },
                                "chromatography column document": {
                                    "chromatography column serial number": "column-1"
                                },
                                "sample document": {"sample identifier": "sample-1"},
                                "device control aggregate document": {
                                    "device control document": [
                                        {"@index": 1, "device type": "detector"}
                                    ]
                                },
                            }
                        ]
                    },
                }
            ]
        },
    }


def test_official_reference_is_pinned_and_full_sample_is_valid():
    """Keep a local canonical schema copy so LC fixtures stay reproducible."""
    assert OFFICIAL_SCHEMA.is_file()
    official = json.loads(OFFICIAL_SCHEMA.read_text(encoding="utf-8"))
    assert official["$id"].endswith("/liquid-chromatography.tabular.embed.schema")
    assert "/REC/2026/09/" in official["$id"]

    if SAMPLE_PATH.is_file():
        sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
        _validate_official(sample, official)


def test_full_root_hierarchy_document_validates_against_official_schema():
    official = json.loads(OFFICIAL_SCHEMA.read_text(encoding="utf-8"))
    _validate_official(_small_full_lc_document(), official)


def test_hplc_schema_has_no_all_of_compositions():
    spec = load_yaml(SPECS["hplc"])

    def find_all_of(node: object, path: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
        found = []
        if isinstance(node, dict):
            if "allOf" in node:
                found.append(path)
            for key, child in node.items():
                found.extend(find_all_of(child, (*path, str(key))))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                found.extend(find_all_of(child, (*path, str(index))))
        return found

    assert find_all_of(spec) == []


def test_hplc_core_components_are_root_reachable():
    schemas = load_yaml(SPECS["hplc"])["components"]["schemas"]
    reachable = _reachable_local_schemas("liquidChromatographySimpleModel", schemas)
    assert set(schemas) == reachable


def test_hplc_uses_shared_unit_quantity_schemas_when_available():
    spec = load_yaml(SPECS["hplc"])
    schemas = spec["components"]["schemas"]
    common_names = {
        "SecondsQuantityValue",
        "MicrolitersQuantityValue",
        "HertzQuantityValue",
        "UnitlessQuantityValue",
        "PercentQuantityValue",
        "MillimetersQuantityValue",
    }
    refs: dict[str, int] = {}

    def visit(node: object) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                name = ref.rsplit("/", 1)[-1]
                if ref.startswith("./common.yaml#/components/schemas/") and name in common_names:
                    refs[name] = refs.get(name, 0) + 1
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(schemas)
    assert set(refs) == common_names
    assert all(count > 0 for count in refs.values())
    assert "QudtS" not in schemas
    assert "QudtL" not in schemas


def test_hplc_cubes_use_shared_datacube_without_local_shape_or_unit_wrappers():
    spec = load_yaml(SPECS["hplc"])
    schemas = spec["components"]["schemas"]
    shared_cube_ref = "./datacube.yaml#/components/schemas/AsmDatacube"
    cube_properties = {
        "chromatogram data cube",
        "mass chromatogram data cube",
        "mass spectrum data cube",
        "three-dimensional mass spectrum data cube",
        "three-dimensional ultraviolet spectrum data cube",
        "absorption spectrum data cube",
        "transmittance spectrum data cube",
        "fluorescence emission profile data cube",
        "fluorescence emission spectrum data cube",
        "fluorescence excitation spectrum data cube",
    }
    found_cubes: list[dict] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            for name, value in node.items():
                if name in cube_properties and isinstance(value, dict):
                    found_cubes.append(value)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(schemas)
    assert len(found_cubes) == len(cube_properties)
    assert all(cube.get("$ref") == shared_cube_ref for cube in found_cubes)
    assert all(set(cube) <= {"$ref", "deprecated"} for cube in found_cubes)
    assert not any(
        name.startswith("LiquidChromatography")
        and name.endswith(("Dimension", "Measure", "DataCube"))
        for name in schemas
    )
    assert not any("cube-structure" in line for line in SPECS["hplc"].read_text(encoding="utf-8").splitlines())


def test_hplc_projection_includes_official_lc_root_property_paths():
    official = json.loads(OFFICIAL_SCHEMA.read_text(encoding="utf-8"))
    spec = load_yaml(SPECS["hplc"])
    schemas = spec["components"]["schemas"]

    generated_paths = _schema_paths(
        schemas["liquidChromatographySimpleModel"], schemas=schemas
    )

    # Flattened hierarchy and measurement fields remain directly reachable.
    expected_device = {
        "asset management identifier",
        "brand name",
        "description",
        "device document",
        "device identifier",
        "equipment serial number",
        "firmware version",
        "model number",
        "product manufacturer",
        "detector model number",
        "pump model number",
    }
    generated_device = schemas["liquidChromatographySimpleModel"]["properties"][
        "liquid chromatography aggregate document"
    ]["properties"]["device system document"]["properties"]
    assert expected_device <= generated_device.keys()

    official_device = official["$defs"][
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2026/09/hierarchy.schema"
    ]["$defs"]["techniqueAggregateDocument"]["properties"]["device system document"][
        "properties"
    ]
    assert {
        "asset management identifier",
        "brand name",
        "description",
        "device document",
        "device identifier",
        "equipment serial number",
        "firmware version",
        "model number",
        "product manufacturer",
    } <= official_device.keys()

    assert any(
        path[-2:] == ("sample document", "sample preparation description")
        for path in generated_paths
    )
    root = schemas["liquidChromatographySimpleModel"]
    assert root["properties"]["$asm.manifest"]["$ref"] == (
        "./common.yaml#/components/schemas/AsmManifest"
    )
    lc_item = root["properties"]["liquid chromatography aggregate document"][
        "properties"
    ]["liquid chromatography document"]["items"]
    assert "measurement aggregate document" in lc_item["properties"]
    assert "fraction aggregate document" in lc_item["properties"]
    assert "measurement aggregate document" in lc_item["required"]
    measurement_aggregate = schemas["measurementAggregateDocument"]
    assert lc_item["properties"]["measurement aggregate document"]["$ref"] == (
        "#/components/schemas/measurementAggregateDocument"
    )
    assert measurement_aggregate["required"] == ["measurement document"]
    measurement_array = measurement_aggregate["properties"]["measurement document"]
    assert measurement_array["type"] == "array"
    assert measurement_array["minItems"] == 1
    assert measurement_array["items"]["$ref"] == (
        "#/components/schemas/LiquidChromatographyMeasurementDocument"
    )
    assert "LiquidChromatographyMeasurementAggregateDocument" not in schemas

    measurement_item = schemas["LiquidChromatographyMeasurementDocument"]
    assert "device control aggregate document" in measurement_item["required"]
    assert "chromatography column document" in measurement_item["required"]
    sample_document = measurement_item["properties"]["sample document"]
    assert sample_document["properties"]["sample identifier"] == {
        "type": "string",
        "description": (
            "Sample id is a measurement metadata that identifies a sample being measured."
        ),
    }
    assert "sample identifier" in sample_document["required"]
    assert "chromatogram data cube" in measurement_item["properties"]
    cube = measurement_item["properties"]["chromatogram data cube"]
    assert cube["$ref"] == "./datacube.yaml#/components/schemas/AsmDatacube"
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
    } <= measurement_item["properties"].keys()
    assert "chromatography column document" in measurement_item["properties"]
    assert "injection document" in measurement_item["properties"]
    particle_size = measurement_item["properties"]["chromatography column document"][
        "properties"
    ]["chromatography column particle size"]
    assert particle_size["$ref"] == (
        "./common.yaml#/components/schemas/MicrometersQuantityValue"
    )
    peak_properties = (
        measurement_item["properties"]["processed data aggregate document"][
            "properties"
        ]["processed data document"]["items"]["properties"]["peak list"][
            "properties"
        ]["peak"]["items"]["properties"]
    )
    assert peak_properties["peak area"]["$ref"] == (
        "./common.yaml#/components/schemas/QuantityValue"
    )
    assert peak_properties["peak height"]["$ref"] == (
        "./common.yaml#/components/schemas/QuantityValue"
    )
    assert any(
        path[-2:] == ("fraction aggregate document", "fraction document")
        for path in generated_paths
    )
    assert any(
        path[-4:]
        == (
            "fraction document",
            "location aggregate document",
            "location document",
            "location identifier",
        )
        for path in generated_paths
    )
    assert any(path[-2:] == ("peak list", "peak") for path in generated_paths)
    assert any(path[-2:] == ("peak", "peak start") for path in generated_paths)
    assert any(path[-2:] == ("peak", "peak end") for path in generated_paths)
