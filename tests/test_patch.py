"""Tests for :mod:`allotrope_gen.patch`."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from allotrope_gen.patch import (
    _MAVEN_NS,
    _CENTRAL_PLUGIN_ARTIFACT,
    _CENTRAL_PLUGIN_GROUP,
    _CENTRAL_PLUGIN_VERSION,
    patch_java_pom,
)


def _has_plugin(pom_path: Path) -> bool:
    """Helper to check if the central plugin is present in the XML file."""
    tree = ET.parse(pom_path)
    root = tree.getroot()
    plugins = root.find(f".//{{{_MAVEN_NS}}}plugin")
    if plugins is None:
        return False
    for plugin in root.findall(f".//{{{_MAVEN_NS}}}plugin"):
        artifact_id = plugin.findtext(f"{{{_MAVEN_NS}}}artifactId")
        if artifact_id == _CENTRAL_PLUGIN_ARTIFACT:
            return True
    return False


class TestPatchJavaPom:
    def test_missing_file_logs_warning(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        missing = tmp_path / "nonexistent.xml"
        patch_java_pom(missing)
        
        captured = capsys.readouterr()
        assert "[WARN] pom.xml not found, skipping patch" in captured.err

    def test_dry_run_does_not_modify_file(self, pom_xml: Path, capsys: pytest.CaptureFixture[str]):
        original_content = pom_xml.read_text(encoding="utf-8")
        
        patch_java_pom(pom_xml, dry_run=True)
        
        # Verify content unchanged
        assert pom_xml.read_text(encoding="utf-8") == original_content
        
        captured = capsys.readouterr()
        assert "injected" in captured.out
        assert not _has_plugin(pom_xml)

    def test_injects_plugin_when_build_element_missing(self, pom_xml: Path, capsys: pytest.CaptureFixture[str]):
        assert not _has_plugin(pom_xml)
        
        patch_java_pom(pom_xml, dry_run=False)
        
        captured = capsys.readouterr()
        assert f"injected {_CENTRAL_PLUGIN_ARTIFACT}" in captured.out
        assert _has_plugin(pom_xml)
        
        # Parse XML and check specific configurations
        tree = ET.parse(pom_xml)
        root = tree.getroot()
        plugin = None
        for p in root.findall(f".//{{{_MAVEN_NS}}}plugin"):
            if p.findtext(f"{{{_MAVEN_NS}}}artifactId") == _CENTRAL_PLUGIN_ARTIFACT:
                plugin = p
                break
        
        assert plugin is not None
        assert plugin.findtext(f"{{{_MAVEN_NS}}}groupId") == _CENTRAL_PLUGIN_GROUP
        assert plugin.findtext(f"{{{_MAVEN_NS}}}version") == _CENTRAL_PLUGIN_VERSION
        assert plugin.findtext(f"{{{_MAVEN_NS}}}extensions") == "true"
        
        config = plugin.find(f"{{{_MAVEN_NS}}}configuration")
        assert config is not None
        assert config.findtext(f"{{{_MAVEN_NS}}}publishingServerId") == "central"
        assert config.findtext(f"{{{_MAVEN_NS}}}autoPublish") == "true"

    def test_injects_plugin_into_existing_build_element(self, pom_xml_with_build: Path, capsys: pytest.CaptureFixture[str]):
        assert not _has_plugin(pom_xml_with_build)
        
        patch_java_pom(pom_xml_with_build, dry_run=False)
        
        captured = capsys.readouterr()
        assert f"injected {_CENTRAL_PLUGIN_ARTIFACT}" in captured.out
        assert _has_plugin(pom_xml_with_build)

    def test_idempotent_skips_when_already_present(self, pom_xml: Path, capsys: pytest.CaptureFixture[str]):
        # First injection
        patch_java_pom(pom_xml, dry_run=False)
        capsys.readouterr() # clear buffers
        
        # Second invocation
        patch_java_pom(pom_xml, dry_run=False)
        
        captured = capsys.readouterr()
        assert "already present, skipping" in captured.out
        assert _has_plugin(pom_xml)
