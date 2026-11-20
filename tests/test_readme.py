"""Tests for :mod:`allotrope_gen.readme`."""

from __future__ import annotations

import re

import pytest

from allotrope_gen.config import LANGUAGES, SPECS
from allotrope_gen.readme import package_name, python_distribution, registry_url, release, render, technique

MODULES = ["commons", *SPECS]


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize("lang", list(LANGUAGES))
def test_every_package_renders(lang: str, module: str):
    readme = render(lang, module)
    assert readme.text.startswith("# Allotrope Simple Model ")
    assert "REC/2026/09" in readme.text and "REC/2026/09" in readme.summary
    # Nothing of the generated HTTP-client README survives.
    for bloat in ("ApiException", "HTTP request", "git_push", "localhost", "OpenAPI Generator"):
        assert bloat not in readme.text
    assert "${" not in readme.text
    assert f"**[" in readme.text  # the current package is highlighted in the matrix
    assert "\n\n\n" not in readme.text
    assert "allotrope" in readme.keywords


def test_spec_readme_content():
    text = render("csharp", "hplc").text
    assert "# Allotrope Simple Model Liquid Chromatography (C#)" in text
    assert "`http://purl.allotrope.org/manifests/liquid-chromatography/REC/2026/09/liquid-chromatography.manifest`" in text
    assert "JsonSerializer.Deserialize<LiquidChromatographySimpleModel>" in text
    assert "document.LiquidChromatographyAggregateDocument.LiquidChromatographyDocument.Count" in text
    assert "dotnet add package IFPEN.AllotropeConverters.AllotropeModels.Hplc --version 2026.9.0" in text


@pytest.mark.parametrize("lang, expected", [
    ("java", "document.getGasChromatographyAggregateDocument().getGasChromatographyDocument().size()"),
    ("python", "len(document.gas_chromatography_aggregate_document.gas_chromatography_document)"),
    ("typescript-angular",
     "document['gas chromatography aggregate document']?.['gas chromatography document']?.length"),
])
def test_navigation_per_language(lang: str, expected: str):
    assert expected in render(lang, "gc").text


@pytest.mark.parametrize("lang, version", [
    ("java", "2026.09.0-beta3"),
    ("csharp", "2026.9.0-beta.3"),
    ("python", "2026.9.0b3"),
    ("typescript-angular", "2026.9.0-beta.3"),
])
def test_prerelease_versions(lang: str, version: str):
    text = render(lang, "dsc", "beta.3").text
    assert f" {version}" in text or f"={version}" in text or f"@{version}" in text or f">{version}<" in text
    assert re.search(r"2026\.0?9\.0(?![-.b0-9])", text) is None  # never the final version


def test_npm_installs_commons_peer():
    text = render("typescript-angular", "gc").text
    assert "npm install @ifpen/allotrope-models-gc@2026.9.0 @ifpen/allotrope-models-commons@2026.9.0" in text
    assert "peer dependency" in text


def test_commons_readme_points_to_techniques():
    text = render("python", "commons").text
    assert "pip install ifpen-allotrope-models==2026.9.0" in text
    assert "install the package of\nyour technique" in text


def test_helpers():
    assert release("commons") == "REC/2026/09"
    assert technique("dsc") == "Differential Scanning Calorimetry"
    assert python_distribution("ifpen.allotrope_models.gc") == "ifpen-allotrope-models-gc"
    assert package_name("java", "gc") == "allotrope-models-gc"
    assert registry_url("csharp", "commons") == (
        "https://www.nuget.org/packages/IFPEN.AllotropeConverters.AllotropeModels.Commons"
    )
    assert registry_url("python", "hplc") == "https://pypi.org/project/ifpen-allotrope-models-hplc/"
