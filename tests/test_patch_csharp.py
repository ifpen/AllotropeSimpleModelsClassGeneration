"""Tests for :mod:`allotrope_gen.patch.csharp`.

The fixtures are trimmed excerpts of openapi-generator 7.23.0 output with the
exact indentation the patches anchor on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from allotrope_gen.patch import PatchError
from allotrope_gen.patch.csharp import (
    PROVIDER_ANCHOR,
    add_commons_registry,
    add_package_reference,
    guard_optional_enum_writes,
    keep_additional_properties,
    patch_doubles,
    patch_primitive_unions,
    register_commons_converters,
)


def _model_dir(root: Path, project: str = "Lib") -> Path:
    """Create and return ``src/<project>/Model``."""
    model = root / "src" / project / "Model"
    model.mkdir(parents=True, exist_ok=True)
    return model


def _host(project: Path, converters: list[str]) -> Path:
    """Write a minimal generated ``HostConfiguration.cs``."""
    (project / "Client").mkdir(parents=True, exist_ok=True)
    host = project / "Client" / "HostConfiguration.cs"
    host.write_text(
        "".join(f"            _jsonOptions.Converters.Add(new {c}());\n" for c in converters)
        + PROVIDER_ANCHOR + " JsonSerializerOptionsProvider(_jsonOptions);\n",
        encoding="utf-8",
    )
    return host


class TestAddPackageReference:
    def test_main_project_only(self, tmp_path: Path):
        for name in ("Lib", "Lib.Test"):
            project = tmp_path / "src" / name / f"{name}.csproj"
            project.parent.mkdir(parents=True)
            project.write_text('<Project Sdk="Microsoft.NET.Sdk"><ItemGroup /></Project>', encoding="utf-8")
        for _ in range(2):
            add_package_reference(tmp_path, "IFPEN.Commons", "1.0.0")
        main = (tmp_path / "src/Lib/Lib.csproj").read_text(encoding="utf-8")
        test = (tmp_path / "src/Lib.Test/Lib.Test.csproj").read_text(encoding="utf-8")
        assert main.count('Include="IFPEN.Commons"') == 1 and 'Version="1.0.0"' in main
        assert "IFPEN.Commons" not in test


class TestConverterRegistration:
    def test_commons_registry_lists_model_converters(self, tmp_path: Path):
        project = tmp_path / "src" / "Commons"
        (project / "Model").mkdir(parents=True)
        (project / "Model" / "QuantityValue.cs").write_text("", encoding="utf-8")
        _host(project, ["JsonStringEnumConverter", "DateTimeJsonConverter", "QuantityValueJsonConverter"])
        add_commons_registry(tmp_path, "Commons.Ns")
        registry = (project / "Client" / "CommonsJsonConverters.cs").read_text(encoding="utf-8")
        assert "options.Converters.Add(new Commons.Ns.Model.QuantityValueJsonConverter());" in registry
        assert "options.Converters.Add(new Commons.Ns.Model.AsmDoubleJsonConverter());" in registry
        assert "DateTimeJsonConverter" not in registry
        assert "namespace Commons.Ns.Client" in registry

    def test_commons_registry_requires_converters(self, tmp_path: Path):
        _host(tmp_path / "src" / "Commons", ["JsonStringEnumConverter"])
        with pytest.raises(PatchError):
            add_commons_registry(tmp_path, "Commons.Ns")

    def test_spec_host_registers_commons_once(self, tmp_path: Path):
        host = _host(tmp_path / "src" / "Gc", ["PeakJsonConverter"])
        for _ in range(2):
            register_commons_converters(tmp_path, "Commons.Ns")
        text = host.read_text(encoding="utf-8")
        call = "Commons.Ns.Client.CommonsJsonConverters.AddTo(_jsonOptions);"
        assert text.count(call) == 1
        assert text.index(call) < text.index(PROVIDER_ANCHOR)

    def test_missing_anchor_fails(self, tmp_path: Path):
        project = tmp_path / "src" / "Gc"
        (project / "Client").mkdir(parents=True)
        (project / "Client" / "HostConfiguration.cs").write_text("// nothing\n", encoding="utf-8")
        with pytest.raises(PatchError):
            register_commons_converters(tmp_path, "Commons.Ns")


class TestGuardOptionalEnumWrites:
    SOURCE = (
        "            var scaleRawValue = Comp.ScaleEnumToJsonValue(comp.ScaleOption.Value.Value);\n"
        '            writer.WriteString("scale", scaleRawValue);\n'
        "            var kindRawValue = Comp.KindEnumToJsonValue(comp.Kind);\n"
        '            writer.WriteString("kind", kindRawValue);\n'
    )

    def test_guards_optional_enums_only(self, tmp_path: Path):
        source = _model_dir(tmp_path) / "Comp.cs"
        source.write_text(self.SOURCE, encoding="utf-8")
        guard_optional_enum_writes(tmp_path)
        guard_optional_enum_writes(tmp_path)  # idempotent
        text = source.read_text(encoding="utf-8")
        assert text.count("if (comp.ScaleOption.IsSet)") == 1
        assert 'writer.WriteNull("scale");' in text
        # Required enums are left untouched.
        assert "            var kindRawValue = Comp.KindEnumToJsonValue(comp.Kind);\n" in text

    def test_unexpected_shape_fails(self, tmp_path: Path):
        (_model_dir(tmp_path) / "Comp.cs").write_text(
            "            var scaleRawValue = Comp.ScaleEnumToJsonValue(comp.ScaleOption.Value.Value);\n"
            '            writer.WriteNumber("scale", scaleRawValue);\n',
            encoding="utf-8",
        )
        with pytest.raises(PatchError):
            guard_optional_enum_writes(tmp_path)


class TestKeepAdditionalProperties:
    SOURCE = (
        "        public Dictionary<string, JsonElement> AdditionalProperties { get; } = new Dictionary<string, JsonElement>();\n"
        "            while (utf8JsonReader.Read())\n"
        "            {\n"
        "                    switch (localVarJsonPropertyName)\n"
        "                    {\n"
        "                        default:\n"
        "                            break;\n"
        "                    }\n"
        "            }\n"
        "            return new TraceDocument(description.Value, customInformation);\n"
        "            WriteProperties(writer, traceDocument, jsonSerializerOptions);\n"
        "            writer.WriteEndObject();\n"
    )

    def test_reads_and_writes_extra_members(self, tmp_path: Path):
        source = _model_dir(tmp_path) / "TraceDocument.cs"
        source.write_text(self.SOURCE, encoding="utf-8")
        keep_additional_properties(tmp_path)
        keep_additional_properties(tmp_path)  # idempotent
        text = source.read_text(encoding="utf-8")
        assert text.count("var additionalProperties = new Dictionary<string, JsonElement>();") == 1
        assert "additionalProperties[localVarJsonPropertyName] = JsonElement.ParseValue(ref utf8JsonReader);" in text
        assert "result.AdditionalProperties[entry.Key] = entry.Value;" in text
        assert "foreach (var entry in traceDocument.AdditionalProperties)" in text

    def test_models_without_additional_properties_are_untouched(self, tmp_path: Path):
        source = _model_dir(tmp_path) / "Plain.cs"
        source.write_text("            while (utf8JsonReader.Read())\n", encoding="utf-8")
        keep_additional_properties(tmp_path)
        assert source.read_text(encoding="utf-8") == "            while (utf8JsonReader.Read())\n"

    def test_unexpected_shape_fails(self, tmp_path: Path):
        (_model_dir(tmp_path) / "TraceDocument.cs").write_text(
            self.SOURCE.replace("default:", 'case "x":'), encoding="utf-8",
        )
        with pytest.raises(PatchError):
            keep_additional_properties(tmp_path)


class TestPatchDoubles:
    QUANTITY = (
        "        public double Value { get; set; }\n"
        '                        case "value":\n'
        "                            value = new Option<double?>(utf8JsonReader.TokenType == JsonTokenType.Null"
        " ? (double?)null : utf8JsonReader.GetDouble());\n"
        '            writer.WriteNumber("value", secondsQuantityValue.Value);\n'
    )
    MATCH = (
        "        public double MatchQualityIndex { get; set; }\n"
        "        public double? LowerLimit { get { return this.LowerLimitOption.Value; } }\n"
        "        public int? Index { get { return this.IndexOption.Value; } }\n"
        "        public decimal? Decimal { get { return this.DecimalOption.Value; } }\n"
        '            writer.WriteNumber("match quality index", match.MatchQualityIndex);\n'
        '                writer.WriteNumber("lower limit", match.LowerLimitOption.Value.Value);\n'
        '                writer.WriteNumber("@index", match.IndexOption.Value.Value);\n'
        '                writer.WriteNumber("decimal", match.DecimalOption.Value.Value);\n'
    )

    def _sources(self, root: Path) -> tuple[Path, Path]:
        model = _model_dir(root)
        quantity, match = model / "SecondsQuantityValue.cs", model / "Match.cs"
        quantity.write_text(self.QUANTITY, encoding="utf-8")
        match.write_text(self.MATCH, encoding="utf-8")
        return quantity, match

    def test_nan_properties_use_asm_double(self, tmp_path: Path):
        quantity, _ = self._sources(tmp_path)
        patch_doubles(tmp_path, "Lib.Ns", {"SecondsQuantityValue": ["value"]}, register_converter=False)
        text = quantity.read_text(encoding="utf-8")
        assert "AsmDouble.Read(ref utf8JsonReader)" in text
        assert 'AsmDouble.Write(writer, "value", secondsQuantityValue.Value);' in text
        helper = (tmp_path / "src/Lib/Model/AsmDouble.cs").read_text(encoding="utf-8")
        assert "namespace Lib.Ns.Model" in helper and "class AsmDoubleJsonConverter" in helper

    def test_other_doubles_use_shortest_format(self, tmp_path: Path):
        _, match = self._sources(tmp_path)
        patch_doubles(tmp_path, "Lib.Ns", {}, register_converter=False)
        patch_doubles(tmp_path, "Lib.Ns", {}, register_converter=False)  # idempotent
        text = match.read_text(encoding="utf-8")
        assert 'AsmDouble.WriteNumber(writer, "match quality index", match.MatchQualityIndex);' in text
        assert 'AsmDouble.WriteNumber(writer, "lower limit", match.LowerLimitOption.Value.Value);' in text
        # Integers and decimals are exact already.
        assert 'writer.WriteNumber("@index", match.IndexOption.Value.Value);' in text
        assert 'writer.WriteNumber("decimal", match.DecimalOption.Value.Value);' in text

    def test_registers_converter_in_commons_host_only_when_asked(self, tmp_path: Path):
        self._sources(tmp_path)
        host = _host(tmp_path / "src" / "Lib", ["MatchJsonConverter"])
        patch_doubles(tmp_path, "Lib.Ns", {}, register_converter=False)
        assert "AsmDoubleJsonConverter" not in host.read_text(encoding="utf-8")
        for _ in range(2):
            patch_doubles(tmp_path, "Lib.Ns", {}, register_converter=True)
        text = host.read_text(encoding="utf-8")
        assert text.count("_jsonOptions.Converters.Add(new Lib.Ns.Model.AsmDoubleJsonConverter());") == 1

    def test_unrecognized_number_write_fails(self, tmp_path: Path):
        (_model_dir(tmp_path) / "Odd.cs").write_text('            writer.WriteNumber("x", 1 + 2);\n', encoding="utf-8")
        with pytest.raises(PatchError):
            patch_doubles(tmp_path, "Lib.Ns", {}, register_converter=False)

    def test_undeclared_property_fails(self, tmp_path: Path):
        (_model_dir(tmp_path) / "Odd.cs").write_text('            writer.WriteNumber("x", odd.Missing);\n', encoding="utf-8")
        with pytest.raises(PatchError):
            patch_doubles(tmp_path, "Lib.Ns", {}, register_converter=False)


UNION = """\
namespace Lib.Ns.Model
{
    public partial class DateTimeStampValue : IValidatableObject
    {
        public DateTimeStampValue(DateTime dateTime)
        {
            DateTime = dateTime;
            OnCreated();
        }

        public DateTimeStampValue(DateTimeValueOneOf dateTimeValueOneOf)
        {
            DateTimeValueOneOf = dateTimeValueOneOf;
            OnCreated();
        }

        public DateTime? DateTime { get; set; }

        public DateTimeValueOneOf DateTimeValueOneOf { get; set; }
    }

    /// <summary>
    /// A Json converter for type <see cref="DateTimeStampValue" />
    /// </summary>
    public class DateTimeStampValueJsonConverter : JsonConverter<DateTimeStampValue>
    {
        public override DateTimeStampValue Read(ref Utf8JsonReader utf8JsonReader, Type typeToConvert, JsonSerializerOptions jsonSerializerOptions)
        {
            if (utf8JsonReader.TokenType != JsonTokenType.StartObject && utf8JsonReader.TokenType != JsonTokenType.StartArray)
                throw new JsonException();
        }

        public override void Write(Utf8JsonWriter writer, DateTimeStampValue dateTimeStampValue, JsonSerializerOptions jsonSerializerOptions)
        {
            writer.WriteStartObject();

            WriteProperties(writer, dateTimeStampValue, jsonSerializerOptions);
            writer.WriteEndObject();
        }

        public void WriteProperties(Utf8JsonWriter writer, DateTimeStampValue dateTimeStampValue, JsonSerializerOptions jsonSerializerOptions)
        {

        }
    }
}
"""


class TestPatchPrimitiveUnions:
    def test_replaces_converter(self, tmp_path: Path):
        source = _model_dir(tmp_path) / "DateTimeStampValue.cs"
        source.write_text(UNION, encoding="utf-8")
        patch_primitive_unions(tmp_path, ["DateTimeStampValue", "NotGeneratedHere"])
        patch_primitive_unions(tmp_path, ["DateTimeStampValue"])  # idempotent
        text = source.read_text(encoding="utf-8")
        assert text.count("public class DateTimeStampValueJsonConverter") == 1
        assert "WriteStartObject" not in text and "WriteProperties" not in text
        assert "                case JsonTokenType.String:\n" in text
        assert "JsonSerializer.Deserialize<DateTime>(ref utf8JsonReader, jsonSerializerOptions)" in text
        assert "JsonSerializer.Deserialize<DateTimeValueOneOf>(ref utf8JsonReader, jsonSerializerOptions)" in text
        assert "JsonSerializer.Serialize(writer, dateTimeStampValue.DateTime.Value, jsonSerializerOptions);" in text
        assert "JsonSerializer.Serialize(writer, dateTimeStampValue.DateTimeValueOneOf, jsonSerializerOptions);" in text
        # The model class and the file end are preserved.
        assert "public DateTime? DateTime { get; set; }" in text
        assert text.endswith("    }\n}\n")

    def test_integer_and_boolean_tokens(self, tmp_path: Path):
        model = _model_dir(tmp_path)
        integer = UNION.replace("DateTimeStampValue", "IntegerValue").replace("DateTimeValueOneOf", "IntegerValueOneOf")
        integer = integer.replace("DateTime dateTime", "int @int").replace("DateTime = dateTime", "Int = @int")
        integer = integer.replace("public DateTime? DateTime", "public int? Int")
        boolean = integer.replace("IntegerValue", "BooleanValue").replace("int @int", "bool @bool")
        boolean = boolean.replace("Int = @int", "Bool = @bool").replace("public int? Int", "public bool? Bool")
        (model / "IntegerValue.cs").write_text(integer, encoding="utf-8")
        (model / "BooleanValue.cs").write_text(boolean, encoding="utf-8")
        patch_primitive_unions(tmp_path, ["IntegerValue", "BooleanValue"])
        integer_text = (model / "IntegerValue.cs").read_text(encoding="utf-8")
        boolean_text = (model / "BooleanValue.cs").read_text(encoding="utf-8")
        assert "case JsonTokenType.Number:" in integer_text and "Deserialize<int>" in integer_text
        assert "case JsonTokenType.True:\n                case JsonTokenType.False:" in boolean_text

    def test_unexpected_constructors_fail(self, tmp_path: Path):
        source = _model_dir(tmp_path) / "DateTimeStampValue.cs"
        source.write_text(UNION.replace("DateTime dateTime", "Other dateTime"), encoding="utf-8")
        with pytest.raises(PatchError):
            patch_primitive_unions(tmp_path, ["DateTimeStampValue"])

    def test_missing_converter_fails(self, tmp_path: Path):
        source = _model_dir(tmp_path) / "DateTimeStampValue.cs"
        source.write_text(UNION.replace("JsonConverter<DateTimeStampValue>", "JsonConverter<Other>"), encoding="utf-8")
        with pytest.raises(PatchError):
            patch_primitive_unions(tmp_path, ["DateTimeStampValue"])
