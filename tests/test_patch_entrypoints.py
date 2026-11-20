"""Tests for the dispatch of :func:`allotrope_gen.patch.patch_commons_output` and
:func:`allotrope_gen.patch.patch_spec_output`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from allotrope_gen.patch import (
    CommonsDependency,
    PackageReadme,
    PatchTargets,
    patch_commons_output,
    patch_spec_output,
)

TARGETS = PatchTargets(nan_properties={"Q": ["value"]}, primitive_unions=["U"])
README = PackageReadme(text="# x\n", summary="x", keywords=("asm",))
COMMONS = CommonsDependency(name="commons", version="1.0", schemas=frozenset({"Foo"}), maven_group="g")

#: Every patch function, by module.
PATCHES = {
    "java": ["add_central_publishing_plugin", "add_dependency", "describe_package"],
    "csharp": [
        "add_package_reference", "register_commons_converters", "add_commons_registry",
        "guard_optional_enum_writes", "keep_additional_properties", "patch_primitive_unions", "patch_doubles",
        "describe_package",
    ],
    "python": ["depend_on_commons", "allow_nan_strings", "describe_package"],
    "typescript": ["keep_models_only", "add_peer_dependency", "allow_nan_strings", "describe_package"],
}


def _called(entry, *args) -> set[str]:
    """Run *entry* with every patch mocked; return ``module.function`` names called."""
    mocks: dict[str, MagicMock] = {}
    patchers = []
    for module, names in PATCHES.items():
        for name in names:
            patcher = patch(f"allotrope_gen.patch.{module}.{name}")
            mocks[f"{module}.{name}"] = patcher.start()
            patchers.append(patcher)
    try:
        entry(*args)
    finally:
        for patcher in patchers:
            patcher.stop()
    return {name for name, mock in mocks.items() if mock.called}


@pytest.mark.parametrize("generator, expected", [
    ("java", {"java.describe_package", "java.add_central_publishing_plugin"}),
    ("csharp", {
        "csharp.describe_package", "csharp.add_commons_registry", "csharp.guard_optional_enum_writes", "csharp.keep_additional_properties",
        "csharp.patch_primitive_unions", "csharp.patch_doubles",
    }),
    ("python", {"python.describe_package", "python.allow_nan_strings"}),
    ("typescript-angular", {"typescript.describe_package", "typescript.keep_models_only", "typescript.allow_nan_strings"}),
])
def test_commons_output(generator: str, expected: set[str], tmp_path: Path):
    assert _called(patch_commons_output, generator, tmp_path, "ns", TARGETS, README) == expected


@pytest.mark.parametrize("generator, expected", [
    ("java", {"java.describe_package", "java.add_central_publishing_plugin", "java.add_dependency"}),
    ("csharp", {
        "csharp.describe_package", "csharp.add_package_reference", "csharp.register_commons_converters",
        "csharp.guard_optional_enum_writes", "csharp.keep_additional_properties",
        "csharp.patch_primitive_unions", "csharp.patch_doubles",
    }),
    ("python", {"python.describe_package", "python.depend_on_commons", "python.allow_nan_strings"}),
    ("typescript-angular", {
        "typescript.describe_package", "typescript.keep_models_only", "typescript.add_peer_dependency",
        "typescript.allow_nan_strings",
    }),
])
def test_spec_output(generator: str, expected: set[str], tmp_path: Path):
    assert _called(patch_spec_output, generator, tmp_path, "pkg", TARGETS, COMMONS, README) == expected


@pytest.mark.parametrize("generator", ["java", "csharp", "python", "typescript-angular"])
def test_spec_output_without_commons_declares_no_dependency(generator: str, tmp_path: Path):
    called = _called(patch_spec_output, generator, tmp_path, "pkg", TARGETS, None, README)
    assert not called & {
        "java.add_dependency", "csharp.add_package_reference", "csharp.register_commons_converters",
        "python.depend_on_commons", "typescript.add_peer_dependency",
    }


def test_csharp_commons_registers_double_converter(tmp_path: Path):
    with patch("allotrope_gen.patch.csharp.patch_doubles") as doubles, \
         patch("allotrope_gen.patch.csharp.add_commons_registry"), \
         patch("allotrope_gen.patch.csharp.guard_optional_enum_writes"), \
         patch("allotrope_gen.patch.csharp.keep_additional_properties"), \
         patch("allotrope_gen.patch.csharp.patch_primitive_unions") as unions, \
         patch("allotrope_gen.patch.csharp.describe_package") as describe:
        patch_commons_output("csharp", tmp_path, "ns", TARGETS, README)
    assert describe.call_args.args[1] is README
    assert doubles.call_args.kwargs["register_converter"] is True
    assert doubles.call_args.args[2] == TARGETS.nan_properties
    assert unions.call_args.args[1] == ["U"]
