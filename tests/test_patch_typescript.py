"""Tests for :mod:`allotrope_gen.patch.typescript`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from allotrope_gen.patch import PackageReadme, PatchError
from allotrope_gen.patch.typescript import add_peer_dependency, allow_nan_strings, describe_package

NAN = {"SecondsQuantityValue": ["value"]}


class TestAddPeerDependency:
    def test_adds_peer(self, tmp_path: Path):
        manifest = tmp_path / "package.json"
        manifest.write_text(json.dumps({"name": "x", "peerDependencies": {"@angular/core": "^19"}}), encoding="utf-8")
        add_peer_dependency(manifest, "@ifpen/allotrope-models-commons", "2026.09.0")
        peers = json.loads(manifest.read_text(encoding="utf-8"))["peerDependencies"]
        assert peers == {"@angular/core": "^19", "@ifpen/allotrope-models-commons": "2026.09.0"}

    def test_missing_manifest_warns(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        add_peer_dependency(tmp_path / "package.json", "x", "1")
        assert "[WARN] package.json not found" in capsys.readouterr().err


class TestAllowNanStrings:
    def test_widens_number_type(self, tmp_path: Path):
        (tmp_path / "model").mkdir()
        source = tmp_path / "model" / "secondsQuantityValue.ts"
        source.write_text("export interface SecondsQuantityValue {\n    value: number;\n}\n", encoding="utf-8")
        allow_nan_strings(tmp_path, NAN)
        allow_nan_strings(tmp_path, NAN)  # idempotent
        assert "    value: number | 'NaN';\n" in source.read_text(encoding="utf-8")

    def test_unexpected_generated_code_fails_loudly(self, tmp_path: Path):
        (tmp_path / "model").mkdir()
        (tmp_path / "model" / "secondsQuantityValue.ts").write_text("value: string;\n", encoding="utf-8")
        with pytest.raises(PatchError):
            allow_nan_strings(tmp_path, NAN)


class TestDescribePackage:
    def test_metadata_and_dist_asset(self, tmp_path: Path):
        (tmp_path / "package.json").write_text(json.dumps({
            "name": "@ifpen/allotrope-models-gc", "description": "OpenAPI client for @ifpen/allotrope-models-gc",
            "author": "OpenAPI-Generator Contributors", "keywords": ["openapi-client"],
        }), encoding="utf-8")
        (tmp_path / "ng-package.json").write_text(json.dumps({"lib": {"entryFile": "index.ts"}}), encoding="utf-8")
        readme = PackageReadme("# GC\n", "GC models.", ("asm", "gc"))
        describe_package(tmp_path, readme)
        describe_package(tmp_path, readme)  # idempotent
        manifest = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
        assert manifest["description"] == "GC models."
        assert manifest["author"] == "Maxime Visconte"
        assert manifest["keywords"] == ["asm", "gc"]
        assert manifest["homepage"].startswith("https://github.com/ifpen/")
        assert json.loads((tmp_path / "ng-package.json").read_text(encoding="utf-8"))["assets"] == ["README.md"]
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == "# GC\n"
