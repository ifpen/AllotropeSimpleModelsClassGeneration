#!/usr/bin/env python3
"""Build generated language clients using the SDKs in the current environment.

This is intended to run inside the repository Dev Container, which provides the
same pinned toolchain locally and in CI. Every requested module/language pair
must have generated output and a supported build manifest; missing inputs are
errors rather than silently skipped checks.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from allotrope_gen.config import LANGUAGES, OUTPUT, SPECS


BUILD_COMMANDS: dict[str, tuple[tuple[str, ...], ...]] = {
    "java": (("mvn", "--batch-mode", "-DskipTests", "compile"),),
    "csharp": (("dotnet", "build", "--configuration", "Release"),),
    "python": (("python", "-m", "build"),),
    # Generated clients have no lockfile. Install dev dependencies without
    # running the package's prepare hook, then invoke the Angular build itself.
    "typescript-angular": (("npm", "install", "--ignore-scripts"), ("npm", "run", "build")),
}


def verify_module_lang(
    module: str,
    lang: str,
    *,
    dry_run: bool = False,
) -> bool:
    """Build one generated module with its native language toolchain."""
    output_dir = OUTPUT / module / LANGUAGES[lang].output_subdir
    if lang == "typescript-angular" and module == "commons":
        output_dir /= "common"
    if not output_dir.is_dir():
        print(f"[ERROR] Generated output is missing for {module} ({lang}): {output_dir}", file=sys.stderr)
        return False

    commands = BUILD_COMMANDS.get(lang)
    if commands is None:
        print(f"[ERROR] No build command configured for language: {lang}", file=sys.stderr)
        return False

    required_manifest = {
        "java": "pom.xml",
        "csharp": "*.csproj",
        "python": "pyproject.toml",
        "typescript-angular": "package.json",
    }[lang]
    manifests = list(output_dir.glob(required_manifest))
    if not manifests:
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

    try:
        for command in commands:
            result = subprocess.run(command, cwd=output_dir, check=False)
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
    """Verify all requested module/language pairs, returning False on any failure."""
    success = True
    for module in modules:
        for lang in langs:
            if not verify_module_lang(module, lang, dry_run=dry_run):
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
        help="Languages to verify (java, csharp, python, typescript-angular). Default is all.",
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
