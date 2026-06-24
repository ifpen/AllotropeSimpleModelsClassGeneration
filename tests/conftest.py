"""
Shared pytest fixtures for the allotrope_gen test suite.

Fixtures here provide minimal, self-contained YAML files so that tests do not
depend on the real ``src/main/resources/`` files (which would couple unit tests
to the repository's content and make them fragile).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Minimal OpenAPI document helpers
# ---------------------------------------------------------------------------


def _make_openapi_yaml(schemas: dict) -> str:
    """Return a minimal OpenAPI 3.1 YAML string containing *schemas*."""
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "Test", "version": "0.1"},
        "components": {"schemas": schemas},
    }
    return yaml.dump(doc, allow_unicode=True)


def _make_pom_xml(with_build: bool = False) -> str:
    """Return a minimal Maven ``pom.xml`` string.

    Args:
        with_build: When ``True``, include an empty ``<build><plugins>`` stanza
                    so that tests can verify both the "create from scratch" and
                    "append to existing" code paths in :func:`patch_java_pom`.
    """
    ns = "http://maven.apache.org/POM/4.0.0"
    build_block = "<build><plugins></plugins></build>" if with_build else ""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<project xmlns="{ns}">\n'
        f"  <modelVersion>4.0.0</modelVersion>\n"
        f"  <groupId>test</groupId>\n"
        f"  <artifactId>test-artifact</artifactId>\n"
        f"  <version>0.1</version>\n"
        f"  {build_block}\n"
        f"</project>\n"
    )


# ---------------------------------------------------------------------------
# Path fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def common_yaml(tmp_path: Path) -> Path:
    """A temporary ``common.yaml`` with two schemas: ``Foo`` and ``Bar``."""
    path = tmp_path / "common.yaml"
    path.write_text(
        _make_openapi_yaml(
            {
                "Foo": {"type": "object", "properties": {"x": {"type": "integer"}}},
                "Bar": {"type": "string"},
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def datacube_yaml(tmp_path: Path) -> Path:
    """A temporary ``datacube.yaml`` with one schema: ``Cube``."""
    path = tmp_path / "datacube.yaml"
    path.write_text(
        _make_openapi_yaml({"Cube": {"type": "object"}}),
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def spec_yaml(tmp_path: Path) -> Path:
    """A temporary instrument-spec YAML that ``$ref``s ``Foo`` from common.yaml."""
    path = tmp_path / "gc.yaml"
    content = (
        "openapi: '3.1.0'\n"
        "info:\n"
        "  title: GC Test\n"
        "  version: '0.1'\n"
        "components:\n"
        "  schemas:\n"
        "    GcModel:\n"
        "      type: object\n"
        "      properties:\n"
        "        quantity:\n"
        "          $ref: './common.yaml#/components/schemas/Foo'\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture()
def pom_xml(tmp_path: Path) -> Path:
    """A temporary minimal ``pom.xml`` without an existing ``<build>`` block."""
    path = tmp_path / "pom.xml"
    path.write_text(_make_pom_xml(with_build=False), encoding="utf-8")
    return path


@pytest.fixture()
def pom_xml_with_build(tmp_path: Path) -> Path:
    """A temporary ``pom.xml`` that already has an empty ``<build><plugins>``."""
    path = tmp_path / "pom_with_build.xml"
    path.write_text(_make_pom_xml(with_build=True), encoding="utf-8")
    return path
