"""
README and registry description of every generated package.

openapi-generator writes READMEs for HTTP API clients (endpoints, retry
policies, ``ApiException``, git-push instructions), which do not apply to
these model-only packages.  This module renders a README for each module
(commons or technique) and language instead; the patches of
:mod:`allotrope_gen.patch` install it where each registry reads it (NuGet
``PackageReadmeFile``, npm and PyPI ``README.md``) and set the one-line
registry description.

Everything shown is derived from the project data, so a new technique or a
new version needs no README change:

* technique name, root model and ASM manifest from the spec YAML
  (:func:`~allotrope_gen.schema.root_schema`,
  :func:`~allotrope_gen.schema.technique_documents`);
* ASM release from the module version (``2026.09.0`` is ``REC/2026/09``);
* package names, versions and registry links from
  :data:`~allotrope_gen.config.LANGUAGES`.

Text lives in ``templates/`` (``spec.md``, ``commons.md``, and per-language
``install.<language>.md``, ``usage-spec.<language>.md`` and
``usage-commons.<language>.md``), rendered with :class:`string.Template`.
The usage snippets mirror the probes of ``verify_deserialization.py``, which
exercise the same calls on the official ASM examples.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from string import Template

from ..command import interpolate, module_version, resolve_version
from ..config import LANGUAGES, PACKAGE_KEYWORDS, SPECS
from ..schema import ASM_MANIFEST, load_yaml, root_schema, technique_documents

TEMPLATES = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class PackageReadme:
    """README of one generated package.

    Attributes:
        text:     Markdown README.
        summary:  One-line registry description (NuGet ``Description``, npm
                  and PyPI ``description``, Maven ``<description>``).
        keywords: Registry keywords/tags.
    """

    text: str
    summary: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class _Language:
    """Language-specific wording of the READMEs."""

    name: str
    registry: str
    kinds: str
    nan: str
    extra: str
    extra_conventions: str = ""
    platform: str = ""


_LANGUAGES: dict[str, _Language] = {
    "java": _Language(
        name="Java",
        registry="Maven Central",
        kinds="classes",
        nan="`Double.NaN`",
        extra="`getAdditionalProperties()`",
    ),
    "csharp": _Language(
        name="C#",
        registry="NuGet",
        kinds="classes",
        nan="`double.NaN`",
        extra="`AdditionalProperties`",
        extra_conventions=(
            "- Numbers are written in their shortest round-trip form on every target\n"
            "  framework (`0.2375`, not `0.23749999999999999` on .NET Framework).\n"
        ),
        platform="| Targets | .NET Standard 2.0, .NET Framework 4.8 |\n",
    ),
    "python": _Language(
        name="Python",
        registry="PyPI",
        kinds="classes (pydantic models)",
        nan="`math.nan`",
        extra="`additional_properties`",
        platform="| Requires | Python 3.9+ |\n",
    ),
    "typescript-angular": _Language(
        name="TypeScript",
        registry="npm",
        kinds="interfaces",
        nan="the string `'NaN'` (the value type is `number | 'NaN'`)",
        extra="the extra keys of `DiagnosticTraceDocument`",
    ),
}

#: Column order of the package matrix.
_MATRIX_ORDER = ("java", "csharp", "python", "typescript-angular")


def _template(name: str, **values: str) -> str:
    """Render ``templates/<name>``; a missing placeholder raises ``KeyError``."""
    return Template((TEMPLATES / name).read_text(encoding="utf-8")).substitute(values).strip("\n")


def release(module: str) -> str:
    """Return the ASM release implemented by *module* (``REC/2026/09``).

    The module version is ``YYYY.MM.patch``, derived from the ASM schema
    ``$id`` (see AGENTS.md, "Versioning tied to ASM schemas").
    """
    year, month, *_ = module_version("" if module == "commons" else module).split(".")
    return f"REC/{year}/{int(month):02d}"


def technique(spec: str) -> str:
    """Return the technique name of *spec* (``Liquid Chromatography``)."""
    aggregate, _ = technique_documents(load_yaml(SPECS[spec])["components"]["schemas"])
    return aggregate.removesuffix(" aggregate document").title()


def package_name(lang: str, module: str) -> str:
    """Return the registry package name of *module* in *lang*."""
    spec = "" if module == "commons" else module
    cfg = LANGUAGES[lang]
    if cfg.generator == "java":
        return interpolate(cfg.extra_props["artifactId"], spec)
    if cfg.generator == "python":
        return python_distribution(cfg.package_fn(spec))
    return cfg.package_fn(spec)


def python_distribution(package: str) -> str:
    """Return the normalized PyPI distribution name of a Python package."""
    return re.sub(r"[._]+", "-", package).lower()


def registry_url(lang: str, module: str) -> str:
    """Return the registry page of *module* in *lang*."""
    name = package_name(lang, module)
    generator = LANGUAGES[lang].generator
    if generator == "java":
        return f"https://central.sonatype.com/artifact/{LANGUAGES[lang].extra_props['groupId']}/{name}"
    if generator == "csharp":
        return f"https://www.nuget.org/packages/{name}"
    if generator == "python":
        return f"https://pypi.org/project/{name}/"
    return f"https://www.npmjs.com/package/{name}"


def _version(lang: str, module: str, prerelease: str | None) -> str:
    """Return the published version of *module* in *lang*."""
    cfg = LANGUAGES[lang]
    # The commons version template is the one every language publishes with.
    return resolve_version(cfg.commons_version, "" if module == "commons" else module, prerelease)


def _packages(current_lang: str, current_module: str) -> str:
    """Return the Markdown matrix of every module in every language."""
    languages = [lang for lang in _MATRIX_ORDER if lang in LANGUAGES]
    header = "| | " + " | ".join(_LANGUAGES[lang].name for lang in languages) + " |"
    rows = [header, "|---" * (len(languages) + 1) + "|"]
    for module in ["commons", *SPECS]:
        label = "Commons" if module == "commons" else technique(module)
        cells = []
        for lang in languages:
            link = f"[{_LANGUAGES[lang].registry}]({registry_url(lang, module)})"
            cells.append(f"**{link}**" if (lang, module) == (current_lang, current_module) else link)
        rows.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def _accessor(lang: str, json_path: list[str]) -> str:
    """Return the expression reaching *json_path* from a root model variable."""
    words = [re.findall(r"[A-Za-z0-9]+", name) for name in json_path]
    if lang == "java":
        return ".".join("get" + "".join(w.capitalize() for w in parts) + "()" for parts in words)
    if lang == "csharp":
        return ".".join("".join(w.capitalize() for w in parts) for parts in words)
    if lang == "python":
        return ".".join("_".join(w.lower() for w in parts) for parts in words)
    return "".join(f"?.['{name}']" if i else f"['{name}']" for i, name in enumerate(json_path))


def render(lang: str, module: str, prerelease: str | None = None) -> PackageReadme:
    """Render the README of *module* (``"commons"`` or a spec key) in *lang*.

    Args:
        lang:       Language key of :data:`~allotrope_gen.config.LANGUAGES`.
        module:     ``"commons"`` or a key of :data:`~allotrope_gen.config.SPECS`.
        prerelease: Pre-release label of the run (``beta.3``), if any.
    """
    cfg = LANGUAGES[lang]
    language = _LANGUAGES[lang]
    spec = "" if module == "commons" else module
    version = _version(lang, module, prerelease)
    rec = release(module)
    package = package_name(lang, module)
    commons_package = package_name(lang, "commons")
    values = {
        "language": language.name,
        "kinds": language.kinds,
        "release": rec,
        "package": package,
        "version": version,
        "namespace": cfg.package_fn(spec),
        "nan": language.nan,
        "extra": language.extra,
        "extra_conventions": language.extra_conventions,
        "platform_row": language.platform,
        "packages": _packages(lang, module),
        "group": cfg.extra_props.get("groupId", ""),
        "distribution": package,
        "peer_install": "",
    }

    if module == "commons":
        title = f"Allotrope Simple Model commons ({language.name})"
        summary = (
            f"Shared Allotrope Simple Model (ASM) {rec} models for {language.name}: quantity values, "
            "data cubes and core documents used by the IFPEN ASM technique packages."
        )
        values |= {"title": title, "usage": _template(f"usage-commons.{lang}.md", **values)}
        values["install"] = _template(f"install.{lang}.md", **values)
        return PackageReadme(_template("commons.md", **values) + "\n", summary, PACKAGE_KEYWORDS)

    schemas = load_yaml(SPECS[spec])["components"]["schemas"]
    root, root_definition = root_schema(schemas)
    manifest = root_definition["properties"][ASM_MANIFEST]["enum"][0]
    documents = list(technique_documents(schemas))
    name = technique(spec)
    title = f"Allotrope Simple Model {name} ({language.name})"
    summary = f"{name} models for reading and writing Allotrope Simple Model (ASM) {rec} JSON in {language.name}."
    if cfg.generator == "typescript-angular":
        values["peer_install"] = f" {commons_package}@{version}"
        depends = f"`{commons_package}` {version} (shared ASM models; peer dependency, install it too)"
    else:
        depends = f"`{commons_package}` {version} (shared ASM models, installed automatically)"
    values |= {
        "title": title,
        "technique": name,
        "root": root,
        "manifest": manifest,
        "commons_package": commons_package,
        "depends": depends,
        "java_documents": _accessor("java", documents),
        "csharp_documents": _accessor("csharp", documents),
        "python_documents": _accessor("python", documents),
        "typescript_documents": _accessor("typescript-angular", documents),
        "naming": _naming(lang, documents[0]),
    }
    values["install"] = _template(f"install.{lang}.md", **values)
    values["usage"] = _template(f"usage-spec.{lang}.md", **values)
    keywords = (*PACKAGE_KEYWORDS, name.lower().replace(" ", "-"))
    return PackageReadme(_template("spec.md", **values) + "\n", summary, keywords)


def _naming(lang: str, json_name: str) -> str:
    """Explain how ASM JSON member names map to *lang* identifiers."""
    if lang == "typescript-angular":
        return f"Interface members keep the ASM JSON names: `document['{json_name}']`."
    accessor = _accessor(lang, [json_name])
    return f"Members follow the ASM JSON names: `\"{json_name}\"` is `{accessor}`."
