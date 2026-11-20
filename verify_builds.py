#!/usr/bin/env python3
"""Build generated language clients using the SDKs in the current environment.

This is intended to run inside the repository Dev Container, which provides the
same pinned toolchain locally and in CI. Every requested module/language pair
must have generated output and a supported build manifest; missing inputs are
errors rather than silently skipped checks.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from allotrope_gen.config import LANGUAGES, OUTPUT, SPECS


#: Local package feeds where commons artefacts are published for spec builds.
LOCAL_PACKAGES: Path = ROOT / "target" / "local-packages"
#: Isolated NuGet cache: commons keeps the same version between generations,
#: so a shared cache could serve a stale commons build to the spec builds.
NUGET_PACKAGES: Path = ROOT / "target" / "nuget-packages"

#: Build manifest whose presence is required before building.
REQUIRED_MANIFESTS: dict[str, str] = {
    "java": "pom.xml",
    "csharp": "*.sln",
    "python": "pyproject.toml",
    "typescript": "package.json",
}


def build_commands(module: str, lang: str) -> list[tuple[str, ...]]:
    """Return the build commands for one module/language pair.

    Instrument packages depend on the commons package, so commons builds also
    publish their artefact locally where the spec builds resolve it:

    * Java installs every module into the local Maven repository;
    * C# packs commons into a local NuGet feed used as an extra restore source;
    * TypeScript packs the built commons library into an npm tarball that the
      spec build installs to satisfy its peer dependency;
    * Python builds need no dependency resolution.
    """
    commons = module == "commons"
    if lang == "java":
        return [("mvn", "--batch-mode", "-DskipTests", "install")]
    if lang == "csharp":
        feed = LOCAL_PACKAGES / "nuget"
        if commons:
            return [("dotnet", "pack", "--configuration", "Release", "--output", str(feed))]
        return [("dotnet", "build", "--configuration", "Release",
                 f"-p:RestoreAdditionalProjectSources={feed}")]
    if lang == "python":
        return [("python", "-m", "build")]
    if lang == "typescript":
        # Generated packages have no lockfile. Install the TypeScript compiler
        # without running the package's prepare hook, then build with tsc.
        # The package is packed from its root (``files``: dist/).
        tarballs = LOCAL_PACKAGES / "npm"
        if commons:
            return [
                ("npm", "install", "--ignore-scripts"),
                ("npm", "run", "build"),
                ("npm", "pack", "--ignore-scripts", "--pack-destination", str(tarballs)),
            ]
        return [
            ("npm", "install", "--ignore-scripts", "--no-save", *map(str, sorted(tarballs.glob("*.tgz")))),
            ("npm", "run", "build"),
        ]
    return []


def verify_module_lang(
    module: str,
    lang: str,
    *,
    dry_run: bool = False,
) -> bool:
    """Build one generated module with its native language toolchain."""
    output_dir = OUTPUT / module / LANGUAGES[lang].output_subdir
    if not output_dir.is_dir():
        print(f"[ERROR] Generated output is missing for {module} ({lang}): {output_dir}", file=sys.stderr)
        return False

    commands = build_commands(module, lang)
    if not commands:
        print(f"[ERROR] No build command configured for language: {lang}", file=sys.stderr)
        return False

    required_manifest = REQUIRED_MANIFESTS[lang]
    if not list(output_dir.glob(required_manifest)):
        print(
            f"[ERROR] Build manifest {required_manifest!r} is missing for {module} ({lang}) in {output_dir}",
            file=sys.stderr,
        )
        return False

    print(f"\n--- Building {module} ({lang}) ---")
    print(f"Working directory: {output_dir}")
    for command in commands:
        print(f"Command: {' '.join(command)}")
    if dry_run:
        return True

    env = os.environ.copy()
    if lang == "csharp":
        env["NUGET_PACKAGES"] = str(NUGET_PACKAGES)
        if module == "commons":
            # Drop the previously extracted commons package (same version).
            commons_id = LANGUAGES[lang].package_fn("").lower()
            shutil.rmtree(NUGET_PACKAGES / commons_id, ignore_errors=True)
            shutil.rmtree(LOCAL_PACKAGES / "nuget", ignore_errors=True)
    if lang == "typescript" and module == "commons":
        shutil.rmtree(LOCAL_PACKAGES / "npm", ignore_errors=True)
        (LOCAL_PACKAGES / "npm").mkdir(parents=True, exist_ok=True)

    try:
        for command in commands:
            result = subprocess.run(command, cwd=output_dir, env=env, check=False)
            if result.returncode != 0:
                return False
    except OSError as exc:
        print(f"[ERROR] Could not run build command for {module} ({lang}): {exc}", file=sys.stderr)
        return False
    return True


def verify_modules(
    modules: list[str],
    langs: list[str],
    *,
    dry_run: bool = False,
) -> bool:
    """Verify all requested module/language pairs, returning False on any failure.

    Commons is built first; it is added automatically when only instrument
    modules are requested, because their builds resolve the commons package.
    """
    ordered = ["commons", *[m for m in modules if m != "commons"]]
    success = True
    for lang in langs:
        commons_ok = True
        for module in ordered:
            if module != "commons" and not commons_ok:
                print(f"[FAIL] Skipping {module} ({lang}): commons did not build", file=sys.stderr)
                success = False
                continue
            ok = verify_module_lang(module, lang, dry_run=dry_run)
            if module == "commons":
                commons_ok = ok
            if not ok:
                print(f"[FAIL] Build failed for module: {module}, language: {lang}", file=sys.stderr)
                success = False

    if success:
        print("\n[SUCCESS] All requested builds completed successfully!")
    else:
        print("\n[FAILURE] One or more requested builds failed.", file=sys.stderr)
    return success


def main(argv: list[str] | None = None) -> int:
    """Verify generated output selected through the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--specs", nargs="+", default=["commons", *SPECS],
        help="Modules to verify (commons, gc, etc.). Default is all.",
    )
    parser.add_argument(
        "--langs", nargs="+", default=list(LANGUAGES),
        help="Languages to verify (java, csharp, python, typescript). Default is all.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print build commands without running them.")
    args = parser.parse_args(argv)

    unknown_langs = set(args.langs) - set(LANGUAGES)
    unknown_modules = set(args.specs) - {"commons", *SPECS}
    if unknown_langs:
        print(f"[ERROR] Unknown language(s): {sorted(unknown_langs)}", file=sys.stderr)
        return 1
    if unknown_modules:
        print(f"[ERROR] Unknown module(s): {sorted(unknown_modules)}", file=sys.stderr)
        return 1

    return 0 if verify_modules(args.specs, args.langs, dry_run=args.dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
