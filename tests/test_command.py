"""Tests for :mod:`allotrope_gen.command`."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from allotrope_gen.command import (
    build_cmd,
    build_commons_cmd,
    build_import_mappings,
    generator_cli,
    interpolate,
    write_config,
)
from allotrope_gen.config import LANGUAGES, LanguageConfig


# ---------------------------------------------------------------------------
# interpolate
# ---------------------------------------------------------------------------


class TestInterpolate:
    def test_spec_placeholder(self):
        assert interpolate("allotrope-models-{spec}", "gc") == "allotrope-models-gc"

    def test_spec_pascal_placeholder(self):
        assert interpolate("Models{spec_pascal}", "gc") == "ModelsGc"

    def test_spec_upper_placeholder(self):
        assert interpolate("{spec_upper}_MODELS", "gc") == "GC_MODELS"

    def test_multiple_placeholders(self):
        result = interpolate("{spec}-{spec_pascal}-{spec_upper}", "gc")
        assert result == "gc-Gc-GC"

    def test_no_placeholders(self):
        assert interpolate("unchanged", "gc") == "unchanged"

    def test_empty_spec(self):
        # When spec="" (commons), placeholders expand to empty string
        assert interpolate("prefix-{spec}", "") == "prefix-"


# ---------------------------------------------------------------------------
# generator_cli
# ---------------------------------------------------------------------------


class TestGeneratorCli:
    def test_linux_returns_bare_name(self):
        with patch.object(sys, "platform", "linux"):
            assert generator_cli() == "openapi-generator-cli"

    def test_windows_returns_cmd_wrapper(self):
        with patch.object(sys, "platform", "win32"):
            assert generator_cli() == "openapi-generator-cli.cmd"

    def test_darwin_returns_bare_name(self):
        with patch.object(sys, "platform", "darwin"):
            assert generator_cli() == "openapi-generator-cli"


# ---------------------------------------------------------------------------
# write_config
# ---------------------------------------------------------------------------


class TestWriteConfig:
    def test_creates_json_file(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        write_config(cfg.extra_props, "gc", cfg, tmp_path)
        config_file = tmp_path / "openapi-generator-config.json"
        assert config_file.exists()

    def test_json_is_valid(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        write_config(cfg.extra_props, "gc", cfg, tmp_path)
        doc = json.loads((tmp_path / "openapi-generator-config.json").read_text())
        assert isinstance(doc, dict)

    def test_package_key_injected(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        write_config(cfg.extra_props, "gc", cfg, tmp_path)
        doc = json.loads((tmp_path / "openapi-generator-config.json").read_text())
        assert cfg.package_key in doc
        assert doc[cfg.package_key] == cfg.package_fn("gc")

    def test_spec_placeholder_resolved(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        write_config(cfg.extra_props, "gc", cfg, tmp_path)
        doc = json.loads((tmp_path / "openapi-generator-config.json").read_text())
        # artifactId contains {spec} → should be resolved
        assert doc["artifactId"] == "allotrope-models-gc"

    def test_commons_uses_empty_spec(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        write_config(cfg.extra_props, "", cfg, tmp_path)
        doc = json.loads((tmp_path / "openapi-generator-config.json").read_text())
        assert doc[cfg.package_key] == cfg.package_fn("")


# ---------------------------------------------------------------------------
# build_import_mappings
# ---------------------------------------------------------------------------


class TestBuildImportMappings:
    def test_empty_schemas_returns_empty_string(self):
        cfg = LANGUAGES["java"]
        assert build_import_mappings(set(), cfg) == ""

    def test_single_schema(self):
        cfg = LANGUAGES["java"]
        result = build_import_mappings({"Foo"}, cfg)
        assert "Foo" in result
        assert cfg.commons_package in result

    def test_multiple_schemas_sorted(self):
        cfg = LANGUAGES["java"]
        result = build_import_mappings({"Zebra", "Alpha"}, cfg)
        # Sorted → Alpha comes before Zebra in the string
        assert result.index("Alpha") < result.index("Zebra")

    def test_comma_separated(self):
        cfg = LANGUAGES["java"]
        result = build_import_mappings({"Foo", "Bar"}, cfg)
        parts = result.split(",")
        assert len(parts) == 2

    def test_typescript_pattern_no_class_suffix(self):
        cfg = LANGUAGES["typescript-angular"]
        result = build_import_mappings({"Foo"}, cfg)
        # TypeScript maps class → npm package, not class → package.class
        assert "Foo=" in result
        assert result.count("Foo") == 1  # class name appears exactly once


# ---------------------------------------------------------------------------
# build_cmd
# ---------------------------------------------------------------------------


class TestBuildCmd:
    def test_returns_list(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        spec_file = tmp_path / "gc.yaml"
        spec_file.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        cmd = build_cmd("gc", spec_file, cfg, {"Foo"}, tmp_path)
        assert isinstance(cmd, list)

    def test_contains_generate_subcommand(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        spec_file = tmp_path / "gc.yaml"
        spec_file.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        cmd = build_cmd("gc", spec_file, cfg, set(), tmp_path)
        assert "generate" in cmd

    def test_contains_input_spec_flag(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        spec_file = tmp_path / "gc.yaml"
        spec_file.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        cmd = build_cmd("gc", spec_file, cfg, set(), tmp_path)
        assert "--input-spec" in cmd
        idx = cmd.index("--input-spec")
        assert cmd[idx + 1] == str(spec_file)

    def test_import_mappings_omitted_when_empty(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        spec_file = tmp_path / "gc.yaml"
        spec_file.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        cmd = build_cmd("gc", spec_file, cfg, set(), tmp_path)
        assert "--import-mappings" not in cmd

    def test_import_mappings_present_when_non_empty(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        spec_file = tmp_path / "gc.yaml"
        spec_file.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        cmd = build_cmd("gc", spec_file, cfg, {"Foo"}, tmp_path)
        assert "--import-mappings" in cmd

    def test_extra_opts_appended(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        spec_file = tmp_path / "gc.yaml"
        spec_file.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        cmd = build_cmd("gc", spec_file, cfg, set(), tmp_path)
        for opt in cfg.extra_opts:
            assert opt in cmd


# ---------------------------------------------------------------------------
# build_commons_cmd
# ---------------------------------------------------------------------------


class TestBuildCommonsCmd:
    def test_returns_list(self, tmp_path: Path):
        cfg = LANGUAGES["python"]
        merged = tmp_path / "commons-merged.yaml"
        merged.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        cmd = build_commons_cmd(merged, cfg, tmp_path)
        assert isinstance(cmd, list)

    def test_uses_merged_path_as_input(self, tmp_path: Path):
        cfg = LANGUAGES["python"]
        merged = tmp_path / "commons-merged.yaml"
        merged.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        cmd = build_commons_cmd(merged, cfg, tmp_path)
        assert str(merged) in cmd

    def test_no_import_mappings_flag(self, tmp_path: Path):
        """Commons generation never uses --import-mappings."""
        cfg = LANGUAGES["java"]
        merged = tmp_path / "commons-merged.yaml"
        merged.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        cmd = build_commons_cmd(merged, cfg, tmp_path)
        assert "--import-mappings" not in cmd

    def test_config_file_uses_commons_package(self, tmp_path: Path):
        cfg = LANGUAGES["java"]
        merged = tmp_path / "commons-merged.yaml"
        merged.write_text("openapi: '3.1.0'\n", encoding="utf-8")
        build_commons_cmd(merged, cfg, tmp_path)
        doc = json.loads((tmp_path / "openapi-generator-config.json").read_text())
        assert doc[cfg.package_key] == cfg.package_fn("")
