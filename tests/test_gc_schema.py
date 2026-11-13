"""Regression checks for the GC REC/2026/09 datacube schema shape."""

from __future__ import annotations

from pathlib import Path

from allotrope_gen.schema import load_yaml


RESOURCES = Path(__file__).parents[1] / "src" / "main" / "resources"


def test_gc_chromatogram_cube_property_names_match_asm() -> None:
    """Keep GC datacube names aligned with the sample and shared ASM model."""
    schemas = load_yaml(RESOURCES / "gc.yaml")["components"]["schemas"]

    cube = schemas["ChromatogramDataCube"]["properties"]
    assert set(cube) == {"cube-structure", "data", "label"}
    assert cube["cube-structure"]["$ref"] == (
        "#/components/schemas/ChromatogramDatacubeStructure"
    )
    assert cube["data"]["$ref"] == "#/components/schemas/ChromatogramData"

    structure = schemas["ChromatogramDatacubeStructure"]["properties"]
    assert set(structure) == {"dimensions", "measures"}

    assert schemas["ChromatogramDataCube"]["required"] == ["cube-structure", "data"]
    assert schemas["ChromatogramData"]["required"] == ["dimensions", "measures"]


def test_gc_chromatogram_components_stay_flat_and_understandable() -> None:
    """Avoid unions and compositions that generate anonymous GC component types."""
    schemas = load_yaml(RESOURCES / "gc.yaml")["components"]["schemas"]

    dimension = schemas["ChromatogramDimension"]
    assert not {"oneOf", "anyOf", "allOf"} & dimension.keys()
    assert dimension["properties"]["@componentDatatype"]["enum"] == ["double"]
    assert dimension["properties"]["concept"]["enum"] == [
        "retention time",
        "retention volume",
    ]
    assert dimension["properties"]["unit"]["enum"] == ["s", "mL"]

    measure = schemas["ChromatogramMeasure"]
    assert not {"oneOf", "anyOf", "allOf"} & measure.keys()
    assert measure["properties"]["@componentDatatype"]["enum"] == ["double"]

    data_schema = schemas["ChromatogramData"]
    assert not {"oneOf", "anyOf", "allOf"} & data_schema.keys()

    # Check nested array schemas too: no union should silently reintroduce
    # generator-created helper models below these named components.
    for name in (
        "ChromatogramDataCube",
        "ChromatogramData",
        "ChromatogramDatacubeStructure",
        "ChromatogramDimension",
        "ChromatogramMeasure",
    ):
        assert not _composition_keys(schemas[name])


def test_core_custom_information_document_has_no_union_branches() -> None:
    """Keep shared custom-information models free of generated oneOf wrappers."""
    schemas = load_yaml(RESOURCES / "core.yaml")["components"]["schemas"]
    document = schemas["CoreCustomInformationDocument"]

    assert not _composition_keys(document)
    assert document["required"] == ["datum label"]
    assert {
        "scalar double datum",
        "unit",
        "scalar string datum",
        "scalar timestamp datum",
        "scalar boolean datum",
    } <= document["properties"].keys()
    assert document["properties"]["scalar double datum"] == {
        "type": "number",
        "format": "double",
    }
    assert document["properties"]["scalar string datum"] == {"type": "string"}
    assert document["properties"]["scalar timestamp datum"] == {
        "type": "string",
        "format": "date-time",
    }
    assert document["properties"]["scalar boolean datum"] == {"type": "boolean"}


def _composition_keys(node: object) -> set[str]:
    """Return composition keywords found anywhere in a schema subtree."""
    if isinstance(node, dict):
        keys = {key for key in ("oneOf", "anyOf", "allOf") if key in node}
        for value in node.values():
            keys.update(_composition_keys(value))
        return keys
    if isinstance(node, list):
        keys: set[str] = set()
        for value in node:
            keys.update(_composition_keys(value))
        return keys
    return set()
