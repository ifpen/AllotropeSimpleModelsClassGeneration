"""Tests for :mod:`allotrope_gen.patch.python`."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

from allotrope_gen.patch import PackageReadme, PatchError
from allotrope_gen.patch.python import allow_nan_strings, depend_on_commons, describe_package

NAN = {"SecondsQuantityValue": ["value"]}


@pytest.fixture()
def python_output(tmp_path: Path) -> Path:
    """A miniature generated Python spec package."""
    package = tmp_path / "ifpen" / "allotrope_models" / "gc"
    (package / "models").mkdir(parents=True)
    (tmp_path / "ifpen" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "ifpen" / "allotrope_models" / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "models" / "peak.py").write_text(
        "from __future__ import annotations\nimport json\n\n"
        "class Peak(BaseModel):\n    retention_time: Optional[SecondsQuantityValue] = None\n"
        "    other: Optional[SecondsQuantityValueX] = None\n",
        encoding="utf-8",
    )
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup, find_packages  # noqa: H301\n"
        'REQUIRES = [\n    "pydantic >= 2",\n]\n'
        'setup(packages=find_packages(exclude=["test", "tests"]))\n',
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text('dependencies = [\n  "pydantic (>=2)",\n]\n', encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pydantic >= 2\n", encoding="utf-8")
    return tmp_path


class TestDependOnCommons:
    def _patch(self, out: Path) -> None:
        depend_on_commons(
            out, "ifpen.allotrope_models.gc", "ifpen.allotrope_models", "2.0.0",
            {"SecondsQuantityValue", "Unused"},
        )

    def test_imports_referenced_commons_classes(self, python_output: Path):
        self._patch(python_output)
        text = (python_output / "ifpen/allotrope_models/gc/models/peak.py").read_text(encoding="utf-8")
        assert "from ifpen.allotrope_models import SecondsQuantityValue\n" in text
        assert "import Unused" not in text

    def test_removes_commons_owned_init_files(self, python_output: Path):
        self._patch(python_output)
        assert not (python_output / "ifpen/__init__.py").exists()
        assert not (python_output / "ifpen/allotrope_models/__init__.py").exists()
        assert (python_output / "ifpen/allotrope_models/gc/__init__.py").exists()

    def test_declares_dependency_and_namespace_packaging(self, python_output: Path):
        self._patch(python_output)
        self._patch(python_output)  # idempotent
        setup = (python_output / "setup.py").read_text(encoding="utf-8")
        assert 'find_namespace_packages(include=["ifpen.allotrope_models.gc", "ifpen.allotrope_models.gc.*"])' in setup
        assert setup.count('"ifpen.allotrope_models==2.0.0"') == 1
        assert '"ifpen.allotrope_models==2.0.0"' in (python_output / "pyproject.toml").read_text(encoding="utf-8")
        assert (python_output / "requirements.txt").read_text(encoding="utf-8").splitlines().count(
            "ifpen.allotrope_models==2.0.0") == 1

    def test_dry_run_changes_nothing(self, python_output: Path):
        before = {p: p.read_bytes() for p in python_output.rglob("*") if p.is_file()}
        depend_on_commons(
            python_output, "ifpen.allotrope_models.gc", "ifpen.allotrope_models", "2.0.0",
            {"SecondsQuantityValue"}, dry_run=True,
        )
        assert {p: p.read_bytes() for p in python_output.rglob("*") if p.is_file()} == before


def _seconds_model(root: Path) -> Path:
    """Write a generated model with one NaN-capable field; return its path."""
    (root / "pkg" / "models").mkdir(parents=True)
    module = root / "pkg" / "models" / "seconds_quantity_value.py"
    module.write_text(
        "from __future__ import annotations\n"
        "class SecondsQuantityValue(BaseModel):\n"
        '    value: Union[StrictFloat, StrictInt] = Field(description="x")\n',
        encoding="utf-8",
    )
    return module


class TestAllowNanStrings:
    def test_types_field_and_adds_helper(self, tmp_path: Path):
        module = _seconds_model(tmp_path)
        allow_nan_strings(tmp_path, "pkg", NAN)
        allow_nan_strings(tmp_path, "pkg", NAN)  # idempotent
        text = module.read_text(encoding="utf-8")
        assert "    value: AsmDouble = Field(" in text
        assert text.count("from pkg.asm_double import AsmDouble\n") == 1
        assert (tmp_path / "pkg" / "asm_double.py").exists()

    def test_asm_double_behaviour(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        pydantic = pytest.importorskip("pydantic")
        _seconds_model(tmp_path)
        allow_nan_strings(tmp_path, "pkg", NAN)
        monkeypatch.syspath_prepend(str(tmp_path))
        from pkg.asm_double import AsmDouble  # type: ignore[import-not-found]

        class Model(pydantic.BaseModel):
            value: AsmDouble

        nan = Model.model_validate({"value": "NaN"})
        assert nan.value != nan.value  # NaN
        assert nan.model_dump() == {"value": "NaN"}
        assert Model.model_validate({"value": 1.5}).model_dump() == {"value": 1.5}
        with pytest.raises(pydantic.ValidationError):
            Model.model_validate({"value": "1.5"})

    def test_unexpected_field_type_fails(self, tmp_path: Path):
        module = _seconds_model(tmp_path)
        module.write_text(module.read_text(encoding="utf-8").replace("StrictInt", "StrictStr"), encoding="utf-8")
        with pytest.raises(PatchError):
            allow_nan_strings(tmp_path, "pkg", NAN)


class TestDescribePackage:
    PYPROJECT = (
        '[project]\nname = "ifpen.allotrope_models.gc"\nversion = "2026.9.0"\n'
        'description = "ASM Gas-Chromatography Schemas"\nauthors = [\n'
        '  {name = "OpenAPI Generator Community",email = "team@openapitools.org"},\n]\n'
        'readme = "README.md"\nkeywords = ["OpenAPI", "OpenAPI-Generator", "ASM Gas-Chromatography Schemas"]\n'
    )
    SETUP = (
        "setup(\n    name=NAME,\n    version=VERSION,\n"
        '    description="ASM Gas-Chromatography Schemas",\n'
        '    author="OpenAPI Generator community",\n    author_email="team@openapitools.org",\n'
        '    url="https://github.com/ifpen/AllotropeSimpleModelsClassGeneration",\n'
        '    keywords=["OpenAPI", "OpenAPI-Generator", "ASM Gas-Chromatography Schemas"],\n'
        "    long_description_content_type='text/markdown',\n"
        '    long_description="""\\\n    These schemas allow to read and write ASM.\n\n    More text.\n    """,  # noqa: E501\n'
        ")\n"
    )

    def test_metadata(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text(self.PYPROJECT, encoding="utf-8")
        (tmp_path / "setup.py").write_text(self.SETUP, encoding="utf-8")
        readme = PackageReadme("# GC\n", 'GC "models".', ("asm", "gc"))
        describe_package(tmp_path, readme)
        describe_package(tmp_path, readme)  # idempotent
        project = tomllib.loads((tmp_path / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        assert project["description"] == 'GC "models".'
        assert project["authors"] == [{"name": "Maxime Visconte", "email": "maxime.visconte@ifpen.fr"}]
        assert project["keywords"] == ["asm", "gc"]
        setup = (tmp_path / "setup.py").read_text(encoding="utf-8")
        ast.parse(setup)
        assert "description='GC \"models\".'," in setup
        assert "    author='Maxime Visconte',\n" in setup
        assert 'long_description=open("README.md", encoding="utf-8").read(),' in setup
        assert "OpenAPI" not in setup.replace("text/markdown", "")
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == "# GC\n"

    def test_unexpected_shape_fails(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        with pytest.raises(PatchError):
            describe_package(tmp_path, PackageReadme("# x\n", "x", ()))
