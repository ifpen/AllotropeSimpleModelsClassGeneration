"""Tests for :mod:`allotrope_gen.patch.typescript`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from allotrope_gen.patch import PackageReadme, PatchError
from allotrope_gen.config import TYPESCRIPT_VERSION
from allotrope_gen.patch.typescript import (
    ANGULAR_RUNTIME,
    MODELS_INDEX,
    add_peer_dependency,
    allow_nan_strings,
    describe_package,
    keep_models_only,
)

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
    def test_metadata_and_readme(self, tmp_path: Path):
        (tmp_path / "package.json").write_text(json.dumps({
            "name": "@ifpen/allotrope-models-gc", "description": "OpenAPI client for @ifpen/allotrope-models-gc",
            "author": "OpenAPI-Generator Contributors", "keywords": ["openapi-client"],
        }), encoding="utf-8")
        readme = PackageReadme("# GC\n", "GC models.", ("asm", "gc"))
        describe_package(tmp_path, readme)
        describe_package(tmp_path, readme)  # idempotent
        manifest = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
        assert manifest["description"] == "GC models."
        assert manifest["author"] == "Maxime Visconte"
        assert manifest["keywords"] == ["asm", "gc"]
        assert manifest["homepage"].startswith("https://github.com/ifpen/")
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == "# GC\n"


#: ``package.json`` written by typescript-angular 7.23.0 (``ngVersion`` 19).
GENERATED_MANIFEST = {
    "name": "@ifpen/allotrope-models-gc",
    "version": "2026.9.0",
    "scripts": {"prepare": "npm run build", "build": "ng-packagr -p ng-package.json"},
    "peerDependencies": {"@angular/core": "^19.0.0", "rxjs": "^7.4.0", "@ifpen/allotrope-models-commons": "2026.9.0"},
    "devDependencies": {"@angular/core": "^19.0.0", "ng-packagr": "^19.0.0", "rxjs": "^7.4.0", "zone.js": "^0.15.0"},
}

GENERATED_INDEX = (
    "export * from './api/api';\nexport * from './model/models';\nexport * from './variables';\n"
    "export * from './configuration';\nexport * from './api.module';\nexport * from './provide-api';\n"
    "export * from './param';\n"
)

GENERATED_PEAK = (
    "import { DateTimeValue } from '@ifpen/allotrope-models-commons';\n"
    "import { PeakArea } from './peakArea';\n\n"
    "export interface Peak {\n    'peak area'?: PeakArea;\n}\n"
)


def _generated_output(root: Path) -> Path:
    """Write a minimal typescript-angular output (runtime files included)."""
    for name in ANGULAR_RUNTIME:
        if name == "api":
            (root / "api").mkdir()
            (root / "api" / "api.ts").write_text("export const APIS = [];\n", encoding="utf-8")
        else:
            (root / name).write_text("import { InjectionToken } from '@angular/core';\n", encoding="utf-8")
    (root / "model").mkdir()
    (root / "model" / "peak.ts").write_text(GENERATED_PEAK, encoding="utf-8")
    (root / "model" / "models.ts").write_text("export * from './peak';\nexport * from './peakArea';\n", encoding="utf-8")
    (root / "index.ts").write_text(GENERATED_INDEX, encoding="utf-8")
    (root / "tsconfig.json").write_text('{"compilerOptions": {"target": "es5"}}', encoding="utf-8")
    (root / "package.json").write_text(json.dumps(GENERATED_MANIFEST), encoding="utf-8")
    return root


class TestKeepModelsOnly:
    def test_removes_angular_runtime(self, tmp_path: Path):
        keep_models_only(_generated_output(tmp_path))
        assert not [name for name in ANGULAR_RUNTIME if (tmp_path / name).exists()]
        assert (tmp_path / "index.ts").read_text(encoding="utf-8") == MODELS_INDEX

    def test_relative_imports_get_js_extension(self, tmp_path: Path):
        keep_models_only(_generated_output(tmp_path))
        peak = (tmp_path / "model" / "peak.ts").read_text(encoding="utf-8")
        assert "from './peakArea.js';" in peak
        assert "from '@ifpen/allotrope-models-commons';" in peak  # package imports unchanged
        assert "export interface Peak {\n    'peak area'?: PeakArea;\n}" in peak  # model unchanged
        models = (tmp_path / "model" / "models.ts").read_text(encoding="utf-8")
        assert models == "export * from './peak.js';\nexport * from './peakArea.js';\n"

    def test_manifest_is_esm_without_angular(self, tmp_path: Path):
        keep_models_only(_generated_output(tmp_path))
        manifest = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
        assert manifest["peerDependencies"] == {"@ifpen/allotrope-models-commons": "2026.9.0"}
        assert manifest["devDependencies"] == {"typescript": TYPESCRIPT_VERSION}
        assert manifest["scripts"] == {"prepare": "npm run build", "build": "tsc -p tsconfig.json"}
        assert manifest["type"] == "module"
        assert manifest["exports"] == {".": {"types": "./dist/index.d.ts", "default": "./dist/index.js"}}
        assert manifest["files"] == ["dist"]
        assert manifest["name"] == "@ifpen/allotrope-models-gc"

    def test_commons_without_peers_has_no_peer_dependencies(self, tmp_path: Path):
        _generated_output(tmp_path)
        manifest = {**GENERATED_MANIFEST, "peerDependencies": {"@angular/core": "^19.0.0", "rxjs": "^7.4.0"}}
        (tmp_path / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
        keep_models_only(tmp_path)
        assert "peerDependencies" not in json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))

    def test_tsconfig_emits_es_modules(self, tmp_path: Path):
        keep_models_only(_generated_output(tmp_path))
        options = json.loads((tmp_path / "tsconfig.json").read_text(encoding="utf-8"))["compilerOptions"]
        assert options["module"] == "nodenext"
        assert options["declaration"] is True
        assert options["outDir"] == "dist"

    def test_idempotent(self, tmp_path: Path):
        keep_models_only(_generated_output(tmp_path))
        before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        keep_models_only(tmp_path)
        assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def test_dry_run_changes_nothing(self, tmp_path: Path):
        _generated_output(tmp_path)
        before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        keep_models_only(tmp_path, dry_run=True)
        assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def test_unknown_build_script_fails_loudly(self, tmp_path: Path):
        _generated_output(tmp_path)
        (tmp_path / "package.json").write_text(json.dumps({"scripts": {"build": "rollup -c"}}), encoding="utf-8")
        with pytest.raises(PatchError, match="build script"):
            keep_models_only(tmp_path)

    def test_index_without_models_fails_loudly(self, tmp_path: Path):
        _generated_output(tmp_path)
        (tmp_path / "index.ts").write_text("export * from './api/api';\n", encoding="utf-8")
        with pytest.raises(PatchError, match="model/models"):
            keep_models_only(tmp_path)

    def test_new_runtime_file_fails_loudly(self, tmp_path: Path):
        _generated_output(tmp_path)
        (tmp_path / "http.interceptor.ts").write_text("export {};\n", encoding="utf-8")
        with pytest.raises(PatchError, match="outside model/"):
            keep_models_only(tmp_path)

    def test_angular_import_in_model_fails_loudly(self, tmp_path: Path):
        _generated_output(tmp_path)
        (tmp_path / "model" / "token.ts").write_text("import { Injectable } from '@angular/core';\n", encoding="utf-8")
        with pytest.raises(PatchError, match="Angular or RxJS"):
            keep_models_only(tmp_path)

    def test_missing_manifest_warns(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        keep_models_only(tmp_path)
        assert "[WARN] package.json not found" in capsys.readouterr().err
