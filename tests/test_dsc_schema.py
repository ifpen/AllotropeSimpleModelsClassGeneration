"""Regression checks for the DSC REC/2026/09 model shape."""

from __future__ import annotations

from pathlib import Path

from allotrope_gen.schema import load_yaml


RESOURCES = Path(__file__).parents[1] / "src" / "main" / "resources"
DSC_SCHEMA = RESOURCES / "dsc.yaml"


def _local_references(node: object) -> set[str]:
    """Return local component names referenced in a schema subtree."""
    found: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            found.add(ref.rsplit("/", 1)[-1])
        for child in node.values():
            found.update(_local_references(child))
    elif isinstance(node, list):
        for child in node:
            found.update(_local_references(child))
    return found


def _composition_keys(node: object) -> set[str]:
    """Return composition keywords found anywhere in a schema subtree."""
    if isinstance(node, dict):
        keys = {key for key in ("oneOf", "anyOf", "allOf") if key in node}
        for child in node.values():
            keys.update(_composition_keys(child))
        return keys
    if isinstance(node, list):
        keys: set[str] = set()
        for child in node:
            keys.update(_composition_keys(child))
        return keys
    return set()


def test_dsc_root_and_manifest_target_rec_2026_09() -> None:
    """Keep DSC package root and manifest aligned with the current ASM release."""
    schemas = load_yaml(DSC_SCHEMA)["components"]["schemas"]
    root = schemas["differentialScanningCalorimetrySimpleModel"]
    manifest = root["properties"]["$asm.manifest"]

    assert root["required"] == [
        "$asm.manifest",
        "differential scanning calorimetry aggregate document",
    ]
    assert manifest["default"].endswith(
        "/REC/2026/09/differential-scanning-calorimetry.manifest"
    )

def test_dsc_model_covers_current_nested_measurement_hierarchy() -> None:
    """Assert the DSC document, measurement, device-control, and sample path."""
    schemas = load_yaml(DSC_SCHEMA)["components"]["schemas"]

    aggregate = schemas["differentialScanningCalorimetryAggregateDocument"]
    assert aggregate["required"] == ["differential scanning calorimetry document"]
    assert "data system document" in aggregate["properties"]
    assert "device system document" in aggregate["properties"]

    technique = schemas["differentialScanningCalorimetryDocument"]
    assert technique["required"] == [
        "@index",
        "measurement aggregate document",
    ]
    measurements = schemas["measurementAggregateDocument"]
    assert measurements["required"] == ["measurement document"]

    measurement = schemas["DscMeasurementDocument"]
    assert set(measurement["required"]) == {
        "device control aggregate document",
        "differential scanning calorimetry data cube",
        "sample document",
    }
    assert measurement["properties"]["differential scanning calorimetry data cube"][
        "$ref"
    ] == "#/components/schemas/DscDataCube"

    assert schemas["DscSampleDocument"]["required"] == [
        "container state description",
        "sample identifier",
    ]
    assert schemas["DscDeviceDocument"]["required"] == [
        "@index",
        "device type",
    ]
    assert schemas["DeviceControlDocument"]["required"] == [
        "@index",
        "device type",
    ]
    assert schemas["ProfileSettingDocument"]["required"] == [
        "@index",
        "profile setting feature",
        "initial setting",
        "final setting",
    ]
    assert schemas["DscProcessedDataDocument"]["properties"]["@index"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 2147483647,
    }
    assert "@index" in schemas["DscProcessedDataDocument"]["required"]
    assert "@index" in schemas["DscProcessedDataDocument"]["required"]
    assert schemas["dscPeak"]["properties"]["@index"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 2147483647,
    }
    assert "@index" in schemas["dscPeak"]["required"]
    assert schemas["DeviceControlAggregateDocument"]["required"] == [
        "device control document"
    ]
    assert schemas["ProfileSettingAggregateDocument"]["required"] == [
        "profile setting document"
    ]


def test_dsc_data_cube_is_flat_and_constrained_to_asm_shape() -> None:
    """Keep the DSC cube shape simple while preserving release constraints."""
    schemas = load_yaml(DSC_SCHEMA)["components"]["schemas"]
    cube = schemas["DscDataCube"]
    structure = schemas["DscDataCubeStructure"]

    assert cube["required"] == ["cube-structure", "data"]
    assert cube["properties"]["data"]["$ref"] == (
        "./datacube.yaml#/components/schemas/AsmDatacubeData"
    )
    assert structure["properties"]["dimensions"]["minItems"] == 1
    assert structure["properties"]["dimensions"]["maxItems"] == 1
    assert structure["properties"]["measures"]["minItems"] == 1
    assert structure["properties"]["measures"]["maxItems"] == 1
    assert schemas["DscDataCubeDimension"]["properties"]["concept"]["enum"] == [
        "temperature"
    ]
    assert schemas["DscDataCubeDimension"]["properties"]["unit"]["enum"] == [
        "degC"
    ]
    assert schemas["DscDataCubeMeasure"]["properties"]["concept"]["enum"] == [
        "heat capacity"
    ]
    assert schemas["DscDataCubeMeasure"]["properties"]["unit"]["enum"] == [
        "W/g"
    ]


def test_dsc_quantity_properties_use_release_units() -> None:
    """Keep DSC temperature and heat-capacity quantities release-specific."""
    schemas = load_yaml(DSC_SCHEMA)["components"]["schemas"]
    device_control = schemas["DeviceControlDocument"]["properties"]
    assert device_control["detector sampling rate setting"]["$ref"] == (
        "./common.yaml#/components/schemas/HertzQuantityValue"
    )

    profile = schemas["ProfileSettingDocument"]["properties"]
    assert profile["duration setting"]["$ref"] == (
        "./common.yaml#/components/schemas/SecondsQuantityValue"
    )
    assert profile["initial setting"]["$ref"] == (
        "./common.yaml#/components/schemas/QuantityValue"
    )

    peaks = schemas["dscPeak"]["properties"]
    assert peaks["peak end"]["$ref"] == (
        "./common.yaml#/components/schemas/DegreesCelsiusQuantityValue"
    )
    assert peaks["transition enthalpy"]["$ref"] == (
        "./common.yaml#/components/schemas/JoulePerGramQuantityValue"
    )


def test_dsc_local_schemas_are_reachable_and_union_free() -> None:
    """Avoid generator-created unnamed branches in DSC model components."""
    schemas = load_yaml(DSC_SCHEMA)["components"]["schemas"]
    reachable = {"differentialScanningCalorimetrySimpleModel"}
    pending = list(reachable)

    while pending:
        name = pending.pop()
        for referenced in _local_references(schemas[name]):
            if referenced not in reachable:
                reachable.add(referenced)
                pending.append(referenced)

    assert reachable == set(schemas)
    assert _composition_keys(schemas) == set()


def test_dsc_peak_fields_use_shared_quantity_types() -> None:
    """Use canonical commons quantity schemas for DSC peak properties."""
    schemas = load_yaml(DSC_SCHEMA)["components"]["schemas"]
    peak = schemas["dscPeak"]["properties"]

    assert peak["glass transition temperature"]["$ref"] == (
        "./common.yaml#/components/schemas/DegreesCelsiusQuantityValue"
    )
    assert peak["transition enthalpy"]["$ref"] == (
        "./common.yaml#/components/schemas/JoulePerGramQuantityValue"
    )
    assert peak["heat capacity (dsc)"]["$ref"] == (
        "./common.yaml#/components/schemas/JoulePerGramDegreeCelsiusQuantityValue"
    )
