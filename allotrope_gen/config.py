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

import re
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
    RESOURCES / "core.yaml",
]

#: Version of the merged commons OpenAPI document (``info.version``).
#: Java and npm commons packages take their version from it, and instrument
#: packages in those languages declare a dependency on exactly this version.
#: It follows the ``YYYY.MM.x`` convention of the newest ASM release the
#: commons schemas are aligned with (``core.yaml``: REC/2026/09).
COMMONS_VERSION: str = "2026.09.0"

#: Instrument specs to generate.
#: Key   = short identifier used on the CLI and in output paths (e.g. ``"gc"``).
#: Value = path to the OpenAPI 3.1 YAML file.
SPECS: dict[str, Path] = {
    "gc": RESOURCES / "gc.yaml",
    "dsc": RESOURCES / "dsc.yaml",
    "hplc": RESOURCES / "hplc.yaml",
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
    """Return the C# root namespace (also NuGet package id and assembly) for *spec*.

    The commons library is ``….AllotropeModels.Commons``: the bare
    ``IFPEN.AllotropeConverters.AllotropeModels`` id was used on nuget.org by
    the earlier all-in-one GC package (2025.6.x), which is deprecated in
    favour of ``….AllotropeModels.Gc``.

    Examples::

        >>> csharp_namespace("gc")
        'IFPEN.AllotropeConverters.AllotropeModels.Gc'
        >>> csharp_namespace("")
        'IFPEN.AllotropeConverters.AllotropeModels.Commons'
    """
    base = "IFPEN.AllotropeConverters.AllotropeModels"
    return f"{base}.{to_pascal(spec)}" if spec else f"{base}.Commons"


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


def npm_semver(version: str) -> str:
    """Return *version* as strict SemVer, as npm stores and resolves it.

    npm normalizes ``2026.09.0`` to ``2026.9.0`` on publish but rejects the
    zero-padded form as a dependency range, so ranges must use this form.

    Examples::

        >>> npm_semver("2026.09.0")
        '2026.9.0'
    """
    return ".".join(str(int(part)) for part in version.split("."))


#: Accepted pre-release labels (``--prerelease``): ``alpha.N``, ``beta.N``, ``rc.N``.
PRERELEASE_PATTERN = re.compile(r"(alpha|beta|rc)\.([1-9]\d*)")
_PEP440_PRERELEASE = {"alpha": "a", "beta": "b", "rc": "rc"}


def version_placeholders(version: str, prerelease: str | None = None) -> dict[str, str]:
    """Return the version forms each registry expects, keyed by placeholder.

    ``{version}``
        Maven form: the OpenAPI version as written (``2026.09.0``), with a
        Maven-style pre-release qualifier without dot (``2026.09.0-beta1``):
        Maven Central's validator rejected bundles whose file names contained
        ``-beta.1`` ("Bundle has content that does NOT have a .pom file").
    ``{semver}``
        npm / NuGet SemVer: no zero padding (``2026.9.0-beta.1``).
    ``{pep440}``
        PyPI: PEP 440 pre-release spelling (``2026.9.0b1``).

    Examples::

        >>> version_placeholders("2026.09.0", "beta.1")["{pep440}"]
        '2026.9.0b1'

    Raises:
        ValueError: If *prerelease* is not ``alpha.N``, ``beta.N`` or ``rc.N``.
    """
    semver = npm_semver(version)
    forms = {"{version}": version, "{semver}": semver, "{pep440}": semver}
    if prerelease:
        match = PRERELEASE_PATTERN.fullmatch(prerelease)
        if match is None:
            raise ValueError(f"invalid pre-release {prerelease!r}: use alpha.N, beta.N or rc.N")
        kind, number = match.groups()
        forms["{version}"] += f"-{kind}{number}"
        forms["{semver}"] += f"-{prerelease}"
        forms["{pep440}"] += f"{_PEP440_PRERELEASE[kind]}{number}"
    return forms


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
        commons_version:  Version template (``{version}``, ``{semver}`` or
                          ``{pep440}``, see :func:`version_placeholders`) of
                          the commons package in this language.  Resolved
                          like the published version, so instrument packages
                          depend on exactly the commons version of the run.
        schema_pattern:   Template for a single ``--schema-mappings`` entry.
                          Schema mappings stop the generator from emitting
                          the commons classes again.  ``None`` reuses
                          *import_pattern*.
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
    commons_version: str
    extra_props: dict[str, str]
    schema_pattern: str | None = None
    extra_opts: list[str] = field(default_factory=list)
    publish_cmd: str | None = None


# ---------------------------------------------------------------------------
# Language registry
# ---------------------------------------------------------------------------

#: Repository coordinates written into every package's metadata (npm
#: ``repository``, NuGet ``RepositoryUrl``, PyPI project URL). npm trusted
#: publishing checks the npm ``repository`` URL against the publishing repo.
_GIT_REPOSITORY = {"gitUserId": "ifpen", "gitRepoId": "AllotropeSimpleModelsClassGeneration"}

LANGUAGES: dict[str, LanguageConfig] = {
    "java": LanguageConfig(
        generator="java",
        output_subdir="java",
        package_key="modelPackage",
        package_fn=java_package,
        commons_package=java_package(""),
        import_pattern="{class_name}={commons_package}.{class_name}",
        commons_version="{version}",
        extra_props={
            **_GIT_REPOSITORY,
            "artifactVersion":          "{version}",
            "groupId":                  "fr.ifpen.allotropeconverters",
            "artifactId":               "allotrope-models-{module}",
            "artifactDescription":      "Allotrope Simple Model (ASM) classes: {module}",
            "artifactUrl":              "https://github.com/ifpen/AllotropeSimpleModelsClassGeneration",
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
            # By default the invoker package is the parent of modelPackage,
            # which for instrument specs is the commons model package: both
            # jars would then ship the same ApiClient/JSON classes.
            "invokerPackage":           "{package}.client",
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
        # npm rejects zero-padded versions in ranges: use the strict form.
        commons_version="{semver}",
        extra_props={
            **_GIT_REPOSITORY,
            "npmVersion":  "{semver}",
            "ngVersion":   "19.0.0",
            "licenseName": "CeCILL, version 2.1",
        },
        # ``uniqueItems`` arrays would otherwise be typed as ``Set<T>``, but
        # the models describe parsed JSON, where arrays are always arrays.
        extra_opts=["--skip-validate-spec", "--type-mappings", "set=Array"],
        publish_cmd="npm publish --access public",
    ),
    "csharp": LanguageConfig(
        generator="csharp",
        output_subdir="csharp",
        # ``packageName`` drives the root namespace in the C# generator.
        package_key="packageName",
        package_fn=csharp_namespace,
        commons_package=csharp_namespace(""),
        import_pattern="{class_name}={commons_package}.Model.{class_name}",
        commons_version="{semver}",
        extra_props={
            **_GIT_REPOSITORY,
            "packageVersion":     "{semver}",
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
        # The Python generator never emits ``import`` statements for mapped
        # schemas.  Map commons schemas to their bare class names;
        # :func:`~allotrope_gen.patch.patch_python_package` then adds
        # ``from ifpen.allotrope_models import <Class>`` where they are used.
        commons_package=python_package(""),
        import_pattern="{class_name}={class_name}",
        commons_version="{pep440}",
        extra_props={
            **_GIT_REPOSITORY,
            "packageVersion": "{pep440}",
            "packageUrl":     "https://github.com/ifpen/AllotropeSimpleModelsClassGeneration",
            "packageAuthor":  "Maxime Visconte",
            "packageEmail":   "maxime.visconte@ifpen.fr",
            "licenseName":    "CeCILL, version 2.1",
        },
        extra_opts=["--skip-validate-spec"],
        publish_cmd="pip install build && python -m build && twine upload dist/*",
    ),
}
