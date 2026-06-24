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
    python generate.py --list-specs          # print registered spec keys
    python generate.py --list-langs          # print supported language keys
"""

from __future__ import annotations

import argparse
import sys

from .config import LANGUAGES, SPECS
from .pipeline import generate_commons, generate_specs


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

    ok = generate_commons(args.langs, dry_run=args.dry_run, no_clean=args.no_clean)

    if not args.commons_only:
        ok = generate_specs(
            args.specs, args.langs,
            dry_run=args.dry_run,
            no_clean=args.no_clean,
        ) and ok

    return 0 if ok else 1
