"""
Java ``pom.xml`` post-generation patch.

``openapi-generator`` emits a ``pom.xml`` that lacks the
``central-publishing-maven-plugin`` required for Maven Central deployment.
This module injects it using the standard-library
:mod:`xml.etree.ElementTree` API rather than a heavier dependency such as
``lxml``.

The patch is **idempotent**: running ``generate.py`` a second time will
detect the plugin and skip the injection.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Maven POM namespace constants
# ---------------------------------------------------------------------------

_MAVEN_NS = "http://maven.apache.org/POM/4.0.0"
_CENTRAL_PLUGIN_GROUP    = "org.sonatype.central"
_CENTRAL_PLUGIN_ARTIFACT = "central-publishing-maven-plugin"
_CENTRAL_PLUGIN_VERSION  = "0.7.0"

# Register the namespace so that ElementTree round-trips it without rewriting
# every tag as ``ns0:artifactId`` etc.
ET.register_namespace("", _MAVEN_NS)


def _q(tag: str) -> str:
    """Return *tag* qualified with the Maven POM namespace URI."""
    return f"{{{_MAVEN_NS}}}{tag}"


def _find_or_create(parent: ET.Element, tag: str) -> ET.Element:
    """Return the first child *tag* of *parent*, creating it if absent."""
    child = parent.find(_q(tag))
    if child is None:
        child = ET.SubElement(parent, _q(tag))
    return child


def _plugin_already_present(plugins: ET.Element) -> bool:
    """Return ``True`` if ``central-publishing-maven-plugin`` is already listed."""
    for plugin in plugins.findall(_q("plugin")):
        if plugin.findtext(_q("artifactId")) == _CENTRAL_PLUGIN_ARTIFACT:
            return True
    return False


def _build_plugin_element(plugins: ET.Element) -> None:
    """Append the ``central-publishing-maven-plugin`` element to *plugins*."""
    plugin = ET.SubElement(plugins, _q("plugin"))
    ET.SubElement(plugin, _q("groupId")).text    = _CENTRAL_PLUGIN_GROUP
    ET.SubElement(plugin, _q("artifactId")).text = _CENTRAL_PLUGIN_ARTIFACT
    ET.SubElement(plugin, _q("version")).text    = _CENTRAL_PLUGIN_VERSION
    ET.SubElement(plugin, _q("extensions")).text = "true"
    config = ET.SubElement(plugin, _q("configuration"))
    ET.SubElement(config, _q("publishingServerId")).text = "central"
    ET.SubElement(config, _q("autoPublish")).text        = "true"


def patch_java_pom(pom_path: Path, dry_run: bool = False) -> None:
    """Inject ``central-publishing-maven-plugin`` into a generated ``pom.xml``.

    If the plugin is already present the function logs a message and returns
    without modifying the file.  If *pom_path* does not exist a warning is
    printed to *stderr* and the function returns silently.

    Args:
        pom_path: Path to the ``pom.xml`` to patch.
        dry_run:  When ``True``, log what *would* be done but do not write the
                  file.
    """
    if not pom_path.exists():
        print(f"[WARN] pom.xml not found, skipping patch: {pom_path}", file=sys.stderr)
        return

    tree = ET.parse(pom_path)
    root = tree.getroot()

    build   = _find_or_create(root, "build")
    plugins = _find_or_create(build, "plugins")

    if _plugin_already_present(plugins):
        print("  [pom patch] central-publishing-maven-plugin already present, skipping.")
        return

    _build_plugin_element(plugins)
    print(f"  [pom patch] injected {_CENTRAL_PLUGIN_ARTIFACT} {_CENTRAL_PLUGIN_VERSION}")

    if not dry_run:
        # ``ET.write`` strips the XML declaration by default; restore it.
        tree.write(pom_path, encoding="UTF-8", xml_declaration=True)
