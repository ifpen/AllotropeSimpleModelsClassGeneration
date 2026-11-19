"""Structural regression tests over every OpenAPI file in ``src/main/resources``.

They guard against model debris found in the specs: schemas nothing reaches
(they still become published classes), constraints the generator silently
ignores, and YAML mistakes PyYAML accepts without warning.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from yaml.constructor import ConstructorError

from allotrope_gen.config import COMMON_YAML_FILES, RESOURCES, SPECS

_REF = re.compile(r"^(?:\./([\w-]+\.yaml))?#/components/schemas/([\w-]+)$")
FILES: list[Path] = [*COMMON_YAML_FILES, *SPECS.values()]


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (PyYAML keeps the last)."""


def _strict_mapping(loader: _StrictLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    keys = [loader.construct_object(key, deep=deep) for key, _ in node.value]
    duplicates = sorted({key for key in keys if keys.count(key) > 1}, key=str)
    if duplicates:
        raise ConstructorError(None, None, f"duplicate keys {duplicates}", node.start_mark)
    return loader.construct_mapping(node, deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping)


def _schemas() -> dict[str, dict]:
    return {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8"))["components"]["schemas"]
        for path in FILES
    }


def _refs(node: object, here: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            match = _REF.fullmatch(ref)
            assert match, f"unsupported $ref {ref!r} in {here}"
            found.append((match[1] or here, match[2]))
        for value in node.values():
            found += _refs(value, here)
    elif isinstance(node, list):
        for value in node:
            found += _refs(value, here)
    return found


def _reachable(schemas: dict[str, dict], root: tuple[str, str]) -> set[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    todo = [root]
    while todo:
        file, name = todo.pop()
        if (file, name) in seen:
            continue
        assert name in schemas.get(file, {}), f"broken $ref to {file}#{name}"
        seen.add((file, name))
        todo += _refs(schemas[file][name], file)
    return seen


def _roots(schemas: dict[str, dict], spec: str) -> list[tuple[str, str]]:
    file = SPECS[spec].name
    roots = [(file, name) for name in schemas[file] if name.lower().endswith("simplemodel")]
    assert len(roots) == 1, f"{file} must have exactly one *SimpleModel root, found {roots}"
    return roots


def _walk(node: object, where: str):
    if isinstance(node, dict):
        yield where, node
        for key, value in node.items():
            yield from _walk(value, f"{where}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{where}[{index}]")


@pytest.mark.parametrize("spec", sorted(SPECS))
def test_every_spec_schema_is_reachable_from_its_root(spec: str):
    """Unreachable schemas still become published (dead) classes."""
    schemas = _schemas()
    file = SPECS[spec].name
    reached = _reachable(schemas, _roots(schemas, spec)[0])
    assert sorted(name for name in schemas[file] if (file, name) not in reached) == []


def test_every_commons_schema_is_used_by_a_spec():
    schemas = _schemas()
    reached = set().union(*(_reachable(schemas, _roots(schemas, spec)[0]) for spec in SPECS))
    unused = [
        f"{path.name}#{name}"
        for path in COMMON_YAML_FILES
        for name in schemas[path.name]
        if (path.name, name) not in reached
    ]
    assert unused == []


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_ignored_or_misplaced_keywords(path: Path):
    """``properties`` on arrays and ``$ref`` siblings are dropped by the generator."""
    schemas = yaml.safe_load(path.read_text(encoding="utf-8"))["components"]["schemas"]
    problems = []
    for where, node in _walk(schemas, path.stem):
        if node.get("type") == "array" and "properties" in node:
            problems.append(f"properties on array schema: {where}")
        if "$ref" in node and set(node) - {"$ref", "description"}:
            problems.append(f"$ref with sibling keywords {sorted(set(node) - {'$ref'})}: {where}")
        description = node.get("description")
        if isinstance(description, str) and "ordered in a not-natural way" in description:
            problems.append(f"@index item description used as model description: {where}")
    assert problems == []


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_duplicate_yaml_keys(path: Path):
    """PyYAML silently keeps the last of duplicate keys."""
    yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictLoader)


def test_no_stray_openapi_files():
    """Every YAML file in the resources is a commons file or a registered spec."""
    known = {path.name for path in FILES}
    stray = sorted(p.name for p in RESOURCES.glob("*.yaml") if p.name not in known)
    assert stray == []
