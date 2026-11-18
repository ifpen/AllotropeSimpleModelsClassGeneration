"""
Java ``pom.xml`` post-generation patch.

``openapi-generator`` emits a ``pom.xml`` that lacks the
``central-publishing-maven-plugin`` required for Maven Central deployment.
This module injects it using the standard-library
:mod:`xml.etree.ElementTree` API rather than a heavier dependency such as
``lxml``.

The patch is **idempotent**: running ``generate.py`` a second time will
detect the plugin and skip the injection.

The module also declares the commons package as a dependency of every
generated instrument package (Maven, NuGet, npm and Python manifests).
"""

from __future__ import annotations

import json
import re
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


# ---------------------------------------------------------------------------
# Commons dependency patches for instrument-spec packages
# ---------------------------------------------------------------------------
#
# Instrument packages reference the commons classes (through import and
# schema mappings) instead of re-emitting them, so every generated build
# manifest must declare the commons package as a dependency.  Each patch is
# idempotent.


def add_java_dependency(
    pom_path: Path,
    group_id: str,
    artifact_id: str,
    version: str,
    dry_run: bool = False,
) -> None:
    """Add a compile dependency to a generated ``pom.xml`` (idempotent).

    Args:
        pom_path:    Path to the ``pom.xml`` to patch.
        group_id:    Maven ``groupId`` of the dependency.
        artifact_id: Maven ``artifactId`` of the dependency.
        version:     Exact dependency version.
        dry_run:     When ``True``, do not write the file.
    """
    if not pom_path.exists():
        print(f"[WARN] pom.xml not found, skipping patch: {pom_path}", file=sys.stderr)
        return
    tree = ET.parse(pom_path)
    dependencies = _find_or_create(tree.getroot(), "dependencies")
    for dependency in dependencies.findall(_q("dependency")):
        if (
            dependency.findtext(_q("groupId")) == group_id
            and dependency.findtext(_q("artifactId")) == artifact_id
        ):
            print(f"  [pom patch] {artifact_id} dependency already present, skipping.")
            return
    dependency = ET.SubElement(dependencies, _q("dependency"))
    ET.SubElement(dependency, _q("groupId")).text = group_id
    ET.SubElement(dependency, _q("artifactId")).text = artifact_id
    ET.SubElement(dependency, _q("version")).text = version
    print(f"  [pom patch] added dependency {group_id}:{artifact_id}:{version}")
    if not dry_run:
        tree.write(pom_path, encoding="UTF-8", xml_declaration=True)


def add_csharp_package_reference(
    output_dir: Path,
    package_id: str,
    version: str,
    dry_run: bool = False,
) -> None:
    """Add a ``PackageReference`` to the generated (non-test) C# project.

    Args:
        output_dir: Generated C# output directory.
        package_id: NuGet package id of the dependency.
        version:    Exact dependency version.
        dry_run:    When ``True``, do not write the file.
    """
    projects = [
        path for path in sorted(output_dir.glob("src/*/*.csproj"))
        if not path.stem.endswith(".Test")
    ]
    if not projects:
        print(f"[WARN] No C# project found, skipping patch: {output_dir}", file=sys.stderr)
        return
    for project in projects:
        tree = ET.parse(project)
        root = tree.getroot()
        if any(ref.get("Include") == package_id for ref in root.iter("PackageReference")):
            print(f"  [csproj patch] {package_id} reference already present, skipping.")
            continue
        group = ET.SubElement(root, "ItemGroup")
        ET.SubElement(group, "PackageReference", Include=package_id, Version=version)
        print(f"  [csproj patch] added PackageReference {package_id} {version}")
        if not dry_run:
            tree.write(project, encoding="utf-8", xml_declaration=False)


def add_npm_peer_dependency(
    package_json: Path,
    name: str,
    version: str,
    dry_run: bool = False,
) -> None:
    """Declare *name* as a peer dependency of a generated Angular library.

    Angular libraries list shared runtime packages as peers so applications
    install a single copy; the commons package is shared by every spec.

    Args:
        package_json: Generated ``package.json``.
        name:         npm package name of the dependency.
        version:      Exact dependency version.
        dry_run:      When ``True``, do not write the file.
    """
    if not package_json.exists():
        print(f"[WARN] package.json not found, skipping patch: {package_json}", file=sys.stderr)
        return
    manifest = json.loads(package_json.read_text(encoding="utf-8"))
    peers = manifest.setdefault("peerDependencies", {})
    if peers.get(name) == version:
        print(f"  [package.json patch] {name} peer dependency already present, skipping.")
        return
    peers[name] = version
    print(f"  [package.json patch] added peer dependency {name}@{version}")
    if not dry_run:
        package_json.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


_PY_IMPORT_ANCHOR = "from __future__ import annotations\n"


def patch_python_package(
    output_dir: Path,
    package: str,
    commons_package: str,
    commons_version: str,
    commons_schemas: set[str],
    dry_run: bool = False,
) -> None:
    """Make a generated Python instrument package depend on Python commons.

    The Python generator maps commons schemas to bare class names but never
    imports them, and it emits empty parent ``__init__.py`` files that would
    overwrite the commons package's own ``__init__.py`` on installation.
    This patch:

    * imports every referenced commons class from *commons_package* in each
      generated module;
    * removes the parent ``__init__.py`` files owned by the commons package
      and packages only the instrument sub-package;
    * declares ``<commons_package>==<commons_version>`` in ``pyproject.toml``,
      ``setup.py`` and ``requirements.txt``.

    Args:
        output_dir:      Generated Python output directory.
        package:         Instrument package (e.g. ``ifpen.allotrope_models.gc``).
        commons_package: Commons package (e.g. ``ifpen.allotrope_models``).
        commons_version: Exact commons version.
        commons_schemas: Commons class names that may be referenced.
        dry_run:         When ``True``, do not modify any file.
    """
    package_dir = output_dir.joinpath(*package.split("."))
    if not package_dir.is_dir():
        print(f"[WARN] Python package not found, skipping patch: {package_dir}", file=sys.stderr)
        return

    patterns = {name: re.compile(rf"\b{re.escape(name)}\b") for name in commons_schemas}
    patched = 0
    for module in sorted(package_dir.rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        if f"from {commons_package} import " in text or _PY_IMPORT_ANCHOR not in text:
            continue
        used = sorted(name for name, pattern in patterns.items() if pattern.search(text))
        if not used:
            continue
        imports = "".join(f"from {commons_package} import {name}\n" for name in used)
        patched += 1
        if not dry_run:
            module.write_text(text.replace(_PY_IMPORT_ANCHOR, _PY_IMPORT_ANCHOR + imports, 1), encoding="utf-8")
    print(f"  [python patch] added {commons_package} imports to {patched} module(s)")

    parts = package.split(".")
    for depth in range(1, len(parts)):
        init = output_dir.joinpath(*parts[:depth], "__init__.py")
        if init.exists():
            print(f"  [python patch] removed {init.relative_to(output_dir)} (owned by {commons_package})")
            if not dry_run:
                init.unlink()

    requirement = f"{commons_package}=={commons_version}"
    setup_py = output_dir / "setup.py"
    if setup_py.exists():
        text = setup_py.read_text(encoding="utf-8")
        text = text.replace(
            "from setuptools import setup, find_packages",
            "from setuptools import setup, find_namespace_packages",
        )
        text = re.sub(
            r"packages=find_packages\([^)]*\)",
            f'packages=find_namespace_packages(include=["{package}", "{package}.*"])',
            text,
        )
        if requirement not in text:
            text = text.replace("REQUIRES = [\n", f'REQUIRES = [\n    "{requirement}",\n', 1)
        if not dry_run:
            setup_py.write_text(text, encoding="utf-8")

    pyproject = output_dir / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        if requirement not in text:
            text = text.replace("dependencies = [\n", f'dependencies = [\n  "{requirement}",\n', 1)
        if not dry_run:
            pyproject.write_text(text, encoding="utf-8")

    requirements = output_dir / "requirements.txt"
    if requirements.exists():
        text = requirements.read_text(encoding="utf-8")
        if requirement not in text.splitlines():
            text = text.rstrip("\n") + f"\n{requirement}\n"
        if not dry_run:
            requirements.write_text(text, encoding="utf-8")
    print(f"  [python patch] declared dependency {requirement}")
