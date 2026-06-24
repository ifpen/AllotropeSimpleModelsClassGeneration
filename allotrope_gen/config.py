"""
Centralised configuration: paths, language descriptors, and spec registry.

The :class:`LanguageConfig` dataclass replaces the raw ``dict`` that was used
previously, giving IDE auto-completion, type safety, and an explicit, documented
contract for every supported language.

**Adding a new language**
    1. Write a ``_<lang>_package(spec: str) -> str`` naming helper below.
    2. Add a ``LanguageConfig`` entry to :data:`LANGUAGES`.
    3. Add the corresponding publish job to ``.github/workflows/generate.yml``.

**Adding a new instrument spec**
    Add its path to :data:`SPECS`.  Nothing else in this file needs to change.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Filesystem paths
# ---------------------------------------------------------------------------

#: Repository root (parent of the ``allotrope_gen`` package directory).
ROOT: Path = Path(__file__).parent.parent
RESOURCES: Path = ROOT / "src" / "main" / "resources"
OUTPUT: Path = ROOT / "target" / "generated-sources"

#: YAML files whose schemas are published together as the *commons* library.
#: Schemas defined here are *never* re-generated inside instrument-spec modules;
#: they are imported from the published commons artifact instead.
COMMON_YAML_FILES: list[Path] = [
    RESOURCES / "common.yaml",
    RESOURCES / "datacube.yaml",
]

#: Instrument specs to generate.
#: Key   = short identifier used on the CLI and in output paths (e.g. ``"gc"``).
#: Value = path to the OpenAPI 3.1 YAML file.
SPECS: dict[str, Path] = {
    "gc": RESOURCES / "gc.yaml",
    "dsc": RESOURCES / "dsc.yaml",
    # "hplc": RESOURCES / "hplc.yaml",
}

# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------
# Each language serialises the logical package name differently:
#   Java    : fr.ifpen.allotropeconverters.allotrope_models.gc
#   C#      : IFPEN.AllotropeConverters.AllotropeModels.Gc
#   Python  : ifpen.allotrope_models.gc
#   npm     : @ifpen/allotrope-models-gc


def to_pascal(s: str) -> str:
    """Return *s* with its first letter capitalised and the rest unchanged.

    Examples::

        >>> to_pascal("gc")
        'Gc'
        >>> to_pascal("hplc")
        'Hplc'
        >>> to_pascal("")
        ''
    """
    return s.capitalize()


def java_package(spec: str) -> str:
    """Return the Java model package for *spec*.

    An empty *spec* string produces the commons base package.

    Examples::

        >>> java_package("gc")
        'fr.ifpen.allotropeconverters.allotrope_models.gc'
        >>> java_package("")
        'fr.ifpen.allotropeconverters.allotrope_models'
    """
    base = "fr.ifpen.allotropeconverters.allotrope_models"
    return f"{base}.{spec}" if spec else base


def csharp_namespace(spec: str) -> str:
    """Return the C# root namespace for *spec*.

    Examples::

        >>> csharp_namespace("gc")
        'IFPEN.AllotropeConverters.AllotropeModels.Gc'
        >>> csharp_namespace("")
        'IFPEN.AllotropeConverters.AllotropeModels'
    """
    base = "IFPEN.AllotropeConverters.AllotropeModels"
    return f"{base}.{to_pascal(spec)}" if spec else base


def python_package(spec: str) -> str:
    """Return the Python package name for *spec*.

    Examples::

        >>> python_package("gc")
        'ifpen.allotrope_models.gc'
        >>> python_package("")
        'ifpen.allotrope_models'
    """
    base = "ifpen.allotrope_models"
    return f"{base}.{spec}" if spec else base


def npm_package(spec: str) -> str:
    """Return the scoped npm package name for *spec*.

    An empty *spec* produces the commons package.

    Examples::

        >>> npm_package("gc")
        '@ifpen/allotrope-models-gc'
        >>> npm_package("")
        '@ifpen/allotrope-models-commons'
    """
    suffix = f"-{spec}" if spec else "-commons"
    return f"@ifpen/allotrope-models{suffix}"


# ---------------------------------------------------------------------------
# Language configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class LanguageConfig:
    """Describes how to generate and publish libraries for one target language.

    Attributes:
        generator:        ``openapi-generator-cli`` generator name
                          (e.g. ``"java"``, ``"python"``).
        output_subdir:    Sub-directory under
                          ``target/generated-sources/<spec>/``
                          where the generator writes its output.
        package_key:      Config-file key that controls the package / namespace
                          name for this language (e.g. ``"modelPackage"`` for
                          Java, ``"packageName"`` for C# and Python,
                          ``"npmName"`` for TypeScript).
        package_fn:       Callable ``(spec: str) -> str`` that maps a spec
                          identifier to the appropriate package / namespace
                          string.  Called with ``""`` when generating the
                          commons library.
        commons_package:  Package identifier for the pre-published commons
                          artifact.  Used to build ``--import-mappings`` so the
                          generator does not re-emit commons classes.
        import_pattern:   ``str.format``-style template for a single
                          ``--import-mappings`` entry.  Receives
                          ``{class_name}`` and ``{commons_package}``.
        extra_props:      Key/value pairs written verbatim to the generator
                          config JSON (``--config``).  Values may contain
                          ``{spec}``, ``{spec_pascal}``, or ``{spec_upper}``
                          placeholders that are resolved at generation time via
                          :func:`~allotrope_gen.command.interpolate`.
        extra_opts:       Additional CLI flags appended after the base command
                          (e.g. ``["--skip-validate-spec"]``).
        publish_cmd:      Shell command used to publish the generated artifact,
                          executed from the output directory.
                          ``None`` means no automated publish step is wired up.
    """

    generator: str
    output_subdir: str
    package_key: str
    package_fn: Callable[[str], str]
    commons_package: str
    import_pattern: str
    extra_props: dict[str, str]
    extra_opts: list[str] = field(default_factory=list)
    publish_cmd: str | None = None


# ---------------------------------------------------------------------------
# Language registry
# ---------------------------------------------------------------------------

LANGUAGES: dict[str, LanguageConfig] = {
    "java": LanguageConfig(
        generator="java",
        output_subdir="java",
        package_key="modelPackage",
        package_fn=java_package,
        commons_package=java_package("commons"),
        import_pattern="{class_name}={commons_package}.{class_name}",
        extra_props={
            "groupId":                  "fr.ifpen.allotropeconverters",
            "artifactId":               "allotrope-models-{spec}",
            "licenseName":              "CeCILL, version 2.1",
            "licenseUrl":               "https://opensource.org/license/cecill-2-1/",
            "developerName":            "Maxime Visconte",
            "developerEmail":           "maxime.visconte@ifpen.fr",
            "developerOrganization":    "IFPEN",
            "developerOrganizationUrl": "https://www.ifpenergiesnouvelles.com/",
            "scmConnection":            "scm:git:git://github.com/ifpen/AllotropeSimpleModelsClassGeneration.git",
            "scmDeveloperConnection":   "scm:git:ssh://github.com/ifpen/AllotropeSimpleModelsClassGeneration.git",
            "scmUrl":                   "https://github.com/ifpen/AllotropeSimpleModelsClassGeneration",
            "serializationLibrary":     "jackson",
            "library":                  "native",
        },
        extra_opts=["--skip-validate-spec"],
        publish_cmd="mvn --batch-mode deploy",
    ),
    "typescript-angular": LanguageConfig(
        generator="typescript-angular",
        output_subdir="typescript",
        # TypeScript import-mappings map a schema name to an npm package name,
        # not to a fully-qualified class path.
        package_key="npmName",
        package_fn=npm_package,
        commons_package=npm_package(""),   # @ifpen/allotrope-models-commons
        import_pattern="{class_name}={commons_package}",
        extra_props={
            "ngVersion":   "19.0.0",
            "licenseName": "CeCILL, version 2.1",
        },
        extra_opts=["--skip-validate-spec"],
        publish_cmd="npm publish --access public",
    ),
    "csharp": LanguageConfig(
        generator="csharp",
        output_subdir="csharp",
        # ``packageName`` drives the root namespace in the C# generator.
        package_key="packageName",
        package_fn=csharp_namespace,
        commons_package=csharp_namespace(""),
        import_pattern="{class_name}={commons_package}.{class_name}",
        extra_props={
            "netCoreProjectFile": "true",
            "targetFramework":    "netstandard2.0;net48",
            "licenseId":          "CECILL-2.1",
            "packageAuthors":     "Maxime Visconte",
            "packageCompany":     "IFPEN",
            "packageTags":        "allotrope;models;chemistry;lab;data",
            "packageCopyright":   "Copyright \u00a9 2026 IFP Energies nouvelles (IFPEN)",
        },
        extra_opts=["--skip-validate-spec"],
        publish_cmd=(
            "dotnet nuget push **/*.nupkg"
            " --api-key $NUGET_API_KEY"
            " --source https://api.nuget.org/v3/index.json"
        ),
    ),
    "python": LanguageConfig(
        generator="python",
        output_subdir="python",
        package_key="packageName",
        package_fn=python_package,
        commons_package=python_package(""),
        import_pattern="{class_name}={commons_package}.{class_name}",
        extra_props={
            "packageVersion": "2.0.0",
            "packageUrl":     "https://github.com/ifpen/AllotropeSimpleModelsClassGeneration",
            "packageAuthor":  "Maxime Visconte",
            "packageEmail":   "maxime.visconte@ifpen.fr",
            "licenseName":    "CeCILL, version 2.1",
        },
        extra_opts=["--skip-validate-spec"],
        publish_cmd="pip install build && python -m build && twine upload dist/*",
    ),
}
