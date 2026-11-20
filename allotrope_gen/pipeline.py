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

After each generator run the output is patched through the two entry points
of :mod:`~allotrope_gen.patch`; the patch catalogue lives there.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
import subprocess
import sys
from pathlib import Path

from .command import build_cmd, build_commons_cmd, interpolate, resolve_version
from .config import COMMON_YAML_FILES, LANGUAGES, OUTPUT, SPECS
from .ontology import enrich_spec_descriptions
from .patch import CommonsDependency, PatchError, PatchTargets, patch_commons_output, patch_spec_output
from .schema import (
    bundle_spec,
    load_yaml,
    merged_commons_schemas,
    merged_commons_yaml,
    nan_capable_properties,
    primitive_unions,
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
    ``openapi-generator-cli`` once per language and patches the output with
    :func:`~allotrope_gen.patch.patch_commons_output`.

    Args:
        langs:    Language keys from :data:`~allotrope_gen.config.LANGUAGES`.
        dry_run:  Pass through to :func:`run` and :func:`clean_output`.
        no_clean: Pass through to :func:`clean_output`.

    Returns:
        ``True`` if every language succeeded, ``False`` if any failed.
    """
    all_ok = True
    targets = patch_targets(merged_commons_schemas())
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
            all_ok &= _patched(
                patch_commons_output, cfg.generator, out, cfg.package_fn(""), targets, dry_run,
            )
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
    mappings to the commons package, and then patches the output with
    :func:`~allotrope_gen.patch.patch_spec_output`, which also declares the
    commons package as a dependency (see :func:`commons_dependency`).

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
        targets = patch_targets(load_yaml(bundled_path)["components"]["schemas"], exclude=common_schemas)

        for lang in langs:
            cfg = LANGUAGES[lang]
            out = OUTPUT / spec / cfg.output_subdir
            clean_output(out, dry_run=dry_run, no_clean=no_clean)
            out.mkdir(parents=True, exist_ok=True)
            print(f"\n[{spec}] -> {lang}")

            cmd = build_cmd(spec, bundled_path, cfg, common_schemas, out, prerelease)
            if run(cmd, dry_run):
                commons = commons_dependency(lang, common_schemas, prerelease) if common_schemas else None
                all_ok &= _patched(
                    patch_spec_output, cfg.generator, out, cfg.package_fn(spec), targets, commons, dry_run,
                )
            else:
                all_ok = False

    return all_ok


def patch_targets(schemas: dict[str, dict], exclude: set[str] = frozenset()) -> PatchTargets:
    """Return the schema-driven patch targets of *schemas*.

    Args:
        schemas: ``components/schemas`` of the document handed to the generator.
        exclude: Schemas not generated in the output (mapped onto commons).
    """
    return PatchTargets(
        nan_properties={
            name: props for name, props in nan_capable_properties(schemas).items() if name not in exclude
        },
        primitive_unions=[name for name in primitive_unions(schemas) if name not in exclude],
    )


def commons_dependency(lang: str, common_schemas: set[str], prerelease: str | None = None) -> CommonsDependency:
    """Describe the commons package a spec package of *lang* depends on.

    The version is the commons version of the same run, including the
    pre-release label, resolved from ``cfg.commons_version``.

    Args:
        lang:           Language key from :data:`~allotrope_gen.config.LANGUAGES`.
        common_schemas: Commons schemas the spec package references.
        prerelease:     Optional pre-release label (``beta.1``).
    """
    cfg = LANGUAGES[lang]
    name = interpolate(cfg.extra_props["artifactId"], "") if cfg.generator == "java" else cfg.package_fn("")
    return CommonsDependency(
        name=name,
        version=resolve_version(cfg.commons_version, "", prerelease),
        schemas=frozenset(common_schemas),
        maven_group=cfg.extra_props.get("groupId", "") if cfg.generator == "java" else "",
    )


def _patched(patch: Callable[..., None], *args: object) -> bool:
    """Call a patch entry point; report a :class:`PatchError` and return ``False``.

    A generated output that no longer matches a patch fails the run instead
    of silently losing the fix.
    """
    try:
        patch(*args)
    except PatchError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return False
    return True
