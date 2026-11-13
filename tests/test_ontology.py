"""Tests for Allotrope ontology description enrichment."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from allotrope_gen.ontology import (
    _index_terms,
    _property_class_candidates,
    _resolve_description,
    enrich_spec_descriptions,
    property_class_ids,
)


def test_resolves_property_class_iri_before_label() -> None:
    by_iri, by_label = _index_terms(
        [
            {
                "iri": "urn:asm:exact",
                "label": "detector model number",
                "description": ["Exact class definition."],
            },
            {
                "iri": "urn:other:similar",
                "label": "detector model number",
                "description": ["Different class definition."],
            },
        ]
    )

    result = _resolve_description(
        "detector model number",
        {"$asm.property-class": "urn:asm:exact"},
        by_iri,
        by_label,
        {},
    )

    assert result == "Exact class definition."


def test_ambiguous_label_is_not_guessed() -> None:
    by_iri, by_label = _index_terms(
        [
            {"iri": "urn:first", "label": "analyst", "description": ["First."]},
            {"iri": "urn:second", "label": "analyst", "description": ["Second."]},
        ]
    )

    assert _resolve_description("analyst", {}, by_iri, by_label, {}) is None


def test_official_reference_resolves_safe_peak_label_aliases(tmp_path: Path) -> None:
    reference_path = tmp_path / "official.json"
    reference_path.write_text(
        json.dumps(
            {
                "properties": {
                    "peak width at 4.4 % of height": {
                        "$asm.property-class": "urn:peak-44"
                    },
                    "number of theoretical plates by peak width at half height": {
                        "$asm.property-class": "urn:plates-half"
                    },
                    "number of theoretical plates by tangent method": {
                        "$asm.property-class": "urn:plates-tangent"
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    class_ids = property_class_ids(reference_path)

    assert class_ids["peak width at 4.4 % of height"] == {"urn:peak-44"}
    assert _property_class_candidates(
        "peak width at 4.4 % height", class_ids
    ) == {"urn:peak-44"}
    assert _property_class_candidates(
        "number theoretical plates peak width at half height", class_ids
    ) == {"urn:plates-half"}
    assert _property_class_candidates(
        "number theoretical plates tangent method", class_ids
    ) == {"urn:plates-tangent"}


def test_normalized_alias_with_multiple_property_classes_is_rejected(
    tmp_path: Path,
) -> None:
    reference_path = tmp_path / "official.json"
    reference_path.write_text(
        json.dumps(
            {
                "properties": {
                    "peak width at 4.4 % of height": {
                        "$asm.property-class": "urn:first"
                    },
                    "peak width 4.4 % height": {
                        "$asm.property-class": "urn:second"
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    class_ids = property_class_ids(reference_path)

    assert len(_property_class_candidates("peak width at 4.4 % height", class_ids)) == 2


def test_safe_alias_resolves_to_authoritative_definition() -> None:
    by_iri, by_label = _index_terms(
        [
            {
                "iri": "urn:peak-44",
                "label": "peak width at 4.4 % of height",
                "description": ["Official peak-width definition."],
            }
        ]
    )

    result = _resolve_description(
        "peak width at 4.4 % height",
        {},
        by_iri,
        by_label,
        {"peak width at 4.4 % height": {"urn:peak-44"}},
    )

    assert result == "Official peak-width definition."


def test_inferred_class_id_is_rejected_when_ontology_label_disagrees() -> None:
    by_iri, by_label = _index_terms(
        [
            {
                "iri": "urn:start-time",
                "label": "start time setting",
                "description": ["A start-time definition."],
            }
        ]
    )

    result = _resolve_description(
        "end time setting",
        {},
        by_iri,
        by_label,
        {"end time setting": {"urn:start-time"}},
    )

    assert result is None


def test_enriches_missing_descriptions_and_preserves_authored_text(tmp_path: Path) -> None:
    spec_path = tmp_path / "gc.yaml"
    spec_path.write_text(
        "openapi: 3.1.0\ncomponents:\n  schemas:\n    Instrument:\n"
        "      type: object\n      properties:\n"
        "        detector model number: {type: string}\n"
        "        detector bandwidth setting: {type: string, description: Existing text.}\n"
        "        nested:\n          type: object\n          properties:\n"
        "            peak: {type: string, description: {}}\n"
        "        quantity:\n          $ref: './common.yaml#/components/schemas/QuantityValue'\n",
        encoding="utf-8",
    )
    cache_path = tmp_path / "afo-terms.json"
    cache_path.write_text(
        json.dumps(
            {
                "terms": [
                    {
                        "iri": "urn:detector-model",
                        "label": "detector model number",
                        "description": ["A detector's model number."],
                    },
                    {
                        "iri": "urn:quantity",
                        "label": "quantity",
                        "description": ["A quantity definition."],
                    },
                    {"iri": "urn:peak", "label": "peak", "description": ["A peak definition."]},
                ]
            }
        ),
        encoding="utf-8",
    )

    added = enrich_spec_descriptions(spec_path, cache_path=cache_path)

    document = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    properties = document["components"]["schemas"]["Instrument"]["properties"]
    assert added == 2
    assert properties["detector model number"]["description"] == "A detector's model number."
    assert properties["detector bandwidth setting"]["description"] == "Existing text."
    assert properties["nested"]["properties"]["peak"]["description"] == "A peak definition."
    assert properties["quantity"]["$ref"] == "./common.yaml#/components/schemas/QuantityValue"
    assert "description" not in properties["quantity"]
    assert "$asm.property-class" not in spec_path.read_text(encoding="utf-8")


def test_dry_run_does_not_write_spec(tmp_path: Path) -> None:
    spec_path = tmp_path / "gc.yaml"
    original = (
        "openapi: 3.1.0\ncomponents:\n  schemas:\n    Instrument:\n"
        "      type: object\n      properties:\n        analyst: {type: string}\n"
    )
    spec_path.write_text(original, encoding="utf-8")
    cache_path = tmp_path / "afo-terms.json"
    cache_path.write_text(
        json.dumps(
            {"terms": [{"iri": "urn:analyst", "label": "analyst", "description": ["An analyst."]}]}
        ),
        encoding="utf-8",
    )

    added = enrich_spec_descriptions(spec_path, cache_path=cache_path, dry_run=True)

    assert added == 1
    assert spec_path.read_text(encoding="utf-8") == original


def test_unresolved_asm_class_refreshes_stale_cache(tmp_path: Path, monkeypatch) -> None:
    from allotrope_gen import ontology

    spec_path = tmp_path / "gc.yaml"
    spec_path.write_text(
        "openapi: 3.1.0\ncomponents:\n  schemas:\n    Instrument:\n"
        "      type: object\n      properties:\n"
        "        detector model number: {type: string, $asm.property-class: 'urn:new-class'}\n",
        encoding="utf-8",
    )
    cache_path = tmp_path / "afo-terms.json"
    cache_path.write_text(json.dumps({"terms": []}), encoding="utf-8")
    import os
    import time

    os.utime(cache_path, (time.time() - ontology.CACHE_MAX_AGE_SECONDS - 10,) * 2)
    refreshed = {
        "urn:new-class": {
            "iri": "urn:new-class",
            "label": "detector model number",
            "description": ["A new definition."],
        }
    }
    monkeypatch.setattr(ontology, "_download_terms", lambda: list(refreshed.values()))

    added = enrich_spec_descriptions(spec_path, cache_path=cache_path)

    document = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    assert added == 1
    assert (
        document["components"]["schemas"]["Instrument"]["properties"]
        ["detector model number"]["description"]
        == "A new definition."
    )
