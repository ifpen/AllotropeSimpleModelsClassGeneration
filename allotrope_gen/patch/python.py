"""
Python (pydantic) patches.

* :func:`depend_on_commons` — spec outputs.  The generator maps commons
  schemas to bare class names but never imports them, and emits empty parent
  ``__init__.py`` files that would overwrite the commons package's own
  ``ifpen/allotrope_models/__init__.py`` on installation.
* :func:`allow_nan_strings` — properties marked ``x-asm-nan``.  ASM writes an
  unavailable quantity as the JSON string ``"NaN"``; the generated
  ``Union[StrictFloat, StrictInt]`` rejects it, so those fields use the
  ``AsmDouble`` type of ``templates/asm_double.py``.

``oneOf`` primitive/object unions need no patch: the generated
``actual_instance`` wrapper reads and writes both forms.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .common import attribute_name, render_template, replace_exact, report, snake_case, write_text

#: Line after which the patches insert imports into generated modules.
IMPORT_ANCHOR = "from __future__ import annotations\n"


def depend_on_commons(
    output_dir: Path,
    package: str,
    commons_package: str,
    commons_version: str,
    commons_schemas: set[str],
    dry_run: bool = False,
) -> None:
    """Make a generated Python spec package depend on the commons package.

    * imports every referenced commons class from *commons_package* in each
      generated module;
    * removes the parent ``__init__.py`` files owned by the commons package
      and packages only the spec sub-package (namespace packaging);
    * declares ``<commons_package>==<commons_version>`` in ``setup.py``,
      ``pyproject.toml`` and ``requirements.txt``.

    Idempotent.

    Args:
        output_dir:      Generated Python output directory.
        package:         Spec package (e.g. ``ifpen.allotrope_models.gc``).
        commons_package: Commons package (e.g. ``ifpen.allotrope_models``).
        commons_version: Exact commons version.
        commons_schemas: Commons class names that may be referenced.
        dry_run:         When ``True``, report but do not modify any file.
    """
    package_dir = output_dir.joinpath(*package.split("."))
    if not package_dir.is_dir():
        print(f"[WARN] Python package not found, skipping patch: {package_dir}", file=sys.stderr)
        return

    patterns = {name: re.compile(rf"\b{re.escape(name)}\b") for name in commons_schemas}
    patched = 0
    for module in sorted(package_dir.rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        if f"from {commons_package} import " in text or IMPORT_ANCHOR not in text:
            continue
        used = sorted(name for name, pattern in patterns.items() if pattern.search(text))
        if not used:
            continue
        imports = "".join(f"from {commons_package} import {name}\n" for name in used)
        patched += 1
        write_text(module, text.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + imports, 1), dry_run)
    report("python patch", f"added {commons_package} imports to {patched} module(s)")

    parts = package.split(".")
    for depth in range(1, len(parts)):
        init = output_dir.joinpath(*parts[:depth], "__init__.py")
        if init.exists():
            report("python patch", f"removed {init.relative_to(output_dir)} (owned by {commons_package})")
            if not dry_run:
                init.unlink()

    requirement = f"{commons_package}=={commons_version}"
    setup_py = output_dir / "setup.py"
    if setup_py.exists():
        text = setup_py.read_text(encoding="utf-8")
        text = text.replace(
            "from setuptools import setup, find_packages",
            "from setuptools import setup, find_namespace_packages",
        )
        text = re.sub(
            r"packages=find_packages\([^)]*\)",
            f'packages=find_namespace_packages(include=["{package}", "{package}.*"])',
            text,
        )
        if requirement not in text:
            text = text.replace("REQUIRES = [\n", f'REQUIRES = [\n    "{requirement}",\n', 1)
        write_text(setup_py, text, dry_run)

    pyproject = output_dir / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        if requirement not in text:
            text = text.replace("dependencies = [\n", f'dependencies = [\n  "{requirement}",\n', 1)
        write_text(pyproject, text, dry_run)

    requirements = output_dir / "requirements.txt"
    if requirements.exists():
        text = requirements.read_text(encoding="utf-8")
        if requirement not in text.splitlines():
            text = text.rstrip("\n") + f"\n{requirement}\n"
        write_text(requirements, text, dry_run)
    report("python patch", f"declared dependency {requirement}")


def allow_nan_strings(
    output_dir: Path,
    package: str,
    nan_properties: dict[str, list[str]],
    dry_run: bool = False,
) -> None:
    """Type NaN-capable number fields as ``AsmDouble`` (idempotent).

    ``AsmDouble`` (``<package>/asm_double.py``, from the template of the same
    name) is a ``float`` that reads ``"NaN"`` as ``math.nan`` and writes NaN
    back as ``"NaN"``.  It is added to the package when a model uses it.

    Args:
        output_dir:     Generated Python output directory.
        package:        Package holding the models (``<package>.models``).
        nan_properties: ``{class name: [JSON property names]}`` of the classes
                        generated in this output.
        dry_run:        When ``True``, report but do not write.

    Raises:
        PatchError: If a field is not typed ``Union[StrictFloat, StrictInt]``.
    """
    package_dir = output_dir.joinpath(*package.split("."))
    patched = 0
    for name, props in nan_properties.items():
        module = package_dir / "models" / f"{snake_case(name)}.py"
        if not module.exists():
            continue
        text = module.read_text(encoding="utf-8")
        if "AsmDouble" in text:
            continue
        for prop in props:
            text = replace_exact(
                text,
                rf"^(    {attribute_name(prop)}: (?:Optional\[)?)Union\[StrictFloat, StrictInt\]",
                r"\1AsmDouble",
                module,
            )
        text = text.replace(IMPORT_ANCHOR, f"{IMPORT_ANCHOR}from {package}.asm_double import AsmDouble\n", 1)
        patched += 1
        write_text(module, text, dry_run)
    if patched:
        write_text(package_dir / "asm_double.py", render_template("asm_double.py"), dry_run)
    report("nan patch", f"python: {patched} model(s) accept the ASM \"NaN\" string")
