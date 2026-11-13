"""Resolve ASM property descriptions from the Allotrope Foundation ontology.

OpenAPI properties are named with Allotrope preferred labels, while the ASM
JSON schemas carry the definitions on ``$asm.property-class`` IRIs.  This
module uses those IRIs when available and otherwise accepts only an unambiguous
exact preferred-label match from OLS.  The full ontology is downloaded in a
few paginated requests and cached outside generated output, rather than doing
one network request per model field.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from .asm import latest_lc_schema
from .config import OUTPUT

OLS_API = "https://www.ebi.ac.uk/ols4/api"
OLS_ONTOLOGY = "afo"
OLS_PAGE_SIZE = 1000
OLS_TIMEOUT_SECONDS = 30
CACHE_PATH = OUTPUT.parent / "ontology-cache" / "afo-terms.json"
CACHE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def _normalise_label(label: str) -> str:
    """Return a whitespace- and case-insensitive label key."""
    return re.sub(r"\s+", " ", label).strip().casefold()


def _asm_label_key(label: str) -> str:
    """Normalize harmless grammatical differences in ASM field labels.

    The official JSON schema and generated OpenAPI names occasionally differ
    only by connective words such as ``of`` or ``at``. This key is used only
    to find a unique property-class IRI in the official schema reference; it is
    not used to search ontology terms by approximate label.
    """
    ignored = {"at", "by", "of", "the"}
    return " ".join(
        token for token in _normalise_label(label).split() if token not in ignored
    )


def property_class_ids(reference_path: Path | None = None) -> dict[str, set[str]]:
    """Collect ASM property-class IRIs indexed by official and safe alias names.

    The official LC schema is read from the complete local ASM checkout, never
    copied into this repository. Exact names are preferred. Connective-word-
    normalized aliases are included only when every official occurrence resolves
    to the same IRI.
    """
    if reference_path is None:
        reference_path = latest_lc_schema()
        if reference_path is None:
            return {}

    if not reference_path.is_file():
        return {}

    try:
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[WARN] Could not read ASM class reference {reference_path}: {exc}", file=sys.stderr)
        return {}

    found: dict[str, set[str]] = defaultdict(set)

    def visit(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                for name, schema in properties.items():
                    if isinstance(schema, dict):
                        iri = schema.get("$asm.property-class")
                        if isinstance(iri, str):
                            found[name].add(iri)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(reference)

    # Preserve exact keys and add normalized aliases only when all official
    # schema occurrences with that key identify the same property class.
    aliases: dict[str, set[str]] = defaultdict(set)
    for name, iris in found.items():
        aliases[_asm_label_key(name)].update(iris)

    result = {name: iris for name, iris in found.items() if len(iris) == 1}
    for name in found:
        candidates = aliases[_asm_label_key(name)]
        if len(candidates) == 1:
            result[name] = candidates
    return result


def _property_class_candidates(
    label: str,
    class_ids: dict[str, set[str]],
) -> set[str]:
    """Return exact property-class IDs, or uniquely normalized aliases."""
    exact = class_ids.get(label)
    if exact:
        return exact
    return {
        iri
        for candidate, iris in class_ids.items()
        if _asm_label_key(candidate) == _asm_label_key(label)
        for iri in iris
    }


def _index_terms(terms: list[dict]) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    """Build IRI and exact-label indexes from OLS term records."""
    by_iri: dict[str, dict] = {}
    by_label: dict[str, list[dict]] = defaultdict(list)
    for term in terms:
        iri = term.get("iri")
        label = term.get("label")
        descriptions = term.get("description")
        if not isinstance(iri, str) or not isinstance(label, str):
            continue
        description = _description_text(descriptions)
        if not description:
            continue
        by_iri[iri] = {**term, "resolved_description": description}
        by_label[_normalise_label(label)].append(by_iri[iri])
    return by_iri, by_label


def _description_text(value: object) -> str | None:
    """Return the first non-empty description from an OLS description value."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def _request_json(url: str) -> dict:
    """Fetch a JSON response from OLS with a descriptive user agent."""
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "allotrope-gen/1.0"})
    with urlopen(request, timeout=OLS_TIMEOUT_SECONDS) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError(f"OLS returned a non-object response for {url}")
    return result


def _download_terms() -> list[dict]:
    """Download all current AFO terms from the paginated OLS API."""
    first_page_url = (
        f"{OLS_API}/ontologies/{OLS_ONTOLOGY}/terms"
        f"?size={OLS_PAGE_SIZE}&page=0&lang=en"
    )
    first_page = _request_json(first_page_url)
    page_info = first_page.get("page", {})
    total_pages = page_info.get("totalPages")
    first_terms = first_page.get("_embedded", {}).get("terms")
    if not isinstance(total_pages, int) or not isinstance(first_terms, list):
        raise ValueError("OLS response did not contain paginated ontology terms")

    terms = list(first_terms)
    for page in range(1, total_pages):
        url = (
            f"{OLS_API}/ontologies/{OLS_ONTOLOGY}/terms"
            f"?size={OLS_PAGE_SIZE}&page={page}&lang=en"
        )
        page_data = _request_json(url)
        page_terms = page_data.get("_embedded", {}).get("terms")
        if not isinstance(page_terms, list):
            raise ValueError(f"OLS response did not contain terms for page {page}")
        terms.extend(page_terms)
    # Keep only fields used to enrich model properties; OLS term records also
    # contain verbose relationship URLs that are not needed in the cache.
    return [
        {key: term[key] for key in ("iri", "label", "description") if key in term}
        for term in terms
    ]


def _load_cached_terms(cache_path: Path) -> list[dict] | None:
    """Return cached OLS records when a valid cache file exists."""
    if not cache_path.is_file():
        return None
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        terms = cache.get("terms")
        return terms if isinstance(terms, list) else None
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        print(f"[WARN] Ignoring invalid ontology cache {cache_path}: {exc}", file=sys.stderr)
        return None


def _cache_is_stale(cache_path: Path) -> bool:
    """Return whether a cached ontology index is older than its refresh interval."""
    try:
        age = time.time() - cache_path.stat().st_mtime
    except OSError:
        return True
    return age > CACHE_MAX_AGE_SECONDS


def _save_cached_terms(cache_path: Path, terms: list[dict]) -> None:
    """Persist downloaded terms so subsequent generation can work offline."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"ontology": OLS_ONTOLOGY, "terms": terms}, ensure_ascii=False),
        encoding="utf-8",
    )


def _get_term_index(
    cache_path: Path,
    *,
    refresh: bool = False,
) -> tuple[dict[str, dict], dict[str, list[dict]]] | None:
    """Load the cached term index, downloading AFO when needed.

    A cache miss triggers one bulk paginated download.  If an existing cache
    cannot resolve a field, the caller can request one refresh before giving
    up; this keeps both repeated and offline builds efficient.
    """
    cached_terms = _load_cached_terms(cache_path)
    terms = None if refresh or _cache_is_stale(cache_path) else cached_terms
    if terms is not None:
        return _index_terms(terms)

    try:
        terms = _download_terms()
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[WARN] Could not retrieve Allotrope ontology definitions: {exc}", file=sys.stderr)
        # A stale-but-usable cache is better than no descriptions at all.
        if cached_terms is not None:
            return _index_terms(cached_terms)
        return None
    try:
        _save_cached_terms(cache_path, terms)
    except OSError as exc:
        print(f"[WARN] Could not save ontology cache {cache_path}: {exc}", file=sys.stderr)
    return _index_terms(terms)


def _resolve_description(
    label: str,
    schema: dict,
    by_iri: dict[str, dict],
    by_label: dict[str, list[dict]],
    class_ids: dict[str, set[str]],
) -> str | None:
    """Resolve one property definition without guessing between terms."""
    iri = schema.get("$asm.property-class")
    if not isinstance(iri, str):
        candidates = _property_class_candidates(label, class_ids)
        if len(candidates) == 1:
            candidate_iri = next(iter(candidates))
            candidate_term = by_iri.get(candidate_iri)
            # The official schema occasionally carries a mismatched class IRI.
            # For IDs inferred from a reference (unlike an IRI on the field
            # itself), require the ontology's own label to agree under the same
            # conservative connective-word normalization.
            if (
                candidate_term is not None
                and _asm_label_key(candidate_term.get("label", ""))
                == _asm_label_key(label)
            ):
                iri = candidate_iri
    if isinstance(iri, str):
        term = by_iri.get(iri)
        if term is not None:
            return term["resolved_description"]

    matches = by_label.get(_normalise_label(label), [])
    if len(matches) == 1:
        return matches[0]["resolved_description"]
    return None


def enrich_spec_descriptions(
    spec_path: Path,
    *,
    cache_path: Path = CACHE_PATH,
    class_ids: dict[str, set[str]] | None = None,
    dry_run: bool = False,
) -> int:
    """Add missing Allotrope definitions to property schemas in *spec_path*.

    Existing non-empty descriptions are never changed. Empty ``description: {}``
    placeholders are treated as missing. Enrichment is written back to the YAML
    so generated clients and checked-in OpenAPI specs share the same text.

    Args:
        spec_path: OpenAPI YAML file to enrich.
        cache_path: Local cache path for the paginated OLS ontology response.
        class_ids: Optional preferred-label to ASM property-class IRI mapping.
            Primarily exposed for deterministic unit tests.
        dry_run: Resolve and report descriptions without writing the YAML.

    Returns:
        Number of property descriptions added.
    """
    source = spec_path.read_bytes().decode("utf-8")
    document = yaml.safe_load(source)
    if not isinstance(document, dict):
        return 0

    # Keep YAML node marks alongside parsed property schemas so edits can be
    # applied surgically. Dumping the entire document would reformat unrelated
    # portions of the instrument specification.
    root_node = yaml.compose(source)
    pending: list[tuple[str, dict, Node, Node | None, bool, MappingNode]] = []

    def collect(node: object, yaml_node: Node | None) -> None:
        if isinstance(node, dict) and isinstance(yaml_node, MappingNode):
            node_values = {
                key.value: value
                for key, value in yaml_node.value
                if isinstance(key, ScalarNode)
            }
            properties = node.get("properties")
            properties_node = node_values.get("properties")
            if isinstance(properties, dict) and isinstance(properties_node, MappingNode):
                property_nodes = {
                    key.value: value
                    for key, value in properties_node.value
                    if isinstance(key, ScalarNode)
                }
                property_schemas_node = properties_node
                properties_flow_style = properties_node.flow_style
                for name, property_schema in properties.items():
                    schema_node = property_nodes.get(name)
                    if not isinstance(property_schema, dict) or not isinstance(schema_node, MappingNode):
                        continue
                    # A pure reference already inherits its target's schema
                    # documentation. Avoid adding a $ref sibling, which some
                    # OpenAPI Generator targets do not preserve consistently.
                    if "$ref" in property_schema:
                        continue
                    description = property_schema.get("description")
                    if not (isinstance(description, str) and description.strip()):
                        schema_values = {
                            key.value: value
                            for key, value in schema_node.value
                            if isinstance(key, ScalarNode)
                        }
                        pending.append(
                            (
                                name,
                                property_schema,
                                schema_node,
                                schema_values.get("description"),
                                properties_flow_style,
                                property_schemas_node,
                            )
                        )
            for key, child in node.items():
                collect(child, node_values.get(key))
        elif isinstance(node, list) and isinstance(yaml_node, SequenceNode):
            for child, child_node in zip(node, yaml_node.value):
                collect(child, child_node)

    collect(document, root_node)
    if not pending:
        return 0

    cache_was_available = _load_cached_terms(cache_path) is not None
    term_index = _get_term_index(cache_path)
    known_classes = class_ids if class_ids is not None else property_class_ids()

    if term_index is None:
        by_iri, by_label = {}, {}
    else:
        by_iri, by_label = term_index

    def resolve_all() -> tuple[dict[int, str], list[str]]:
        resolved: dict[int, str] = {}
        missing: list[str] = []
        for index, (name, property_schema, _, _, _, _) in enumerate(pending):
            description = _resolve_description(name, property_schema, by_iri, by_label, known_classes)
            if description:
                resolved[index] = description
            else:
                missing.append(name)
        return resolved, missing

    resolved, unresolved = resolve_all()
    has_unresolved_class_iris = any(
        (
            isinstance(schema.get("$asm.property-class"), str)
            or len(_property_class_candidates(name, known_classes)) == 1
        )
        and index not in resolved
        for index, (name, schema, _, _, _, _) in enumerate(pending)
    )
    if (
        unresolved
        and term_index is not None
        and cache_was_available
        and _cache_is_stale(cache_path)
        and has_unresolved_class_iris
    ):
        # A stale cache can miss recently added terms. Refresh the bulk index
        # once when authoritative ASM IRIs fail to resolve.
        refreshed = _get_term_index(cache_path, refresh=True)
        if refreshed is not None:
            by_iri, by_label = refreshed
            resolved, unresolved = resolve_all()

    added = len(resolved)

    if unresolved:
        print(
            f"[WARN] {len(unresolved)} field(s) in {spec_path.name} have no unambiguous AFO definition: "
            + ", ".join(sorted(set(unresolved))),
            file=sys.stderr,
        )
    if added and not dry_run:
        newline = "\r\n" if "\r\n" in source else "\n"
        edits: list[tuple[int, int, str]] = []
        for index, description in resolved.items():
            name, _, schema_node, description_node, properties_flow_style, properties_node = pending[index]
            serialized = json.dumps(description, ensure_ascii=False)
            if description_node is not None:
                # Replace only the empty placeholder value (often ``{}``),
                # retaining the original indentation and surrounding fields.
                edits.append(
                    (
                        description_node.start_mark.index,
                        description_node.end_mark.index,
                        serialized,
                    )
                )
            elif schema_node.flow_style:
                # Inline property schemas need a comma-delimited sibling.
                insertion = schema_node.end_mark.index - 1
                separator = ", " if schema_node.value else ""
                edits.append((insertion, insertion, f'{separator}description: {serialized}'))
            else:
                if properties_flow_style:
                    insertion = properties_node.end_mark.index - 1
                    separator = ", " if properties_node.value else ""
                    edits.append(
                        (
                            insertion,
                            insertion,
                            f'{separator}{name}: {{description: {serialized}}}',
                        )
                    )
                    continue
                elif schema_node.value:
                    first_key = schema_node.value[0][0]
                    insertion = source.rfind("\n", 0, first_key.start_mark.index) + 1
                    indent = " " * first_key.start_mark.column
                else:
                    insertion = source.rfind("\n", 0, schema_node.start_mark.index) + 1
                    indent = " " * schema_node.start_mark.column
                edits.append(
                    (insertion, insertion, f'{indent}description: {serialized}{newline}')
                )

        for start, end, replacement in sorted(edits, reverse=True):
            source = source[:start] + replacement + source[end:]
        spec_path.write_bytes(source.encode("utf-8"))
    if added:
        action = "would add" if dry_run else "added"
        print(f"[descriptions] {spec_path.name}: {action} {added} field definition(s)")
    return added
