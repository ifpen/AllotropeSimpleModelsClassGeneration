"""
Java (Maven) patches.

* :func:`add_central_publishing_plugin` — every Java output.  The generated
  ``pom.xml`` lacks the ``central-publishing-maven-plugin`` that Maven Central
  deployment requires.
* :func:`add_dependency` — spec outputs.  Spec packages use the commons
  classes (import/schema mappings), so they declare the commons artifact.

Java needs no code patch: Jackson reads and writes the ASM ``"NaN"`` string
for ``Double`` and serializes ``oneOf`` primitive/object unions natively.

Both patches edit the POM with :mod:`xml.etree.ElementTree` and are
idempotent.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .common import report

MAVEN_NS = "http://maven.apache.org/POM/4.0.0"
CENTRAL_PLUGIN_GROUP = "org.sonatype.central"
CENTRAL_PLUGIN_ARTIFACT = "central-publishing-maven-plugin"
CENTRAL_PLUGIN_VERSION = "0.12.0"

# Register the namespace so that ElementTree round-trips it without rewriting
# every tag as ``ns0:artifactId``.
ET.register_namespace("", MAVEN_NS)


def _q(tag: str) -> str:
    """Return *tag* qualified with the Maven POM namespace URI."""
    return f"{{{MAVEN_NS}}}{tag}"


def _find_or_create(parent: ET.Element, tag: str) -> ET.Element:
    """Return the first child *tag* of *parent*, creating it if absent."""
    child = parent.find(_q(tag))
    if child is None:
        child = ET.SubElement(parent, _q(tag))
    return child


def _parse(pom_path: Path) -> ET.ElementTree | None:
    """Parse *pom_path*, or warn and return ``None`` if it does not exist."""
    if not pom_path.exists():
        print(f"[WARN] pom.xml not found, skipping patch: {pom_path}", file=sys.stderr)
        return None
    return ET.parse(pom_path)


def _write(tree: ET.ElementTree, pom_path: Path, dry_run: bool) -> None:
    """Write the POM back, restoring the XML declaration ``ET`` drops."""
    if not dry_run:
        tree.write(pom_path, encoding="UTF-8", xml_declaration=True)


def add_central_publishing_plugin(pom_path: Path, dry_run: bool = False) -> None:
    """Inject ``central-publishing-maven-plugin`` into a generated ``pom.xml``.

    Idempotent: an existing plugin entry is left untouched.  A missing POM is
    reported on *stderr* and skipped.

    Args:
        pom_path: Generated ``pom.xml``.
        dry_run:  When ``True``, report but do not write.
    """
    tree = _parse(pom_path)
    if tree is None:
        return
    plugins = _find_or_create(_find_or_create(tree.getroot(), "build"), "plugins")
    if any(p.findtext(_q("artifactId")) == CENTRAL_PLUGIN_ARTIFACT for p in plugins.findall(_q("plugin"))):
        report("pom patch", f"{CENTRAL_PLUGIN_ARTIFACT} already present, skipping.")
        return

    plugin = ET.SubElement(plugins, _q("plugin"))
    ET.SubElement(plugin, _q("groupId")).text = CENTRAL_PLUGIN_GROUP
    ET.SubElement(plugin, _q("artifactId")).text = CENTRAL_PLUGIN_ARTIFACT
    ET.SubElement(plugin, _q("version")).text = CENTRAL_PLUGIN_VERSION
    ET.SubElement(plugin, _q("extensions")).text = "true"
    config = ET.SubElement(plugin, _q("configuration"))
    ET.SubElement(config, _q("publishingServerId")).text = "central"
    ET.SubElement(config, _q("autoPublish")).text = "true"
    report("pom patch", f"injected {CENTRAL_PLUGIN_ARTIFACT} {CENTRAL_PLUGIN_VERSION}")
    _write(tree, pom_path, dry_run)


def add_dependency(pom_path: Path, group_id: str, artifact_id: str, version: str, dry_run: bool = False) -> None:
    """Add a compile dependency to a generated ``pom.xml`` (idempotent).

    Args:
        pom_path:    Generated ``pom.xml``.
        group_id:    Maven ``groupId`` of the dependency.
        artifact_id: Maven ``artifactId`` of the dependency.
        version:     Exact dependency version.
        dry_run:     When ``True``, report but do not write.
    """
    tree = _parse(pom_path)
    if tree is None:
        return
    dependencies = _find_or_create(tree.getroot(), "dependencies")
    for dependency in dependencies.findall(_q("dependency")):
        if dependency.findtext(_q("groupId")) == group_id and dependency.findtext(_q("artifactId")) == artifact_id:
            report("pom patch", f"{artifact_id} dependency already present, skipping.")
            return
    dependency = ET.SubElement(dependencies, _q("dependency"))
    ET.SubElement(dependency, _q("groupId")).text = group_id
    ET.SubElement(dependency, _q("artifactId")).text = artifact_id
    ET.SubElement(dependency, _q("version")).text = version
    report("pom patch", f"added dependency {group_id}:{artifact_id}:{version}")
    _write(tree, pom_path, dry_run)
