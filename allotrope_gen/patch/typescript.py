"""
TypeScript (``typescript-angular``) patches.

* :func:`add_peer_dependency` — spec outputs.  Angular libraries list shared
  runtime packages as peers so an application installs a single copy; the
  commons package is shared by every spec package.
* :func:`allow_nan_strings` — properties marked ``x-asm-nan``.  ASM writes an
  unavailable quantity as the JSON string ``"NaN"``; the generated
  ``value: number`` becomes ``value: number | 'NaN'`` so such documents
  type-check.

``oneOf`` primitive/object unions need no patch: the generator emits a
TypeScript union type.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .common import lower_camel, replace_exact, report, write_text


def add_peer_dependency(package_json: Path, name: str, version: str, dry_run: bool = False) -> None:
    """Declare *name* as a peer dependency of a generated library (idempotent).

    Args:
        package_json: Generated ``package.json``.
        name:         npm package name of the dependency.
        version:      Exact dependency version.
        dry_run:      When ``True``, report but do not write.
    """
    if not package_json.exists():
        print(f"[WARN] package.json not found, skipping patch: {package_json}", file=sys.stderr)
        return
    manifest = json.loads(package_json.read_text(encoding="utf-8"))
    peers = manifest.setdefault("peerDependencies", {})
    if peers.get(name) == version:
        report("package.json patch", f"{name} peer dependency already present, skipping.")
        return
    peers[name] = version
    report("package.json patch", f"added peer dependency {name}@{version}")
    write_text(package_json, json.dumps(manifest, indent=2) + "\n", dry_run)


def allow_nan_strings(output_dir: Path, nan_properties: dict[str, list[str]], dry_run: bool = False) -> None:
    """Type NaN-capable number properties as ``number | 'NaN'`` (idempotent).

    Args:
        output_dir:     Generated TypeScript output directory.
        nan_properties: ``{class name: [JSON property names]}`` of the classes
                        generated in this output.
        dry_run:        When ``True``, report but do not write.

    Raises:
        PatchError: If a property declaration is not ``<name>: number;``.
    """
    patched = 0
    for name, props in nan_properties.items():
        source = output_dir / "model" / f"{lower_camel(name)}.ts"
        if not source.exists():
            continue
        text = source.read_text(encoding="utf-8")
        if "| 'NaN'" in text:
            continue
        for prop in props:
            text = replace_exact(text, rf"^(\s+'?{re.escape(prop)}'?\??: number)(;)", r"\1 | 'NaN'\2", source)
        patched += 1
        write_text(source, text, dry_run)
    report("nan patch", f"typescript: {patched} interface(s) accept the ASM \"NaN\" string")
