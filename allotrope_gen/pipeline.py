"""
Generation pipeline: subprocess runner, output cleaning, and orchestration.

This module wires together the lower-level utilities from
:mod:`~allotrope_gen.schema`, :mod:`~allotrope_gen.command`, and
:mod:`~allotrope_gen.patch` into the two top-level operations that the CLI
invokes:

* :func:`generate_commons` — merge commons YAML files and run the generator
  for each requested language.
* :func:`generate_specs` — for each (spec, language) pair, compute
  ``--import-mappings`` and run the generator.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .command import build_cmd, build_commons_cmd
from .config import COMMON_YAML_FILES, LANGUAGES, OUTPUT, SPECS, LanguageConfig
from .patch import patch_java_pom
from .schema import merged_commons_yaml, schemas_referenced_from_commons


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

        cmd = build_commons_cmd(merged_path, cfg, out)
        if run(cmd, dry_run):
            if lang == "java":
                patch_java_pom(out / "pom.xml", dry_run)
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
) -> bool:
    """Generate instrument-spec libraries for every requested (spec, language) pair.

    For each spec the function first resolves which commons schemas are
    referenced (to build ``--import-mappings``), then calls
    ``openapi-generator-cli`` for each language.

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

        common_schemas = schemas_referenced_from_commons(spec_path)
        print(f"\n[{spec}] common schemas referenced: {sorted(common_schemas)}")

        for lang in langs:
            cfg = LANGUAGES[lang]
            out = OUTPUT / spec / cfg.output_subdir
            clean_output(out, dry_run=dry_run, no_clean=no_clean)
            out.mkdir(parents=True, exist_ok=True)
            print(f"\n[{spec}] -> {lang}")

            cmd = build_cmd(spec, spec_path, cfg, common_schemas, out)
            if run(cmd, dry_run):
                if lang == "java":
                    patch_java_pom(out / "pom.xml", dry_run)
            else:
                all_ok = False

    return all_ok
