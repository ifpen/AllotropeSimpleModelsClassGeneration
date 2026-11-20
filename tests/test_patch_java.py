"""Tests for :mod:`allotrope_gen.patch.java`."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from allotrope_gen.patch.java import (
    CENTRAL_PLUGIN_ARTIFACT,
    CENTRAL_PLUGIN_GROUP,
    CENTRAL_PLUGIN_VERSION,
    MAVEN_NS,
    add_central_publishing_plugin,
    add_dependency,
)

NS = {"m": MAVEN_NS}


def _central_plugin(pom_path: Path) -> ET.Element | None:
    """Return the central publishing plugin element of *pom_path*, if any."""
    for plugin in ET.parse(pom_path).getroot().findall(".//m:plugin", NS):
        if plugin.findtext("m:artifactId", namespaces=NS) == CENTRAL_PLUGIN_ARTIFACT:
            return plugin
    return None


def _pom(path: Path) -> Path:
    """Write a POM with one existing dependency."""
    path.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<project xmlns="{MAVEN_NS}">'
        "<modelVersion>4.0.0</modelVersion><dependencies><dependency>"
        "<groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-core</artifactId>"
        "<version>2</version></dependency></dependencies></project>",
        encoding="utf-8",
    )
    return path


class TestAddCentralPublishingPlugin:
    def test_missing_file_logs_warning(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        add_central_publishing_plugin(tmp_path / "nonexistent.xml")
        assert "[WARN] pom.xml not found, skipping patch" in capsys.readouterr().err

    def test_dry_run_does_not_modify_file(self, pom_xml: Path, capsys: pytest.CaptureFixture[str]):
        original = pom_xml.read_text(encoding="utf-8")
        add_central_publishing_plugin(pom_xml, dry_run=True)
        assert pom_xml.read_text(encoding="utf-8") == original
        assert "injected" in capsys.readouterr().out

    def test_injects_plugin_when_build_element_missing(self, pom_xml: Path):
        add_central_publishing_plugin(pom_xml)
        plugin = _central_plugin(pom_xml)
        assert plugin is not None
        assert plugin.findtext("m:groupId", namespaces=NS) == CENTRAL_PLUGIN_GROUP
        assert plugin.findtext("m:version", namespaces=NS) == CENTRAL_PLUGIN_VERSION
        assert plugin.findtext("m:extensions", namespaces=NS) == "true"
        assert plugin.findtext("m:configuration/m:publishingServerId", namespaces=NS) == "central"
        assert plugin.findtext("m:configuration/m:autoPublish", namespaces=NS) == "true"
        assert pom_xml.read_text(encoding="utf-8").startswith("<?xml")

    def test_injects_plugin_into_existing_build_element(self, pom_xml_with_build: Path):
        add_central_publishing_plugin(pom_xml_with_build)
        assert _central_plugin(pom_xml_with_build) is not None

    def test_idempotent(self, pom_xml: Path, capsys: pytest.CaptureFixture[str]):
        add_central_publishing_plugin(pom_xml)
        add_central_publishing_plugin(pom_xml)
        assert "already present, skipping" in capsys.readouterr().out
        assert len(ET.parse(pom_xml).getroot().findall(".//m:plugin", NS)) == 1


class TestAddDependency:
    def test_adds_and_is_idempotent(self, tmp_path: Path):
        pom = _pom(tmp_path / "pom.xml")
        for _ in range(2):
            add_dependency(pom, "fr.ifpen", "allotrope-models-commons", "2026.09.0")
        deps = ET.parse(pom).getroot().findall("m:dependencies/m:dependency", NS)
        commons = [d for d in deps if d.findtext("m:artifactId", namespaces=NS) == "allotrope-models-commons"]
        assert len(deps) == 2 and len(commons) == 1
        assert commons[0].findtext("m:version", namespaces=NS) == "2026.09.0"

    def test_dry_run_does_not_write(self, tmp_path: Path):
        pom = _pom(tmp_path / "pom.xml")
        before = pom.read_text(encoding="utf-8")
        add_dependency(pom, "g", "a", "1", dry_run=True)
        assert pom.read_text(encoding="utf-8") == before
