"""
YAML schema utilities.

Responsible for:

* Loading OpenAPI 3.1 YAML documents.
* Extracting the set of schema names from a document.
* Determining which commons schemas an instrument spec actually references
  (so ``--import-mappings`` stays minimal).
* Merging the commons YAML files into a single temporary document that the
  generator can consume as a single ``--input-spec``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from .config import COMMON_YAML_FILES

# Pre-compiled pattern that matches $ref values pointing to commons files:
#   $ref: './common.yaml#/components/schemas/Foo'
#   $ref: './datacube.yaml#/components/schemas/Foo'
_COMMONS_REF_RE = re.compile(
    r'\$ref:\s*[\'"]?\./(?:common|datacube)\.yaml#/components/schemas/(\w+)'
)


def load_yaml(path: Path) -> dict:
    """Load *path* as YAML and return the parsed document as a :class:`dict`."""
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def schema_names(doc: dict) -> set[str]:
    """Return the set of schema names declared under ``components/schemas``."""
    return set(doc.get("components", {}).get("schemas", {}).keys())


def collect_common_schemas(
    common_files: list[Path] | None = None,
) -> set[str]:
    """Return the union of all schema names across every commons YAML file.

    Args:
        common_files: Override the default :data:`~allotrope_gen.config.COMMON_YAML_FILES`.
            Primarily useful in tests.

    Returns:
        Set of schema names.  Missing files emit a warning to *stderr* and are
        skipped rather than raising.
    """
    files = COMMON_YAML_FILES if common_files is None else common_files
    names: set[str] = set()
    for path in files:
        if not path.exists():
            print(f"[WARN] Common file not found, skipping: {path}", file=sys.stderr)
            continue
        names |= schema_names(load_yaml(path))
    return names


def schemas_referenced_from_commons(
    spec_path: Path,
    common_files: list[Path] | None = None,
) -> set[str]:
    """Return the commons schema names that *spec_path* actually ``$ref``s.

    Only schemas appearing in *both* the commons files and the spec's ``$ref``
    expressions are returned.  This keeps ``--import-mappings`` minimal and
    avoids confusing generators with schemas the spec never uses.

    Args:
        spec_path:    Path to the instrument spec YAML file.
        common_files: Override for the commons file list (test helper).

    Returns:
        Intersection of commons-defined names and names referenced by the spec.
        Returns an empty set if *spec_path* does not exist.
    """
    common = collect_common_schemas(common_files)
    if not spec_path.exists():
        return set()
    raw = spec_path.read_text(encoding="utf-8")
    referenced = set(_COMMONS_REF_RE.findall(raw))
    return common & referenced


def merged_commons_yaml(
    output_dir: Path,
    common_files: list[Path] | None = None,
) -> Path:
    """Merge all commons YAML files into a single document in *output_dir*.

    The merged file (``commons-merged.yaml``) is passed as ``--input-spec``
    when generating the commons library.  Schema definitions that appear
    identically in multiple source files are silently deduplicated; conflicting
    definitions for the same schema name are a hard error.

    Args:
        output_dir:   Directory where ``commons-merged.yaml`` will be written.
        common_files: Override for the commons file list (test helper).

    Returns:
        Path to the written ``commons-merged.yaml`` file.

    Raises:
        SystemExit: If two source files define the same schema name with
            different content.  The collision must be resolved manually.
    """
    files = COMMON_YAML_FILES if common_files is None else common_files
    merged: dict = {
        "openapi": "3.1.0",
        "info": {"title": "ASM Commons", "version": "2025-03"},
        "components": {"schemas": {}},
    }
    schemas = merged["components"]["schemas"]

    for path in files:
        if not path.exists():
            print(f"[WARN] Common file not found, skipping: {path}", file=sys.stderr)
            continue
        doc = load_yaml(path)
        for name, definition in doc.get("components", {}).get("schemas", {}).items():
            if name in schemas:
                if schemas[name] != definition:
                    print(
                        f"[ERROR] Schema collision in commons: '{name}' is defined"
                        f" differently in multiple files. Resolve manually.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                # Identical definition — silently deduplicate.
            else:
                schemas[name] = definition

    merged_path = output_dir / "commons-merged.yaml"
    merged_path.write_text(
        yaml.dump(merged, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return merged_path
