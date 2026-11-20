"""Unit tests for the toolchain-independent helpers of ``verify_deserialization``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


from verify_deserialization import (
    KNOWN_EXAMPLE_DEVIATIONS,
    compare_documents,
    forbidden_npm_packages,
    latest_examples,
    prepare_examples,
    spec_manifests,
    typescript_enum_constant,
    with_nan_quantity,
    without_known_deviations,
)


class TestCompareDocuments:
    def test_identical(self):
        doc = {"a": [1, {"b": "x"}], "c": True}
        assert compare_documents(doc, json.loads(json.dumps(doc))) == []

    def test_dropped_member(self):
        assert compare_documents({"a": 1, "b": 2}, {"a": 1}) == ['dropped $["b"]']

    def test_empty_member_counts_as_dropped(self):
        assert compare_documents({"a": {"x": 1}}, {"a": {}}) == ['dropped $["a"]']

    def test_added_member(self):
        assert compare_documents({}, {"a": 1})[0].startswith('added $["a"]')

    def test_added_null_is_ignored(self):
        assert compare_documents({}, {"a": None, "b": []}) == []

    def test_numeric_equivalence(self):
        assert compare_documents({"v": 17}, {"v": 17.0}) == []
        assert compare_documents({"v": 1.5}, {"v": 1.6}) != []

    def test_boolean_is_not_a_number(self):
        assert compare_documents({"v": True}, {"v": 1}) != []

    def test_equivalent_datetimes(self):
        assert compare_documents({"t": "2020-01-01T00:00:00Z"}, {"t": "2020-01-01T00:00:00+00:00"}) == []
        assert compare_documents({"t": "2020-01-01T00:00:00Z"}, {"t": "2020-01-01T01:00:00Z"}) != []

    def test_list_length(self):
        assert compare_documents([1, 2], [1]) == ["length of $: 2 != 1"]


class TestDeviations:
    def test_removes_only_under_parent(self):
        doc = {
            "processed data aggregate document": {"peak list": {}, "processed data document": [{"peak list": {}}]},
        }
        cleaned, removed = without_known_deviations("gc", doc)
        assert cleaned == {"processed data aggregate document": {"processed data document": [{"peak list": {}}]}}
        assert removed == ["processed data aggregate document.peak list"]

    def test_array_items_of_parent(self):
        doc = {"match result document": [{"InChiKey molecular structure": "K", "molecular formula": "C"}]}
        cleaned, removed = without_known_deviations("gc", doc)
        assert cleaned == {"match result document": [{"molecular formula": "C"}]}
        assert len(removed) == 1

    def test_every_deviation_is_documented(self):
        for rules in KNOWN_EXAMPLE_DEVIATIONS.values():
            assert all(parent and member and reason for parent, member, reason in rules)


#: Smallest LC-shaped example every synthetic variant applies to.
LC_EXAMPLE = {
    "$asm.manifest": "manifest",
    "liquid chromatography aggregate document": {
        "liquid chromatography document": [{
            "measurement aggregate document": {
                "measurement document": [{
                    "processed data aggregate document": {"processed data document": [{}]},
                }],
            },
        }],
    },
}


def _prepared(tmp_path: Path, spec: str = "hplc") -> dict[str, dict]:
    """Prepare :data:`LC_EXAMPLE` for *spec*; return the documents by file name."""
    example = tmp_path / "lc.json"
    example.write_text(json.dumps(LC_EXAMPLE), encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in prepare_examples(spec, [example], work)}


class TestSyntheticVariants:
    def test_hplc_diagnostic_trace_variant(self, tmp_path: Path):
        trace = _prepared(tmp_path)["lc.diagnostic-trace.json"]
        aggregate = trace["liquid chromatography aggregate document"]["liquid chromatography document"][0]
        measurement = aggregate["measurement aggregate document"]
        document = measurement["diagnostic trace aggregate document"]["diagnostic trace document"][0]
        assert document["description"] and "pump pressure data cube" in document

    @pytest.mark.parametrize("suffix, typed", [("union-primitive", False), ("union-typed", True)])
    def test_union_variants_fill_every_union(self, tmp_path: Path, suffix: str, typed: bool):
        document = _prepared(tmp_path)[f"lc.{suffix}.json"]
        technique = document["liquid chromatography aggregate document"]
        measurement = technique["liquid chromatography document"][0]["measurement aggregate document"][
            "measurement document"][0]
        values = [
            technique["analysis sequence document"]["start time"],
            measurement["processed data aggregate document"]["processed data document"][0][
                "data processing document"]["data processing time"],
            measurement["image aggregate document"]["image document"][0]["index"],
        ]
        assert technique["analysis sequence document"]["written name"]
        if typed:
            assert all(set(value) == {"@type", "value"} for value in values)
        else:
            assert [type(value) for value in values] == [str, str, int]

    def test_gc_union_variant_only_fills_analysis_sequence(self, tmp_path: Path):
        document = _prepared(tmp_path, "gc")["lc.union-primitive.json"]
        technique = document["liquid chromatography aggregate document"]
        measurement = technique["liquid chromatography document"][0]["measurement aggregate document"][
            "measurement document"][0]
        assert "analysis sequence document" in technique
        assert "image aggregate document" not in measurement

    def test_variant_must_apply(self, tmp_path: Path):
        example = tmp_path / "lc.json"
        example.write_text("{}", encoding="utf-8")
        work = tmp_path / "work"
        work.mkdir()
        with pytest.raises(RuntimeError):
            prepare_examples("hplc", [example], work)


class TestNanVariant:
    def test_first_quantity_value_becomes_nan(self):
        doc = {"a": [{"value": 1, "unit": "s"}, {"value": 2, "unit": "s"}], "b": {"value": 3}}
        assert with_nan_quantity(doc)
        assert doc == {"a": [{"value": "NaN", "unit": "s"}, {"value": 2, "unit": "s"}], "b": {"value": 3}}

    def test_no_quantity(self):
        assert not with_nan_quantity({"value": True, "unit": "s"})

    def test_prepare_examples_writes_copies_and_variant(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("verify_deserialization.SYNTHETIC_VARIANTS", {})
        example = tmp_path / "ex.json"
        example.write_text(json.dumps({"q": {"value": 1.0, "unit": "s"}}), encoding="utf-8")
        work = tmp_path / "work"
        work.mkdir()
        prepared = prepare_examples("dsc", [example], work)
        assert [p.name for p in prepared] == ["ex.json", "ex.nan.json"]
        assert json.loads(prepared[1].read_text(encoding="utf-8")) == {"q": {"value": "NaN", "unit": "s"}}


class TestExampleSelection:
    def test_spec_manifests(self):
        assert any("gas-chromatography" in m for m in spec_manifests("gc"))

    def test_latest_release_with_matching_manifest(self, tmp_path: Path):
        manifest = next(iter(spec_manifests("dsc")))
        base = tmp_path / "test" / "adm" / "dsc" / "REC"
        for release, name, doc_manifest in [
            ("2026/03", "old.json", manifest),
            ("2026/09", "new.json", manifest),
            ("2026/09", "other.json", "http://example.org/other.manifest"),
            ("2026/10", "foreign.json", "http://example.org/other.manifest"),
        ]:
            path = base / release / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"$asm.manifest": doc_manifest}), encoding="utf-8")
        assert [p.name for p in latest_examples("dsc", tmp_path)] == ["new.json"]

    def test_missing_directory(self, tmp_path: Path):
        assert latest_examples("dsc", tmp_path) == []


class TestTypescriptEnumConstant:
    ENUM = (
        "export interface Peak {\n    unit: Peak.UnitEnum;\n}\n"
        "export namespace Peak {\n    export const UnitEnum = {\n        S: 's',\n        Min: 'min'\n"
        "    } as const;\n    export type UnitEnum = typeof UnitEnum[keyof typeof UnitEnum];\n}\n"
    )

    def test_first_enum_in_name_order(self, tmp_path: Path):
        (tmp_path / "model").mkdir()
        (tmp_path / "model" / "b.ts").write_text(self.ENUM, encoding="utf-8")
        (tmp_path / "model" / "a.ts").write_text("export interface A {\n    x: string;\n}\n", encoding="utf-8")
        assert typescript_enum_constant(tmp_path) == ("Peak.UnitEnum.S", "s")

    def test_package_without_enum(self, tmp_path: Path):
        (tmp_path / "model").mkdir()
        (tmp_path / "model" / "a.ts").write_text("export interface A {\n    x: string;\n}\n", encoding="utf-8")
        assert typescript_enum_constant(tmp_path) is None


def test_forbidden_npm_packages(tmp_path: Path):
    for name in ("@angular/core", "@ifpen/allotrope-models-commons"):
        (tmp_path / name).mkdir(parents=True)
        (tmp_path / name / "package.json").write_text("{}", encoding="utf-8")
    assert forbidden_npm_packages(tmp_path) == ["@angular/core"]
