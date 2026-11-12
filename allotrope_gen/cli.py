"""
Command-line interface entry point.

Parses arguments and delegates to :func:`~allotrope_gen.pipeline.generate_commons`
and :func:`~allotrope_gen.pipeline.generate_specs`.

Usage::

    python generate.py                        # generate everything
    python generate.py --specs gc hplc       # only these specs
    python generate.py --langs java python   # only these languages
    python generate.py --dry-run             # print commands, do not execute
    python generate.py --no-clean            # skip output dir removal
    python generate.py --commons-only        # skip instrument-spec generation
    python generate.py --no-verify-builds     # skip builds after generation
    python generate.py --list-specs          # print registered spec keys
    python generate.py --list-langs          # print supported language keys
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .command import generator_cli
from .config import LANGUAGES, ROOT, SPECS


def generate_commons(*args, **kwargs) -> bool:
    """Load and invoke commons generation after prerequisite checks pass."""
    from .pipeline import generate_commons as _generate_commons

    return _generate_commons(*args, **kwargs)


def generate_specs(*args, **kwargs) -> bool:
    """Load and invoke spec generation after prerequisite checks pass."""
    from .pipeline import generate_specs as _generate_specs

    return _generate_specs(*args, **kwargs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--specs", nargs="+", default=list(SPECS), metavar="SPEC",
        help="Instrument specs to generate (default: all registered specs).",
    )
    parser.add_argument(
        "--langs", nargs="+", default=list(LANGUAGES), metavar="LANG",
        help="Target languages to generate (default: all supported languages).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print generator commands without executing them.",
    )
    parser.add_argument(
        "--no-clean", action="store_true",
        help="Skip removal of output directories before generation.",
    )
    parser.add_argument(
        "--commons-only", action="store_true",
        help="Generate only the commons libraries; skip instrument specs.",
    )
    parser.add_argument(
        "--no-verify-builds", action="store_true",
        help="Skip building generated clients (verification is enabled by default).",
    )
    parser.add_argument(
        "--list-specs", action="store_true",
        help="Print all registered spec keys and exit.",
    )
    parser.add_argument(
        "--list-langs", action="store_true",
        help="Print all supported language keys and exit.",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> int:
    """Return a non-zero exit code and print errors for unknown keys."""
    rc = 0
    unknown_specs = set(args.specs) - set(SPECS)
    unknown_langs = set(args.langs) - set(LANGUAGES)
    if unknown_specs:
        print(f"[ERROR] Unknown spec(s): {sorted(unknown_specs)}", file=sys.stderr)
        print(f"        Valid specs: {list(SPECS)}", file=sys.stderr)
        rc = 1
    if unknown_langs:
        print(f"[ERROR] Unknown language(s): {sorted(unknown_langs)}", file=sys.stderr)
        print(f"        Valid languages: {list(LANGUAGES)}", file=sys.stderr)
        rc = 1
    return rc


def _check_version(
    label: str,
    command: list[str],
    pattern: str,
    minimum: tuple[int, ...],
    *,
    exact: bool = False,
) -> bool:
    """Run a tool's version command and check it against a minimum version."""
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=120 if label == "OpenAPI Generator CLI" else 15,
            shell=(sys.platform == "win32" and label == "OpenAPI Generator CLI"),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[ERROR] Could not check {label}: {exc}", file=sys.stderr)
        return False

    output = f"{result.stdout}\n{result.stderr}"
    match = re.search(pattern, output, re.IGNORECASE)
    if match is None:
        print(
            f"[ERROR] Could not determine {label} version from: {output.strip()!r}",
            file=sys.stderr,
        )
        return False

    version = tuple(int(part) for part in match.group(1).split("."))
    version_mismatch = version != minimum if exact else version < minimum
    if version_mismatch:
        requirement = (
            "the pinned version"
            if exact
            else f"{'.'.join(map(str, minimum))} or newer"
        )
        print(
            f"[ERROR] {label} {requirement} is required "
            f"(found {'.'.join(map(str, version))}).",
            file=sys.stderr,
        )
        return False
    return True


def _resolve_java() -> str | None:
    """Find Java on PATH, or expose the executable under ``JAVA_HOME``.

    When Java is found under ``JAVA_HOME``, its ``bin`` directory is prepended
    to this process's PATH so child processes (notably the OpenAPI Generator
    CLI) can also resolve ``java``. The caller's parent shell is unaffected.
    """
    java = shutil.which("java")
    if java is not None:
        return java

    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        java_bin = Path(java_home) / "bin"
        executable_name = "java.exe" if sys.platform == "win32" else "java"
        candidate = java_bin / executable_name
        if candidate.is_file():
            os.environ["PATH"] = os.pathsep.join(
                [str(java_bin), os.environ.get("PATH", "")]
            )
            print(f"[INFO] Added JAVA_HOME Java to PATH for this run: {java_bin}")
            return str(candidate)

        print(
            f"[ERROR] JAVA_HOME is set but Java was not found at {candidate}.",
            file=sys.stderr,
        )
        return None

    return None


def check_prerequisites(*, dry_run: bool = False) -> bool:
    """Check the runtime prerequisites needed by the requested operation.

    PyYAML is always required because even a dry run parses and merges the
    OpenAPI YAML files. The external generation toolchain is not needed for a
    dry run. npm is intentionally not checked: it is only needed to install
    the already-invoked ``openapi-generator-cli`` wrapper.
    """
    ok = True
    if sys.version_info < (3, 12):
        print(
            f"[ERROR] Python 3.12 or newer is required (found {sys.version.split()[0]}).",
            file=sys.stderr,
        )
        ok = False

    if importlib.util.find_spec("yaml") is None:
        print(
            "[ERROR] PyYAML is not installed. Install it with: "
            "python -m pip install pyyaml",
            file=sys.stderr,
        )
        ok = False

    if not ok:
        print(
            f"[ERROR] Generation prerequisites are missing or invalid. See "
            f"{ROOT / 'README.md'} for setup instructions.",
            file=sys.stderr,
        )
        return False

    if dry_run:
        return ok

    node = shutil.which("node")
    node_ok = node is not None
    if node is None:
        print(
            "[ERROR] Node.js was not found on PATH. Install Node.js 20 or newer.",
            file=sys.stderr,
        )
        ok = False
    else:
        node_ok = _check_version(
            "Node.js", [node, "--version"], r"v?(\d+(?:\.\d+)+)", (20,)
        )
        ok = node_ok and ok

    java = _resolve_java()
    java_ok = java is not None
    if java is None:
        print(
            "[ERROR] Java was not found on PATH or under JAVA_HOME. Install JDK "
            "17 or newer, then add its bin directory to PATH or set JAVA_HOME.",
            file=sys.stderr,
        )
        ok = False
    else:
        java_ok = _check_version(
            "Java",
            [java, "-version"],
            r'(?:version\s+"|(?:openjdk|java)\s+)(\d+(?:\.\d+)+)',
            (17,),
        )
        ok = java_ok and ok

    cli_name = generator_cli()
    cli_path = shutil.which(cli_name)
    if cli_path is None:
        print(
            f"[ERROR] {cli_name} was not found on PATH. Install it with: "
            "npm install -g @openapitools/openapi-generator-cli",
            file=sys.stderr,
        )
        ok = False
    elif node_ok and java_ok:
        # The version command also confirms that the wrapper can launch its
        # pinned JAR. On first use this may download that JAR, as generation
        # itself would do; timeout/failure is reported cleanly here.
        try:
            tools_config = json.loads((ROOT / "openapitools.json").read_text(encoding="utf-8"))
            pinned_version = tools_config["generator-cli"]["version"]
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            print(f"[ERROR] Could not read the pinned OpenAPI Generator version: {exc}", file=sys.stderr)
            ok = False
        else:
            if not _check_version(
                "OpenAPI Generator CLI",
                [cli_path, "version"],
                r"(\d+(?:\.\d+)+)",
                tuple(int(part) for part in pinned_version.split(".")),
                exact=True,
            ):
                ok = False

    if not ok:
        print(
            f"[ERROR] Generation prerequisites are missing or invalid. See "
            f"{ROOT / 'README.md'} for setup instructions.",
            file=sys.stderr,
        )
    return ok


def verify_generated_builds(
    specs: list[str],
    langs: list[str],
    *,
    commons_only: bool,
) -> bool:
    """Build every module/language pair requested from the generator."""
    from verify_builds import verify_modules

    modules = ["commons"]
    if not commons_only:
        modules.extend(specs)
    return verify_modules(modules, langs)


def main(argv: list[str] | None = None) -> int:
    """Parse *argv* and run the generation pipeline.

    Args:
        argv: Argument list (defaults to :data:`sys.argv` when ``None``).

    Returns:
        ``0`` on success, ``1`` on any error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_specs:
        print("\n".join(SPECS))
        return 0
    if args.list_langs:
        print("\n".join(LANGUAGES))
        return 0

    if rc := _validate_args(args):
        return rc

    if not check_prerequisites(dry_run=args.dry_run):
        return 1

    ok = generate_commons(args.langs, dry_run=args.dry_run, no_clean=args.no_clean)

    if not args.commons_only:
        ok = generate_specs(
            args.specs, args.langs,
            dry_run=args.dry_run,
            no_clean=args.no_clean,
        ) and ok

    if ok and not args.dry_run and not args.no_verify_builds:
        print("\n[verify] Building generated clients...")
        ok = verify_generated_builds(
            args.specs,
            args.langs,
            commons_only=args.commons_only,
        )

    return 0 if ok else 1
