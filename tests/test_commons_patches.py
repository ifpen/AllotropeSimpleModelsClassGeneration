"""Tests for the commons-dependency and NaN patches in :mod:`allotrope_gen.patch`."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from allotrope_gen.patch import (
    _MAVEN_NS,
    PatchError,
    add_csharp_commons_registry,
    add_csharp_package_reference,
    add_java_dependency,
    add_npm_peer_dependency,
    patch_csharp_optional_enum_writes,
    patch_nan_support,
    patch_python_package,
    register_csharp_commons_converters,
)

NS = {"m": _MAVEN_NS}


def _pom(path: Path) -> Path:
    path.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<project xmlns="{_MAVEN_NS}">'
        "<modelVersion>4.0.0</modelVersion><dependencies><dependency>"
        "<groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-core</artifactId>"
        "<version>2</version></dependency></dependencies></project>",
        encoding="utf-8",
    )
    return path


class TestAddJavaDependency:
    def test_adds_and_is_idempotent(self, tmp_path: Path):
        pom = _pom(tmp_path / "pom.xml")
        for _ in range(2):
            add_java_dependency(pom, "fr.ifpen", "allotrope-models-commons", "2026.09.0")
        deps = ET.parse(pom).getroot().findall("m:dependencies/m:dependency", NS)
        commons = [d for d in deps if d.findtext("m:artifactId", namespaces=NS) == "allotrope-models-commons"]
        assert len(deps) == 2 and len(commons) == 1
        assert commons[0].findtext("m:version", namespaces=NS) == "2026.09.0"

    def test_dry_run_does_not_write(self, tmp_path: Path):
        pom = _pom(tmp_path / "pom.xml")
        before = pom.read_text(encoding="utf-8")
        add_java_dependency(pom, "g", "a", "1", dry_run=True)
        assert pom.read_text(encoding="utf-8") == before


class TestAddCsharpPackageReference:
    def test_main_project_only(self, tmp_path: Path):
        for name in ("Lib", "Lib.Test"):
            project = tmp_path / "src" / name / f"{name}.csproj"
            project.parent.mkdir(parents=True)
            project.write_text('<Project Sdk="Microsoft.NET.Sdk"><ItemGroup /></Project>', encoding="utf-8")
        for _ in range(2):
            add_csharp_package_reference(tmp_path, "IFPEN.Commons", "1.0.0")
        main = (tmp_path / "src/Lib/Lib.csproj").read_text(encoding="utf-8")
        test = (tmp_path / "src/Lib.Test/Lib.Test.csproj").read_text(encoding="utf-8")
        assert main.count('Include="IFPEN.Commons"') == 1 and 'Version="1.0.0"' in main
        assert "IFPEN.Commons" not in test


class TestAddNpmPeerDependency:
    def test_adds_peer(self, tmp_path: Path):
        manifest = tmp_path / "package.json"
        manifest.write_text(json.dumps({"name": "x", "peerDependencies": {"@angular/core": "^19"}}), encoding="utf-8")
        add_npm_peer_dependency(manifest, "@ifpen/allotrope-models-commons", "2026.09.0")
        peers = json.loads(manifest.read_text(encoding="utf-8"))["peerDependencies"]
        assert peers == {"@angular/core": "^19", "@ifpen/allotrope-models-commons": "2026.09.0"}


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


class TestPatchPythonPackage:
    def _patch(self, out: Path) -> None:
        patch_python_package(
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


NAN = {"SecondsQuantityValue": ["value"]}


class TestPatchNanSupport:
    def test_python(self, tmp_path: Path):
        models = tmp_path / "pkg" / "models"
        models.mkdir(parents=True)
        module = models / "seconds_quantity_value.py"
        module.write_text(
            "from __future__ import annotations\n"
            "class SecondsQuantityValue(BaseModel):\n"
            '    value: Union[StrictFloat, StrictInt] = Field(description="x")\n',
            encoding="utf-8",
        )
        patch_nan_support("python", tmp_path, "pkg", NAN)
        text = module.read_text(encoding="utf-8")
        assert "    value: AsmDouble = Field(" in text
        assert "from pkg.asm_double import AsmDouble\n" in text
        assert (tmp_path / "pkg" / "asm_double.py").exists()

    def test_python_asm_double_behaviour(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        pydantic = pytest.importorskip("pydantic")
        (tmp_path / "pkg" / "models").mkdir(parents=True)
        (tmp_path / "pkg" / "models" / "seconds_quantity_value.py").write_text(
            "from __future__ import annotations\n"
            "    value: Union[StrictFloat, StrictInt] = Field()\n", encoding="utf-8",
        )
        patch_nan_support("python", tmp_path, "pkg", NAN)
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

    def test_csharp(self, tmp_path: Path):
        model = tmp_path / "src" / "Lib" / "Model"
        model.mkdir(parents=True)
        source = model / "SecondsQuantityValue.cs"
        source.write_text(
            '                        case "value":\n'
            "                            value = new Option<double?>(utf8JsonReader.TokenType == JsonTokenType.Null"
            " ? (double?)null : utf8JsonReader.GetDouble());\n"
            '            writer.WriteNumber("value", secondsQuantityValue.Value);\n',
            encoding="utf-8",
        )
        patch_nan_support("csharp", tmp_path, "Lib.Ns", NAN)
        text = source.read_text(encoding="utf-8")
        assert "AsmDouble.Read(ref utf8JsonReader)" in text
        assert 'AsmDouble.Write(writer, "value", secondsQuantityValue.Value);' in text
        helper = (model / "AsmDouble.cs").read_text(encoding="utf-8")
        assert "namespace Lib.Ns.Model" in helper

    def test_typescript(self, tmp_path: Path):
        (tmp_path / "model").mkdir()
        source = tmp_path / "model" / "secondsQuantityValue.ts"
        source.write_text("export interface SecondsQuantityValue {\n    value: number;\n}\n", encoding="utf-8")
        patch_nan_support("typescript-angular", tmp_path, "@x/y", NAN)
        patch_nan_support("typescript-angular", tmp_path, "@x/y", NAN)  # idempotent
        assert "    value: number | 'NaN';\n" in source.read_text(encoding="utf-8")

    def test_java_needs_no_patch(self, tmp_path: Path):
        patch_nan_support("java", tmp_path, "fr.x", NAN)
        assert list(tmp_path.iterdir()) == []

    def test_unexpected_generated_code_fails_loudly(self, tmp_path: Path):
        (tmp_path / "model").mkdir()
        (tmp_path / "model" / "secondsQuantityValue.ts").write_text("value: string;\n", encoding="utf-8")
        with pytest.raises(PatchError):
            patch_nan_support("typescript-angular", tmp_path, "@x/y", NAN)


def _host(project: Path, converters: list[str]) -> Path:
    """Write a minimal generated ``HostConfiguration.cs``."""
    (project / "Client").mkdir(parents=True, exist_ok=True)
    host = project / "Client" / "HostConfiguration.cs"
    host.write_text(
        "".join(f"            _jsonOptions.Converters.Add(new {c}());\n" for c in converters)
        + "            JsonSerializerOptionsProvider jsonSerializerOptionsProvider = new JsonSerializerOptionsProvider(_jsonOptions);\n",
        encoding="utf-8",
    )
    return host


class TestCsharpConverterRegistration:
    def test_commons_registry_lists_model_converters(self, tmp_path: Path):
        project = tmp_path / "src" / "Commons"
        (project / "Model").mkdir(parents=True)
        (project / "Model" / "QuantityValue.cs").write_text("", encoding="utf-8")
        _host(project, ["JsonStringEnumConverter", "DateTimeJsonConverter", "QuantityValueJsonConverter"])
        add_csharp_commons_registry(tmp_path, "Commons.Ns")
        registry = (project / "Client" / "CommonsJsonConverters.cs").read_text(encoding="utf-8")
        assert "options.Converters.Add(new Commons.Ns.Model.QuantityValueJsonConverter());" in registry
        assert "DateTimeJsonConverter" not in registry
        assert "namespace Commons.Ns.Client" in registry

    def test_commons_registry_requires_converters(self, tmp_path: Path):
        _host(tmp_path / "src" / "Commons", ["JsonStringEnumConverter"])
        with pytest.raises(PatchError):
            add_csharp_commons_registry(tmp_path, "Commons.Ns")

    def test_spec_host_registers_commons_once(self, tmp_path: Path):
        host = _host(tmp_path / "src" / "Gc", ["PeakJsonConverter"])
        for _ in range(2):
            register_csharp_commons_converters(tmp_path, "Commons.Ns")
        text = host.read_text(encoding="utf-8")
        call = "Commons.Ns.Client.CommonsJsonConverters.AddTo(_jsonOptions);"
        assert text.count(call) == 1
        assert text.index(call) < text.index("JsonSerializerOptionsProvider jsonSerializerOptionsProvider")


class TestCsharpOptionalEnumWrites:
    SOURCE = (
        "            var scaleRawValue = Comp.ScaleEnumToJsonValue(comp.ScaleOption.Value.Value);\n"
        '            writer.WriteString("scale", scaleRawValue);\n'
        "            var kindRawValue = Comp.KindEnumToJsonValue(comp.Kind);\n"
        '            writer.WriteString("kind", kindRawValue);\n'
    )

    def test_guards_optional_enums_only(self, tmp_path: Path):
        model = tmp_path / "src" / "Lib" / "Model"
        model.mkdir(parents=True)
        source = model / "Comp.cs"
        source.write_text(self.SOURCE, encoding="utf-8")
        patch_csharp_optional_enum_writes(tmp_path)
        patch_csharp_optional_enum_writes(tmp_path)  # idempotent
        text = source.read_text(encoding="utf-8")
        assert text.count("if (comp.ScaleOption.IsSet)") == 1
        assert 'writer.WriteNull("scale");' in text
        # Required enums are left untouched.
        assert "            var kindRawValue = Comp.KindEnumToJsonValue(comp.Kind);\n" in text

    def test_unexpected_shape_fails(self, tmp_path: Path):
        model = tmp_path / "src" / "Lib" / "Model"
        model.mkdir(parents=True)
        (model / "Comp.cs").write_text(
            "            var scaleRawValue = Comp.ScaleEnumToJsonValue(comp.ScaleOption.Value.Value);\n"
            '            writer.WriteNumber("scale", scaleRawValue);\n',
            encoding="utf-8",
        )
        with pytest.raises(PatchError):
            patch_csharp_optional_enum_writes(tmp_path)
