"""
Generation pipeline: subprocess runner, output cleaning, and orchestration.

This module wires together the lower-level utilities from
:mod:`~allotrope_gen.schema`, :mod:`~allotrope_gen.command`, and
:mod:`~allotrope_gen.patch` into the two top-level operations that the CLI
invokes:

* :func:`generate_commons` — merge commons YAML files and run the generator
  for each requested language.
* :func:`generate_specs` — bundle each spec with the commons schemas it
  reaches, run the generator for each language with import/schema mappings
  to the commons package, and declare the commons dependency.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .command import build_cmd, build_commons_cmd, interpolate, resolve_version
from .config import COMMON_YAML_FILES, LANGUAGES, OUTPUT, SPECS, LanguageConfig
from .ontology import enrich_spec_descriptions
from .patch import (
    add_csharp_commons_registry,
    add_csharp_package_reference,
    add_java_dependency,
    add_npm_peer_dependency,
    PatchError,
    patch_java_pom,
    patch_csharp_additional_properties,
    patch_csharp_optional_enum_writes,
    patch_nan_support,
    patch_python_package,
    register_csharp_commons_converters,
)
from .schema import (
    bundle_spec,
    load_yaml,
    merged_commons_schemas,
    merged_commons_yaml,
    nan_capable_properties,
)

#: Directory for self-contained instrument specs handed to the generator.
BUNDLED: Path = OUTPUT.parent / "bundled-specs"


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------


def run(cmd: list[str], dry_run: bool) -> bool:
    """Execute *cmd*, printing it first for transparency.

    On Windows, ``.cmd`` wrappers installed by npm require ``shell=True`` to be
    invoked correctly by ``subprocess``; this is the *only* place where
    platform-specific subprocess behaviour lives.

    Args:
        cmd:     Argument list to execute.
        dry_run: When ``True``, print the command and return ``True`` without
                 executing it.

    Returns:
        ``True`` on success (or dry-run), ``False`` if the process exits with a
        non-zero return code.
    """
    print("  $ " + " ".join(cmd))
    if dry_run:
        print("  [dry-run]")
        return True
    result = subprocess.run(cmd, shell=(sys.platform == "win32"))
    if result.returncode != 0:
        print(f"[ERROR] Process exited with code {result.returncode}", file=sys.stderr)
        return False
    return True


# ---------------------------------------------------------------------------
# Output directory management
# ---------------------------------------------------------------------------


def clean_output(output_dir: Path, *, dry_run: bool, no_clean: bool) -> None:
    """Remove *output_dir* before regeneration, unless suppressed.

    Args:
        output_dir: Directory to remove.
        dry_run:    When ``True``, print the action but do not delete.
        no_clean:   When ``True``, skip cleaning entirely (``--no-clean`` flag).
    """
    if no_clean or not output_dir.exists():
        return
    print(f"  [clean] {output_dir}")
    if not dry_run:
        shutil.rmtree(output_dir)


# ---------------------------------------------------------------------------
# Commons generation
# ---------------------------------------------------------------------------


def generate_commons(
    langs: list[str],
    *,
    dry_run: bool,
    no_clean: bool,
    prerelease: str | None = None,
) -> bool:
    """Generate the commons library for every requested language.

    Merges all commons YAML files into a single temporary document, then calls
    ``openapi-generator-cli`` once per language.  After Java generation,
    :func:`~allotrope_gen.patch.patch_java_pom` is applied automatically.

    Args:
        langs:    Language keys from :data:`~allotrope_gen.config.LANGUAGES`.
        dry_run:  Pass through to :func:`run` and :func:`clean_output`.
        no_clean: Pass through to :func:`clean_output`.

    Returns:
        ``True`` if every language succeeded, ``False`` if any failed.
    """
    all_ok = True
    for lang in langs:
        cfg = LANGUAGES[lang]
        out = OUTPUT / "commons" / cfg.output_subdir
        clean_output(out, dry_run=dry_run, no_clean=no_clean)
        out.mkdir(parents=True, exist_ok=True)

        merged_path = merged_commons_yaml(out)
        print(
            f"\n[commons] -> {lang}"
            f"  (merged: {', '.join(p.name for p in COMMON_YAML_FILES)})"
        )

        cmd = build_commons_cmd(merged_path, cfg, out, prerelease)
        if run(cmd, dry_run):
            if lang == "java":
                patch_java_pom(out / "pom.xml", dry_run)
            all_ok &= _patch_nan(
                cfg, out, "", nan_capable_properties(merged_commons_schemas()), dry_run,
            )
            if cfg.generator == "csharp":
                try:
                    patch_csharp_optional_enum_writes(out, dry_run)
                    patch_csharp_additional_properties(out, dry_run)
                    add_csharp_commons_registry(out, cfg.package_fn(""), dry_run)
                except PatchError as exc:
                    print(f"[ERROR] {exc}", file=sys.stderr)
                    all_ok = False
        else:
            all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# Instrument-spec generation
# ---------------------------------------------------------------------------


def generate_specs(
    specs: list[str],
    langs: list[str],
    *,
    dry_run: bool,
    no_clean: bool,
    prerelease: str | None = None,
) -> bool:
    """Generate instrument-spec libraries for every requested (spec, language) pair.

    For each spec the function bundles the commons schemas it reaches into a
    self-contained copy (see :func:`~allotrope_gen.schema.bundle_spec`), calls
    ``openapi-generator-cli`` for each language with import and schema
    mappings to the commons package, and then declares the commons package as
    a dependency of the generated package (see :func:`declare_commons_dependency`).

    Args:
        specs:    Spec keys from :data:`~allotrope_gen.config.SPECS`.
        langs:    Language keys from :data:`~allotrope_gen.config.LANGUAGES`.
        dry_run:  Pass through to :func:`run` and :func:`clean_output`.
        no_clean: Pass through to :func:`clean_output`.

    Returns:
        ``True`` if every (spec, language) pair succeeded, ``False`` otherwise.
    """
    all_ok = True
    for spec in specs:
        spec_path = SPECS[spec]
        if not spec_path.exists():
            print(f"[ERROR] Spec file not found: {spec_path}", file=sys.stderr)
            all_ok = False
            continue

        if not dry_run:
            enrich_spec_descriptions(spec_path)

        bundled_path, common_schemas = bundle_spec(spec_path, BUNDLED)
        print(f"\n[{spec}] common schemas reachable: {sorted(common_schemas)}")
        # Mapped commons classes are patched once, in the commons output.
        nan_properties = {
            name: props
            for name, props in nan_capable_properties(
                load_yaml(bundled_path)["components"]["schemas"]
            ).items()
            if name not in common_schemas
        }

        for lang in langs:
            cfg = LANGUAGES[lang]
            out = OUTPUT / spec / cfg.output_subdir
            clean_output(out, dry_run=dry_run, no_clean=no_clean)
            out.mkdir(parents=True, exist_ok=True)
            print(f"\n[{spec}] -> {lang}")

            cmd = build_cmd(spec, bundled_path, cfg, common_schemas, out, prerelease)
            if run(cmd, dry_run):
                if lang == "java":
                    patch_java_pom(out / "pom.xml", dry_run)
                if common_schemas:
                    try:
                        declare_commons_dependency(
                            spec, lang, out, common_schemas, dry_run, prerelease,
                        )
                    except PatchError as exc:
                        print(f"[ERROR] {exc}", file=sys.stderr)
                        all_ok = False
                all_ok &= _patch_nan(cfg, out, spec, nan_properties, dry_run)
                if cfg.generator == "csharp":
                    try:
                        patch_csharp_optional_enum_writes(out, dry_run)
                        patch_csharp_additional_properties(out, dry_run)
                    except PatchError as exc:
                        print(f"[ERROR] {exc}", file=sys.stderr)
                        all_ok = False
            else:
                all_ok = False

    return all_ok


def declare_commons_dependency(
    spec: str,
    lang: str,
    output_dir: Path,
    common_schemas: set[str],
    dry_run: bool,
    prerelease: str | None = None,
) -> None:
    """Declare the commons package as a dependency of a generated spec package.

    The dependency version is the commons version of the same run, including
    the pre-release label, resolved from ``cfg.commons_version``.

    Args:
        spec:           Spec identifier (e.g. ``"gc"``).
        lang:           Language key from :data:`~allotrope_gen.config.LANGUAGES`.
        output_dir:     Generated output directory for the pair.
        common_schemas: Commons schemas the spec package references.
        dry_run:        When ``True``, report but do not modify any file.
        prerelease:     Optional pre-release label (``beta.1``).
    """
    cfg = LANGUAGES[lang]
    commons_name = cfg.package_fn("")
    version = resolve_version(cfg.commons_version, "", prerelease)
    if cfg.generator == "java":
        add_java_dependency(
            output_dir / "pom.xml",
            cfg.extra_props["groupId"],
            interpolate(cfg.extra_props["artifactId"], ""),
            version,
            dry_run,
        )
    elif cfg.generator == "csharp":
        add_csharp_package_reference(output_dir, commons_name, version, dry_run)
        register_csharp_commons_converters(output_dir, commons_name, dry_run)
    elif cfg.generator == "typescript-angular":
        add_npm_peer_dependency(output_dir / "package.json", commons_name, version, dry_run)
    elif cfg.generator == "python":
        patch_python_package(
            output_dir,
            cfg.package_fn(spec),
            commons_name,
            version,
            common_schemas,
            dry_run,
        )


def _patch_nan(
    cfg: LanguageConfig,
    output_dir: Path,
    spec: str,
    nan_properties: dict[str, list[str]],
    dry_run: bool,
) -> bool:
    """Apply :func:`~allotrope_gen.patch.patch_nan_support`; report failures.

    Returns:
        ``False`` (after printing the error) if the generated code no longer
        matches the patch, so the run fails instead of silently losing NaN
        support.
    """
    try:
        patch_nan_support(cfg.generator, output_dir, cfg.package_fn(spec), nan_properties, dry_run)
    except PatchError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return False
    return True
