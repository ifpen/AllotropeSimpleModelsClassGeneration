"""
Post-generation patches of the code emitted by openapi-generator.

openapi-generator cannot express a few requirements of this project
(publishing metadata, packages split into commons + spec packages, ASM JSON
conventions), and some of its templates are buggy.  This package edits the
generated code after each generator run.  The pipeline only calls the two
entry points below; they decide which patch applies to which output.

Catalogue
=========

Each row is one problem; *Where* says which outputs are patched.

=======================  ==========  ========================================================
Problem                  Where       Patch per language
=======================  ==========  ========================================================
Maven Central needs      commons +   Java: :func:`java.add_central_publishing_plugin`
the publishing plugin    specs
-----------------------  ----------  --------------------------------------------------------
Spec packages use the    specs       Java: :func:`java.add_dependency`;
commons classes (import              C#: :func:`csharp.add_package_reference`,
/schema mappings) and                :func:`csharp.register_commons_converters`;
must depend on commons               TypeScript: :func:`typescript.add_peer_dependency`;
                                     Python: :func:`python.depend_on_commons`
-----------------------  ----------  --------------------------------------------------------
Spec serializers need    commons     C#: :func:`csharp.add_commons_registry`
the commons converters
-----------------------  ----------  --------------------------------------------------------
ASM ``"NaN"`` string     commons +   Python: :func:`python.allow_nan_strings`;
for unavailable numbers  specs       TypeScript: :func:`typescript.allow_nan_strings`;
(``x-asm-nan``)                      C#: :func:`csharp.patch_doubles`; Java: native
-----------------------  ----------  --------------------------------------------------------
.NET Framework writes    commons +   C#: :func:`csharp.patch_doubles` (issue #13)
17-digit doubles         specs
-----------------------  ----------  --------------------------------------------------------
Primitive/object         commons +   C#: :func:`csharp.patch_primitive_unions` (issue #12);
``oneOf`` unions         specs       Java, Python, TypeScript: native
-----------------------  ----------  --------------------------------------------------------
Unset optional enums     commons +   C#: :func:`csharp.guard_optional_enum_writes`
throw on serialization   specs
-----------------------  ----------  --------------------------------------------------------
``additionalProperties`` commons +   C#: :func:`csharp.keep_additional_properties`
are lost                 specs
=======================  ==========  ========================================================

Conventions
===========

* Every patch is **idempotent**: running it twice changes nothing.
* Patches that rewrite generated code **fail loudly**: they raise
  :class:`PatchError` when the code no longer has the expected shape, so a
  generator upgrade cannot silently drop a fix (see :mod:`.common`).
* Classes mapped onto commons are absent from spec outputs and are patched
  once, in the commons output; callers pass only the schemas generated in
  the output being patched.
* Source files added to the generated code are real files in
  ``templates/`` (see :func:`.common.render_template`).
* A new patch gets a row in the catalogue above, a call in
  :func:`patch_commons_output` and/or :func:`patch_spec_output`, and unit
  tests in ``tests/test_patch_<language>.py``.  Behaviour that generated
  code must have end to end is checked by ``verify_deserialization.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import csharp, java, python, typescript
from .common import PatchError

__all__ = [
    "CommonsDependency",
    "PatchError",
    "PatchTargets",
    "csharp",
    "java",
    "patch_commons_output",
    "patch_spec_output",
    "python",
    "typescript",
]


@dataclass(frozen=True)
class PatchTargets:
    """Schemas generated in one output that need a schema-driven patch.

    Attributes:
        nan_properties:   ``{class name: [JSON property names]}`` of
                          NaN-capable numbers
                          (:func:`allotrope_gen.schema.nan_capable_properties`).
        primitive_unions: ``oneOf`` primitive/object union schema names
                          (:func:`allotrope_gen.schema.primitive_unions`).
    """

    nan_properties: dict[str, list[str]]
    primitive_unions: list[str]


@dataclass(frozen=True)
class CommonsDependency:
    """The commons package a spec package depends on, in one language.

    Attributes:
        name:       Package name/namespace (Maven ``artifactId``, NuGet id,
                    npm name or Python package).
        version:    Exact version, including any pre-release label.
        schemas:    Commons schema names the spec references.
        maven_group: Maven ``groupId`` (Java only).
    """

    name: str
    version: str
    schemas: frozenset[str]
    maven_group: str = ""


def patch_commons_output(
    generator: str,
    output_dir: Path,
    namespace: str,
    targets: PatchTargets,
    dry_run: bool = False,
) -> None:
    """Apply every commons-package patch for *generator*.

    Args:
        generator:  openapi-generator name (``java``, ``csharp``, ``python``,
                    ``typescript-angular``).
        output_dir: Generated commons output directory.
        namespace:  Commons package/namespace in that language.
        targets:    Schema-driven patch targets of the commons schemas.
        dry_run:    When ``True``, report but do not modify any file.

    Raises:
        PatchError: If generated code no longer has an expected shape.
    """
    if generator == "java":
        java.add_central_publishing_plugin(output_dir / "pom.xml", dry_run)
    elif generator == "csharp":
        _patch_csharp_converters(output_dir, namespace, targets, dry_run)
        csharp.add_commons_registry(output_dir, namespace, dry_run)
        csharp.patch_doubles(output_dir, namespace, targets.nan_properties, register_converter=True, dry_run=dry_run)
    elif generator == "python":
        python.allow_nan_strings(output_dir, namespace, targets.nan_properties, dry_run)
    elif generator == "typescript-angular":
        typescript.allow_nan_strings(output_dir, targets.nan_properties, dry_run)


def patch_spec_output(
    generator: str,
    output_dir: Path,
    package: str,
    targets: PatchTargets,
    commons: CommonsDependency | None,
    dry_run: bool = False,
) -> None:
    """Apply every spec-package patch for *generator*.

    Args:
        generator:  openapi-generator name.
        output_dir: Generated spec output directory.
        package:    Spec package/namespace in that language.
        targets:    Schema-driven patch targets of the schemas generated in
                    this output (commons-mapped schemas excluded).
        commons:    Commons package to depend on, or ``None`` when the spec
                    references no commons schema.
        dry_run:    When ``True``, report but do not modify any file.

    Raises:
        PatchError: If generated code no longer has an expected shape.
    """
    if generator == "java":
        java.add_central_publishing_plugin(output_dir / "pom.xml", dry_run)
        if commons:
            java.add_dependency(output_dir / "pom.xml", commons.maven_group, commons.name, commons.version, dry_run)
    elif generator == "csharp":
        if commons:
            csharp.add_package_reference(output_dir, commons.name, commons.version, dry_run)
            csharp.register_commons_converters(output_dir, commons.name, dry_run)
        _patch_csharp_converters(output_dir, package, targets, dry_run)
        csharp.patch_doubles(output_dir, package, targets.nan_properties, register_converter=False, dry_run=dry_run)
    elif generator == "python":
        if commons:
            python.depend_on_commons(output_dir, package, commons.name, commons.version, set(commons.schemas), dry_run)
        python.allow_nan_strings(output_dir, package, targets.nan_properties, dry_run)
    elif generator == "typescript-angular":
        if commons:
            typescript.add_peer_dependency(output_dir / "package.json", commons.name, commons.version, dry_run)
        typescript.allow_nan_strings(output_dir, targets.nan_properties, dry_run)


def _patch_csharp_converters(output_dir: Path, namespace: str, targets: PatchTargets, dry_run: bool) -> None:
    """Apply the C# converter fixes shared by commons and spec outputs."""
    csharp.guard_optional_enum_writes(output_dir, dry_run)
    csharp.keep_additional_properties(output_dir, dry_run)
    csharp.patch_primitive_unions(output_dir, targets.primitive_unions, dry_run)
