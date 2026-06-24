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

    def test_all_values_are_paths(self):
        from pathlib import Path
        for key, path in SPECS.items():
            assert isinstance(path, Path), f"SPECS['{key}'] is not a Path"
