"""Regression tests for the commons-owned analysis-sequence model."""

from __future__ import annotations

from pathlib import Path

from allotrope_gen.config import COMMON_YAML_FILES, SPECS
from allotrope_gen.schema import load_yaml, schemas_referenced_from_commons


RESOURCES = Path(__file__).parents[1] / "src" / "main" / "resources"
ANALYSIS_SEQUENCE_REF = (
    "./core.yaml#/components/schemas/AnalysisSequenceDocument"
)


def test_analysis_sequence_document_is_defined_once_in_commons() -> None:
    """Keep the shared model in Commons rather than copying it into instruments."""
    core = load_yaml(RESOURCES / "core.yaml")["components"]["schemas"]
    assert "AnalysisSequenceDocument" in core

    for spec_path in SPECS.values():
        schemas = load_yaml(spec_path)["components"]["schemas"]
        assert "AnalysisSequenceDocument" not in schemas
        assert "analysisSequenceDocument" not in schemas


def test_analysis_sequence_document_is_exposed_by_all_three_instruments() -> None:
    """Expose the Commons model on the HPLC, DSC, and GC aggregate roots."""
    aggregate_names = {
        "hplc": ("liquidChromatographyAggregateDocument",),
        "dsc": ("differentialScanningCalorimetryAggregateDocument",),
        "gc": ("gasChromatographyAggregateDocument",),
    }

    for spec_name, (aggregate_name,) in aggregate_names.items():
        schemas = load_yaml(SPECS[spec_name])["components"]["schemas"]
        field = schemas[aggregate_name]["properties"]["analysis sequence document"]
        assert field["$ref"] == ANALYSIS_SEQUENCE_REF
        assert "AnalysisSequenceDocument" in schemas_referenced_from_commons(
            SPECS[spec_name], COMMON_YAML_FILES
        )


def test_analysis_sequence_commons_schema_keeps_shared_fields() -> None:
    """Preserve the shared document's established field names and requirement."""
    schemas = load_yaml(RESOURCES / "core.yaml")["components"]["schemas"]
    document = schemas["AnalysisSequenceDocument"]

    assert set(document["properties"]) == {
        "UNC path",
        "custom information aggregate document",
        "end time",
        "file name",
        "identifier",
        "method identifier",
        "method name",
        "start time",
        "version number",
        "written name",
    }
    assert document["required"] == ["written name"]
