"""
C# (``csharp`` generic-host library) patches.

The generic-host templates of openapi-generator 7.23.0 emit one
``JsonConverter`` per model and register them in the package's own
``Client/HostConfiguration.cs``.  Several converters are incomplete for ASM
documents; each function below fixes one problem.  All are idempotent and
raise :class:`~allotrope_gen.patch.common.PatchError` when the generated code
no longer has the expected shape.

==================================  =======================================================
Function                            Problem fixed
==================================  =======================================================
:func:`add_package_reference`       Spec projects must reference the commons NuGet package.
:func:`add_commons_registry`        Spec serializer options need the converters of every
                                    commons model: commons gets ``CommonsJsonConverters``.
:func:`register_commons_converters` Spec ``HostConfiguration`` calls
                                    ``CommonsJsonConverters.AddTo``.
:func:`guard_optional_enum_writes`  Unset optional enums threw "Nullable object must have
                                    a value" on serialization.
:func:`keep_additional_properties`  ``AdditionalProperties`` (named ``… data cube``
                                    members) were dropped on read and never written.
:func:`patch_doubles`               ASM ``"NaN"`` strings (``x-asm-nan``) were rejected,
                                    and .NET Framework wrote doubles with 17 significant
                                    digits (issue #13).
:func:`patch_primitive_unions`      ``oneOf`` primitive/object unions (``DateTimeValue``,
                                    ``DateTimeStampValue``, ``IntegerValue``) were written
                                    as ``{}`` and could not read the primitive form
                                    (issue #12).
==================================  =======================================================

Generated C# layout assumed by the patches: one project per package under
``src/<Namespace>/`` (plus a ``<Namespace>.Test`` project that is never
patched), models in ``Model/<Class>.cs`` with the converter in the same file,
and ``Client/HostConfiguration.cs``.
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .common import PatchError, lower_camel, render_template, replace_exact, report, write_text

# ---------------------------------------------------------------------------
# Generated project layout
# ---------------------------------------------------------------------------

#: Line of ``HostConfiguration`` before which converter registrations are added.
PROVIDER_ANCHOR = "            JsonSerializerOptionsProvider jsonSerializerOptionsProvider = new"

_CONVERTER_REGISTRATION = re.compile(r"_jsonOptions\.Converters\.Add\(new (\w+JsonConverter)\(\)\);")


def projects(output_dir: Path) -> list[Path]:
    """Return the generated (non-test) C# project directories under ``src/``."""
    return [p for p in sorted(output_dir.glob("src/*")) if p.is_dir() and not p.name.endswith(".Test")]


def _models(output_dir: Path) -> list[Path]:
    """Return every generated model source of the (non-test) projects."""
    return [source for project in projects(output_dir) for source in sorted((project / "Model").glob("*.cs"))]


def _insert_before_provider(host: Path, line: str, dry_run: bool) -> bool:
    """Insert *line* before :data:`PROVIDER_ANCHOR` in *host* (idempotent).

    Returns:
        ``True`` if the line was added, ``False`` if it was already present.

    Raises:
        PatchError: If the anchor is not found exactly once.
    """
    text = host.read_text(encoding="utf-8")
    if line in text:
        return False
    if text.count(PROVIDER_ANCHOR) != 1:
        raise PatchError(f"{host}: serializer options provider anchor not found")
    write_text(host, text.replace(PROVIDER_ANCHOR, line + PROVIDER_ANCHOR, 1), dry_run)
    return True


# ---------------------------------------------------------------------------
# Commons package dependency and converter registration
# ---------------------------------------------------------------------------


def add_package_reference(output_dir: Path, package_id: str, version: str, dry_run: bool = False) -> None:
    """Add a ``PackageReference`` to the generated (non-test) ``.csproj``.

    Args:
        output_dir: Generated C# output directory.
        package_id: NuGet package id of the dependency.
        version:    Exact dependency version.
        dry_run:    When ``True``, report but do not write.
    """
    csprojs = [p for p in sorted(output_dir.glob("src/*/*.csproj")) if not p.stem.endswith(".Test")]
    if not csprojs:
        print(f"[WARN] No C# project found, skipping patch: {output_dir}", file=sys.stderr)
        return
    for csproj in csprojs:
        tree = ET.parse(csproj)
        root = tree.getroot()
        if any(ref.get("Include") == package_id for ref in root.iter("PackageReference")):
            report("csproj patch", f"{package_id} reference already present, skipping.")
            continue
        ET.SubElement(ET.SubElement(root, "ItemGroup"), "PackageReference", Include=package_id, Version=version)
        report("csproj patch", f"added PackageReference {package_id} {version}")
        if not dry_run:
            tree.write(csproj, encoding="utf-8", xml_declaration=False)


def add_commons_registry(output_dir: Path, namespace: str, dry_run: bool = False) -> None:
    """Generate ``Client/CommonsJsonConverters.cs`` in the commons project.

    Spec models embed commons models, so a spec's serializer options must hold
    every commons converter, including those of commons-internal helper
    models.  ``CommonsJsonConverters.AddTo(options)`` registers them; the
    list is read from the generated ``HostConfiguration`` (model converters
    only) so it always matches the models actually emitted, and it ends with
    the ``AsmDoubleJsonConverter`` of :func:`patch_doubles`.

    Args:
        output_dir: Generated commons C# output directory.
        namespace:  Commons namespace.
        dry_run:    When ``True``, report but do not write.

    Raises:
        PatchError: If no model converter registration is found.
    """
    for project in projects(output_dir):
        host = project / "Client" / "HostConfiguration.cs"
        if not host.exists():
            continue
        converters = [
            name for name in _CONVERTER_REGISTRATION.findall(host.read_text(encoding="utf-8"))
            if name != "AsmDoubleJsonConverter"
            and (project / "Model" / f"{name.removesuffix('JsonConverter').removesuffix('Nullable')}.cs").exists()
        ]
        if not converters:
            raise PatchError(f"{host}: no model converter registrations found")
        registrations = "\n".join(
            f"            options.Converters.Add(new {namespace}.Model.{name}());" for name in converters
        )
        report("csharp patch", f"CommonsJsonConverters registers {len(converters)} model converter(s)")
        write_text(
            project / "Client" / "CommonsJsonConverters.cs",
            render_template("CommonsJsonConverters.cs", namespace=namespace, registrations=registrations),
            dry_run,
        )


def register_commons_converters(output_dir: Path, commons_namespace: str, dry_run: bool = False) -> None:
    """Make a spec ``HostConfiguration`` call ``CommonsJsonConverters.AddTo``.

    Args:
        output_dir:        Generated spec C# output directory.
        commons_namespace: Commons namespace.
        dry_run:           When ``True``, report but do not write.

    Raises:
        PatchError: If ``HostConfiguration`` lacks :data:`PROVIDER_ANCHOR`.
    """
    call = f"            {commons_namespace}.Client.CommonsJsonConverters.AddTo(_jsonOptions);\n"
    for project in projects(output_dir):
        host = project / "Client" / "HostConfiguration.cs"
        if host.exists() and _insert_before_provider(host, call, dry_run):
            report("csharp patch", "HostConfiguration registers the commons converters")


# ---------------------------------------------------------------------------
# Optional enum serialization
# ---------------------------------------------------------------------------

_OPTIONAL_ENUM_WRITE = re.compile(
    r"^            var (?P<var>\w+RawValue) = (?P<call>\w+\.\w+EnumToJsonValue)"
    r"\((?P<obj>\w+)\.(?P<opt>\w+Option)\.Value\.Value\);\n"
    r'            writer\.WriteString\("(?P<json>[^"]+)", (?P=var)\);\n',
    re.MULTILINE,
)
_UNGUARDED_OPTIONAL_ENUM = re.compile(r"^            var \w+RawValue = .*Option\.Value\.Value\);", re.MULTILINE)


def _guarded_enum_write(match: re.Match[str]) -> str:
    """Return the guarded replacement for one optional enum write."""
    option = f"{match['obj']}.{match['opt']}"
    return (
        f"            if ({option}.IsSet)\n"
        f"                if ({option}.Value != null)\n"
        "                {\n"
        f"                    var {match['var']} = {match['call']}({option}.Value.Value);\n"
        f'                    writer.WriteString("{match["json"]}", {match["var"]});\n'
        "                }\n"
        "                else\n"
        f'                    writer.WriteNull("{match["json"]}");\n'
    )


def guard_optional_enum_writes(output_dir: Path, dry_run: bool = False) -> None:
    """Write optional enum properties only when set, like other optionals.

    The generated converters dereference ``XOption.Value.Value`` of optional
    enums unconditionally, so serializing a model whose optional enum is unset
    throws "Nullable object must have a value".

    Raises:
        PatchError: If an unguarded optional enum write of another shape remains.
    """
    patched = 0
    for source in _models(output_dir):
        text = source.read_text(encoding="utf-8")
        new_text, count = _OPTIONAL_ENUM_WRITE.subn(_guarded_enum_write, text)
        if _UNGUARDED_OPTIONAL_ENUM.search(new_text):
            raise PatchError(f"{source}: unguarded optional enum write has an unexpected shape")
        if count:
            patched += count
            write_text(source, new_text, dry_run)
    report("csharp patch", f"guarded {patched} optional enum write(s)")


# ---------------------------------------------------------------------------
# Additional properties
# ---------------------------------------------------------------------------

_EXTRA_MARKER = "public Dictionary<string, JsonElement> AdditionalProperties"
_EXTRA_PATCHED = "// allotrope_gen: additional properties"


def keep_additional_properties(output_dir: Path, dry_run: bool = False) -> None:
    """Make converters read and write ``AdditionalProperties``.

    Models with ``additionalProperties`` (diagnostic trace documents: any
    ``… data cube`` member) get an ``AdditionalProperties`` dictionary, but
    the converters skip unknown members on read (``default: break``) and never
    write the dictionary, so those members were silently lost.

    Raises:
        PatchError: If a converter no longer has the expected shape.
    """
    patched = 0
    for source in _models(output_dir):
        text = source.read_text(encoding="utf-8")
        if _EXTRA_MARKER not in text or _EXTRA_PATCHED in text:
            continue
        name = source.stem
        variable = lower_camel(name)
        # Collect unknown members while reading…
        text = replace_exact(
            text,
            r"^(            while \(utf8JsonReader\.Read\(\)\)\n)",
            f"            var additionalProperties = new Dictionary<string, JsonElement>(); {_EXTRA_PATCHED}\n\\1",
            source,
        )
        text = replace_exact(
            text,
            r"^(                        default:\n)(                            break;\n)",
            "\\1                            additionalProperties[localVarJsonPropertyName] = "
            "JsonElement.ParseValue(ref utf8JsonReader);\n\\2",
            source,
        )
        # …store them on the model…
        text = replace_exact(
            text,
            rf"^            return new {re.escape(name)}\((.*)\);\n",
            f"            var result = new {name}(\\1);\n"
            "            foreach (var entry in additionalProperties)\n"
            "                result.AdditionalProperties[entry.Key] = entry.Value;\n"
            "            return result;\n",
            source,
        )
        # …and write them after the declared properties.
        text = replace_exact(
            text,
            rf"^(            WriteProperties\(writer, {re.escape(variable)}, jsonSerializerOptions\);\n)",
            f"\\1            foreach (var entry in {variable}.AdditionalProperties)\n"
            "            {\n"
            "                writer.WritePropertyName(entry.Key);\n"
            "                entry.Value.WriteTo(writer);\n"
            "            }\n",
            source,
        )
        patched += 1
        write_text(source, text, dry_run)
    report("csharp patch", f"{patched} converter(s) keep additional properties")


# ---------------------------------------------------------------------------
# Doubles: ASM "NaN" strings and shortest round-trip formatting
# ---------------------------------------------------------------------------

#: ``writer.WriteNumber("<json>", <object>.<Property>[Option.Value.Value]);``
_WRITE_NUMBER = re.compile(
    r'writer\.WriteNumber\("(?P<json>[^"]+)", (?P<expr>\w+\.(?P<prop>\w+?)(?:Option\.Value\.Value)?)\);'
)
_ANY_WRITE_NUMBER = re.compile(r"writer\.WriteNumber\([^;]*\);")


def _property_type(text: str, prop: str, source: Path) -> str:
    """Return the declared C# type of public property *prop* in *text*.

    Raises:
        PatchError: If the property declaration is not found.
    """
    match = re.search(rf"^        public (\S+) {re.escape(prop)} \{{", text, re.MULTILINE)
    if match is None:
        raise PatchError(f"{source}: declaration of property {prop!r} not found")
    return match.group(1)


def _use_asm_double_for_nan(text: str, props: list[str], source: Path) -> str:
    """Route reads and writes of NaN-capable *props* through ``AsmDouble``."""
    for prop in props:
        if f'AsmDouble.Write(writer, "{prop}",' in text:
            continue
        text = replace_exact(
            text,
            rf'(case "{re.escape(prop)}":\n[^\n]*?)utf8JsonReader\.GetDouble\(\)',
            r"\1AsmDouble.Read(ref utf8JsonReader)",
            source,
        )
        text = replace_exact(
            text,
            rf'writer\.WriteNumber\("{re.escape(prop)}", ([^;]+)\);',
            rf'AsmDouble.Write(writer, "{prop}", \1);',
            source,
        )
    return text


def _format_double_writes(text: str, source: Path) -> tuple[str, int]:
    """Replace ``writer.WriteNumber`` of ``double`` properties with ``AsmDouble.WriteNumber``.

    Returns:
        The new text and the number of writes replaced.

    Raises:
        PatchError: If a ``WriteNumber`` call has an unrecognized argument.
    """
    for call in _ANY_WRITE_NUMBER.findall(text):
        if not _WRITE_NUMBER.fullmatch(call):
            raise PatchError(f"{source}: unrecognized number write {call!r}")

    def replace(match: re.Match[str]) -> str:
        if _property_type(text, match["prop"], source) not in ("double", "double?"):
            return match[0]
        return f'AsmDouble.WriteNumber(writer, "{match["json"]}", {match["expr"]});'

    new_text = _WRITE_NUMBER.sub(replace, text)
    return new_text, new_text.count("AsmDouble.WriteNumber(") - text.count("AsmDouble.WriteNumber(")


def patch_doubles(
    output_dir: Path,
    namespace: str,
    nan_properties: dict[str, list[str]],
    *,
    register_converter: bool,
    dry_run: bool = False,
) -> None:
    """Read and write doubles the ASM way in every converter.

    Adds ``Model/AsmDouble.cs`` (template ``AsmDouble.cs``) to each project
    and routes the generated converters through it:

    * NaN-capable properties (``x-asm-nan``) read ``"NaN"`` as
      ``double.NaN`` and write NaN back as ``"NaN"``.  Java and the other
      languages are patched separately; see :mod:`allotrope_gen.patch`.
    * Every other ``double`` property is written with
      ``AsmDouble.WriteNumber``: on .NET Framework (``net48`` target)
      ``Utf8JsonWriter.WriteNumber`` formats doubles with ``G17``, so 0.2375
      became 0.23749999999999999 (issue #13).  The helper writes the shortest
      round-trippable form on every framework.
    * Doubles that converters hand to ``JsonSerializer`` (``List<double>``,
      data cube values) use the registered ``AsmDoubleJsonConverter``.  It is
      registered in the commons ``HostConfiguration`` (*register_converter*)
      and in ``CommonsJsonConverters``, which every spec host calls.

    Args:
        output_dir:         Generated C# output directory.
        namespace:          Namespace of the generated package.
        nan_properties:     ``{class name: [JSON property names]}`` of the
                            classes generated in this output.
        register_converter: Register ``AsmDoubleJsonConverter`` in this
                            output's ``HostConfiguration`` (commons only).
        dry_run:            When ``True``, report but do not write.

    Raises:
        PatchError: If a converter no longer has the expected shape.
    """
    nan_classes = formatted = 0
    for project in projects(output_dir):
        for source in sorted((project / "Model").glob("*.cs")):
            if source.name == "AsmDouble.cs":
                continue
            original = text = source.read_text(encoding="utf-8")
            if source.stem in nan_properties:
                text = _use_asm_double_for_nan(text, nan_properties[source.stem], source)
                nan_classes += text != original
            text, count = _format_double_writes(text, source)
            formatted += count
            if text != original:
                write_text(source, text, dry_run)
        write_text(project / "Model" / "AsmDouble.cs", render_template("AsmDouble.cs", namespace=namespace), dry_run)
        host = project / "Client" / "HostConfiguration.cs"
        if register_converter and host.exists():
            _insert_before_provider(
                host, f"            _jsonOptions.Converters.Add(new {namespace}.Model.AsmDoubleJsonConverter());\n", dry_run,
            )
    report("csharp patch", f"{nan_classes} class(es) accept the ASM \"NaN\" string")
    report("csharp patch", f"{formatted} double write(s) use the shortest round-trip format")


# ---------------------------------------------------------------------------
# oneOf primitive/object unions
# ---------------------------------------------------------------------------

#: JSON token types of each C# primitive a ``oneOf`` branch can map to.
_PRIMITIVE_TOKENS: dict[str, tuple[str, ...]] = {
    "DateTime": ("String",),
    "DateTimeOffset": ("String",),
    "Guid": ("String",),
    "string": ("String",),
    "int": ("Number",),
    "long": ("Number",),
    "float": ("Number",),
    "double": ("Number",),
    "decimal": ("Number",),
    "bool": ("True", "False"),
}
_JSON_KIND = {"String": "string", "Number": "number", "True": "boolean"}
_UNION_PATCHED = "Replaced by allotrope_gen"


def _union_constructors(text: str, model: str, source: Path) -> tuple[tuple[str, str], tuple[str, str]]:
    """Return ``((type, property), (type, property))`` of the primitive and object branches.

    A generated ``oneOf`` model has one single-argument constructor per
    branch, each assigning its argument to the branch property.

    Raises:
        PatchError: If there are not exactly one primitive and one object branch.
    """
    constructors = re.findall(
        rf"^        public {re.escape(model)}\((\w+) (@?\w+)\)\n        \{{\n            (\w+) = \2;\n",
        text,
        re.MULTILINE,
    )
    primitive = [(t, p) for t, _, p in constructors if t in _PRIMITIVE_TOKENS]
    objects = [(t, p) for t, _, p in constructors if t not in _PRIMITIVE_TOKENS]
    if len(primitive) != 1 or len(objects) != 1:
        raise PatchError(f"{source}: expected one primitive and one object constructor, found {constructors}")
    return primitive[0], objects[0]


def patch_primitive_unions(output_dir: Path, unions: list[str], dry_run: bool = False) -> None:
    """Replace the converters of ``oneOf`` primitive/object unions.

    ASM encodes some scalars either as a bare primitive or as a typed object
    (``"2026-11-17T09:00:00Z"`` or ``{"@type": …, "value": …}``).  The
    generated converter throws on anything but a JSON object when reading,
    and writes ``WriteStartObject`` + an empty ``WriteProperties`` +
    ``WriteEndObject``, i.e. ``{}``, for both branches (issue #12).

    The whole converter class is replaced by template
    ``PrimitiveUnionJsonConverter.cs``: it reads the primitive token or the
    object, and writes whichever branch is set, both through
    ``JsonSerializer`` so the registered converters (dates, objects) apply.

    Args:
        output_dir: Generated C# output directory.
        unions:     Union schema names (see
                    :func:`allotrope_gen.schema.primitive_unions`); models not
                    generated in this output (mapped onto commons) are skipped.
        dry_run:    When ``True``, report but do not write.

    Raises:
        PatchError: If a union model or converter has an unexpected shape.
    """
    patched = 0
    for project in projects(output_dir):
        for model in unions:
            source = project / "Model" / f"{model}.cs"
            if not source.exists():
                continue
            text = source.read_text(encoding="utf-8")
            if _UNION_PATCHED in text:
                continue
            (primitive_type, primitive_property), (object_type, object_property) = (
                _union_constructors(text, model, source)
            )
            tokens = _PRIMITIVE_TOKENS[primitive_type]
            variable = lower_camel(model)
            value = f"{variable}.{primitive_property}"
            if _property_type(text, primitive_property, source).endswith("?"):
                value += ".Value"
            converter = render_template(
                "PrimitiveUnionJsonConverter.cs",
                model=model,
                variable=variable,
                json_kind=_JSON_KIND[tokens[0]],
                primitive_cases="\n".join(f"                case JsonTokenType.{token}:" for token in tokens),
                primitive_type=primitive_type,
                primitive_property=primitive_property,
                primitive_value=value,
                object_type=object_type,
                object_property=object_property,
            )
            text = replace_exact(
                text,
                rf"^    public class {re.escape(model)}JsonConverter : JsonConverter<{re.escape(model)}>\n"
                r"    \{\n(?:.*\n)*?    \}\n",
                converter.replace("\\", "\\\\"),
                source,
            )
            patched += 1
            write_text(source, text, dry_run)
    report("csharp patch", f"{patched} primitive/object union converter(s) replaced")
