"""
YAML schema utilities.

Responsible for:

* Loading OpenAPI 3.1 YAML documents.
* Extracting the set of schema names from a document.
* Determining which commons schemas an instrument spec actually references
  (so ``--import-mappings`` stays minimal).
* Merging the commons YAML files into a single temporary document that the
  generator can consume as a single ``--input-spec``.
* Bundling an instrument spec with the commons schemas it reaches, so the
  generator keeps commons schema names and honours schema mappings.
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import yaml

from .config import COMMON_YAML_FILES, COMMONS_VERSION

# Pre-compiled pattern for parsed $ref values that point to commons files.
_COMMONS_REF_RE = re.compile(
    r"^\./[\w-]+\.yaml#/components/schemas/(\w+)$"
)
_MERGED_SCHEMA_REF_RE = re.compile(
    r"^\./[\w-]+\.yaml#/components/schemas/([\w-]+)$"
)
_LOCAL_SCHEMA_PREFIX = "#/components/schemas/"


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
    if not spec_path.exists():
        return set()
    common = collect_common_schemas(common_files)

    def visit(node: object) -> set[str]:
        referenced: set[str] = set()
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                match = _COMMONS_REF_RE.fullmatch(ref)
                if match:
                    referenced.add(match.group(1))
            for value in node.values():
                referenced.update(visit(value))
        elif isinstance(node, list):
            for value in node:
                referenced.update(visit(value))
        return referenced

    referenced = visit(load_yaml(spec_path))
    return common & referenced


def _rewrite_commons_refs(node: object, names: set[str]) -> set[str]:
    """Rewrite commons ``$ref``s in *node* to local component references.

    Both relative cross-file references (``./core.yaml#/components/schemas/X``)
    and local references (``#/components/schemas/X``) whose target is in
    *names* are normalised to ``#/components/schemas/X``.  The tree is
    modified in place.

    Args:
        node:  Parsed YAML node (dict, list or scalar).
        names: Schema names available in the shared component namespace.

    Returns:
        The set of names in *names* referenced anywhere below *node*.
    """
    referenced: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            decoded = unquote(ref)
            match = _MERGED_SCHEMA_REF_RE.fullmatch(decoded)
            name = match.group(1) if match else None
            if name is None and decoded.startswith(_LOCAL_SCHEMA_PREFIX):
                name = decoded[len(_LOCAL_SCHEMA_PREFIX):]
            if name in names:
                node["$ref"] = f"{_LOCAL_SCHEMA_PREFIX}{name}"
                referenced.add(name)
        for value in node.values():
            referenced |= _rewrite_commons_refs(value, names)
    elif isinstance(node, list):
        for value in node:
            referenced |= _rewrite_commons_refs(value, names)
    return referenced


def merged_commons_schemas(
    common_files: list[Path] | None = None,
) -> dict[str, dict]:
    """Return every commons schema in one namespace with local ``$ref``s.

    Schema definitions that appear identically in multiple source files are
    silently deduplicated; conflicting definitions for the same schema name
    are a hard error.  Cross-file references between commons files are
    rewritten to ``#/components/schemas/<name>``.

    Args:
        common_files: Override for the commons file list (test helper).

    Returns:
        Mapping of schema name to (rewritten) schema definition.

    Raises:
        SystemExit: If two source files define the same schema name with
            different content.  The collision must be resolved manually.
    """
    files = COMMON_YAML_FILES if common_files is None else common_files
    schemas: dict[str, dict] = {}
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

    _rewrite_commons_refs(schemas, set(schemas))
    return schemas


def merged_commons_yaml(
    output_dir: Path,
    common_files: list[Path] | None = None,
) -> Path:
    """Merge all commons YAML files into a single document in *output_dir*.

    The merged file (``commons-merged.yaml``) is passed as ``--input-spec``
    when generating the commons library.  See :func:`merged_commons_schemas`
    for the merge and collision rules.

    Args:
        output_dir:   Directory where ``commons-merged.yaml`` will be written.
        common_files: Override for the commons file list (test helper).

    Returns:
        Path to the written ``commons-merged.yaml`` file.
    """
    merged: dict = {
        "openapi": "3.1.0",
        "info": {"title": "ASM Commons", "version": COMMONS_VERSION},
        "components": {"schemas": merged_commons_schemas(common_files)},
    }
    merged_path = output_dir / "commons-merged.yaml"
    merged_path.write_text(
        yaml.dump(merged, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return merged_path


def bundle_spec(
    spec_path: Path,
    output_dir: Path,
    common_files: list[Path] | None = None,
) -> tuple[Path, set[str]]:
    """Write a self-contained copy of an instrument spec for the generator.

    openapi-generator's OpenAPI 3.1 parser dereferences external
    ``./core.yaml#/...`` references *inline*.  The referenced commons schemas
    then lose their names, ``--import-mappings`` never match, and every spec
    package re-emits its own copies of the commons classes under long
    path-derived names.  Bundling avoids that: every commons schema reachable
    from the spec is copied under its own name into the spec's
    ``components/schemas`` and all references become local.  The returned name
    set is then passed as both import and schema mappings, so the generator
    references the commons package classes instead of emitting copies.

    Args:
        spec_path:    Instrument spec YAML file.
        output_dir:   Directory for the bundled ``<spec>.bundled.yaml``.
        common_files: Override for the commons file list (test helper).

    Primitive aliases (e.g. ``CoreTNamed: {type: string}``) produce no class
    in the commons package; they are copied verbatim and left unmapped so the
    generator inlines the primitive type, exactly as it does for commons.
    Inside every *mapped* schema, nested inline objects and unions are
    replaced by an empty ``{type: object}``: the generator never emits the
    mapped schema, but it would otherwise still emit helper classes for them
    (``DoubleValueOneOf``, ``AsmDatacubeComponentAsmFillValue`` …) into the
    instrument package.

    Returns:
        ``(bundled_path, commons_names)`` where *commons_names* is the
        transitive closure of class-producing commons schemas reachable from
        the spec, i.e. the names to map onto the commons package.

    Raises:
        SystemExit: If the spec defines a schema whose name is also a commons
            schema name (the two would be indistinguishable after bundling).
    """
    commons = merged_commons_schemas(common_files)
    doc = load_yaml(spec_path)
    schemas = doc.setdefault("components", {}).setdefault("schemas", {})
    clashes = sorted(set(schemas) & set(commons))
    if clashes:
        print(
            f"[ERROR] {spec_path.name} redefines commons schema(s) {clashes};"
            " reference the commons definition instead.",
            file=sys.stderr,
        )
        sys.exit(1)

    pending = _rewrite_commons_refs(doc, set(commons))
    included: set[str] = set()
    while pending:
        name = pending.pop()
        if name in included:
            continue
        included.add(name)
        definition = copy.deepcopy(commons[name])
        pending |= _rewrite_commons_refs(definition, set(commons)) - included
        if generates_model(definition):
            _hollow_nested_inline_objects(definition)
        schemas[name] = definition
    mapped = {name for name in included if generates_model(schemas[name])}

    output_dir.mkdir(parents=True, exist_ok=True)
    bundled_path = output_dir / f"{spec_path.stem}.bundled.yaml"
    bundled_path.write_text(
        yaml.dump(doc, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return bundled_path, mapped


_PRIMITIVE_TYPES = {"string", "number", "integer", "boolean"}


def generates_model(schema: dict) -> bool:
    """Return whether the generator emits a model class for *schema*.

    Primitive aliases without an ``enum`` (and array aliases) are unaliased
    to the underlying type by openapi-generator, so no class exists for them.
    Objects, compositions (``oneOf``/``anyOf``/``allOf``) and enums produce
    models.
    """
    if any(key in schema for key in ("properties", "oneOf", "anyOf", "allOf", "enum")):
        return True
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next((t for t in schema_type if t != "null"), None)
    return schema_type not in _PRIMITIVE_TYPES and schema_type != "array"


def _hollow_nested_inline_objects(schema: dict) -> None:
    """Replace inline objects and unions *below* the top level with ``{type: object}``.

    The generator would emit a helper class for each of them (e.g.
    ``AsmDatacubeComponentAsmFillValue`` for an inline ``anyOf``) even though
    the mapped schema itself is never emitted.  ``$ref`` nodes, primitive
    leaves and the top-level node are untouched, so the schema keeps its shape
    (object, composition, enum) for the generator.
    """
    def visit(node: object, top: bool) -> object:
        if isinstance(node, dict):
            if not top and "$ref" not in node and (
                {"properties", "additionalProperties", "oneOf", "anyOf", "allOf"} & node.keys()
            ):
                return {"type": "object"}
            return {key: visit(value, False) for key, value in node.items()}
        if isinstance(node, list):
            return [visit(value, False) for value in node]
        return node

    hollowed = visit(schema, True)
    schema.clear()
    schema.update(hollowed)


#: Vendor extension marking a ``number`` property whose ASM value may be the
#: JSON string ``"NaN"``.
NAN_EXTENSION = "x-asm-nan"


def nan_capable_properties(schemas: dict[str, dict]) -> dict[str, list[str]]:
    """Return ``{schema name: [property names]}`` for NaN-capable numbers.

    A property is NaN-capable when it carries ``x-asm-nan: true``.  Schemas
    that compose a NaN-capable schema through ``allOf`` (the unit-specific
    ``*QuantityValue`` wrappers) inherit its NaN-capable properties, because
    generators flatten ``allOf`` into one class with the same fields.

    Args:
        schemas: ``components/schemas`` mapping with local ``$ref``s.

    Returns:
        NaN-capable property names per schema; schemas without any are omitted.
    """
    def own(schema: dict) -> list[str]:
        return [
            name for name, prop in (schema.get("properties") or {}).items()
            if isinstance(prop, dict) and prop.get(NAN_EXTENSION) is True
        ]

    def collect(name: str, seen: frozenset[str]) -> list[str]:
        schema = schemas.get(name) or {}
        found = own(schema)
        for part in schema.get("allOf") or []:
            if not isinstance(part, dict):
                continue
            ref = part.get("$ref", "")
            if ref.startswith(_LOCAL_SCHEMA_PREFIX):
                target = ref[len(_LOCAL_SCHEMA_PREFIX):]
                if target not in seen:
                    found += collect(target, seen | {target})
            else:
                found += own(part)
        return sorted(set(found))

    result = {name: collect(name, frozenset({name})) for name in schemas}
    return {name: props for name, props in result.items() if props}


def primitive_unions(schemas: dict[str, dict]) -> list[str]:
    """Return the schemas that are a ``oneOf`` of a JSON primitive and an object.

    ASM encodes some scalar values either as a bare JSON primitive or as a
    typed ``{"@type": …, "value": …}`` object (``DateTimeValue``,
    ``DateTimeStampValue``, ``IntegerValue``).  Generators that cannot
    serialize such unions natively are patched for these schemas (see
    :func:`allotrope_gen.patch.csharp.patch_primitive_unions`).

    Args:
        schemas: ``components/schemas`` mapping.

    Returns:
        Sorted schema names with exactly one primitive branch and at least
        one object branch.
    """
    def is_primitive(branch: object) -> bool:
        return isinstance(branch, dict) and branch.get("type") in _PRIMITIVE_TYPES

    def is_object(branch: object) -> bool:
        return isinstance(branch, dict) and (branch.get("type") == "object" or "$ref" in branch)

    return sorted(
        name for name, schema in schemas.items()
        if isinstance(schema, dict)
        and isinstance(branches := schema.get("oneOf"), list)
        and sum(map(is_primitive, branches)) == 1
        and any(map(is_object, branches))
    )


ASM_MANIFEST = "$asm.manifest"


def root_schema(schemas: dict[str, dict]) -> tuple[str, dict]:
    """Return ``(class name, schema)`` of the ASM document root of a spec.

    The root is the only schema declaring the ``$asm.manifest`` member; its
    class name is the schema name with an upper-case first letter, as the
    generators emit it (``liquidChromatographySimpleModel`` becomes
    ``LiquidChromatographySimpleModel``).

    Raises:
        ValueError: If not exactly one schema declares ``$asm.manifest``.
    """
    roots = [
        (name, schema) for name, schema in schemas.items()
        if isinstance(schema, dict) and ASM_MANIFEST in (schema.get("properties") or {})
    ]
    if len(roots) != 1:
        raise ValueError(f"expected one schema declaring {ASM_MANIFEST}, found {[n for n, _ in roots]}")
    name, schema = roots[0]
    return name[:1].upper() + name[1:], schema


def technique_documents(schemas: dict[str, dict]) -> tuple[str, str]:
    """Return the JSON names of the root aggregate document and its document list.

    Every ASM technique document has the shape ``{"<technique> aggregate
    document": {"<technique> document": [...]}}``, e.g. ``"liquid
    chromatography aggregate document"`` / ``"liquid chromatography
    document"``.

    Raises:
        ValueError: If the root has no such aggregate document.
    """
    _, root = root_schema(schemas)
    aggregates = [name for name in root.get("properties", {}) if name.endswith(" aggregate document")]
    if len(aggregates) != 1:
        raise ValueError(f"expected one root aggregate document, found {aggregates}")
    return aggregates[0], aggregates[0].replace(" aggregate document", " document")
