#!/usr/bin/env python3
"""Deserialize upstream ASM examples into the generated clients.

For every requested spec/language pair the verifier:

1. builds the generated *commons* package for the language once and makes it
   resolvable (local Maven repository, local NuGet feed, npm tarball, Python
   target directory), exactly as a consumer would install it;
2. selects every example of the newest ``REC/YYYY/MM`` release in the full ASM
   checkout whose ``$asm.manifest`` is one the spec accepts;
3. removes the few documented members of the official examples that the
   official schema does not declare (:data:`KNOWN_EXAMPLE_DEVIATIONS`);
4. runs a language-native probe:

   * **Java, C#, Python** deserialize each example into the generated root
     model, serialize it back to JSON, and the round-tripped document is
     compared with the original.  Any field that is dropped, altered or added
     is reported, so a model that silently ignores part of an example fails.
   * **TypeScript** models are interfaces without a runtime deserializer.
     The commons and spec packages are packed and installed into a consumer
     project without Angular, as an npm user would install them; each example
     is type-checked as an object literal with ``satisfies <RootModel>`` under
     ``tsc --strict``, with both ``bundler`` and ``nodenext`` module
     resolution.  Excess-property checks report unknown fields, and wrong
     types or enum values fail compilation.  The consumer must not contain
     Angular or RxJS, and an enum constant of each package must load through
     both ``import`` and ``require`` (issue #16, ``docs/adr/0002``).

Every missing example, generated module, toolchain or comparison failure is
reported as a failed pair; nothing is skipped silently.
"""

from __future__ import annotations

import argparse
import atexit
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from functools import partial
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from allotrope_gen.asm import find_asm_repository
from allotrope_gen.config import LANGUAGES, OUTPUT, SPECS, TYPESCRIPT_VERSION
from allotrope_gen.schema import load_yaml, root_schema


#: Example directory of each technique in the ASM checkout.
EXAMPLE_DIRS: dict[str, str] = {
    "gc": "test/adm/gas-chromatography",
    "dsc": "test/adm/dsc",
    "hplc": "test/adm/liquid-chromatography",
}

#: Generated root model class of each spec.
ROOT_MODELS: dict[str, str] = {
    spec: root_schema(load_yaml(path)["components"]["schemas"])[0] for spec, path in SPECS.items()
}

#: Content of the official examples that the official REC/2026/09 JSON
#: Schema does not declare at that location.  The schemas are open, so the
#: examples still validate, but the models follow the schema and do not
#: model these members.  Each entry is ``(parent member, member, reason)``:
#: *member* is removed from objects that are the value (or an array item) of
#: *parent member* before probing.  Every removal is printed.
KNOWN_EXAMPLE_DEVIATIONS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "gc": (
        ("processed data aggregate document", "peak list",
         "the schema declares peak list only under processed data document[]"),
        ("chromatography column document", "chromatography column film thickness",
         "not a chromatography column document property in the schema"),
        ("sample document", "description", "not a sample document property in the schema"),
        ("match result document", "InChiKey molecular structure",
         "misspelling of the declared 'InChIKey molecular structure'"),
        ("match result document", "peak identifier", "not a match result document property"),
        ("match result document", "database contributor", "not a match result document property"),
        ("match result document", "retention index", "not a match result document property"),
    ),
    "dsc": (
        ("measurement document", "diagnostic trace aggregate document",
         "the schema declares it on the measurement aggregate document"),
    ),
}

#: Maximum number of differences printed per example.
MAX_REPORTED_DIFFERENCES = 25

_REC_RE = re.compile(r"^REC$")


# ---------------------------------------------------------------------------
# Example selection
# ---------------------------------------------------------------------------


def spec_manifests(spec: str) -> set[str]:
    """Return the ``$asm.manifest`` values accepted by the spec's models."""
    manifests: set[str] = set()

    def visit(node: object) -> None:
        if isinstance(node, dict):
            manifest = node.get("$asm.manifest")
            if isinstance(manifest, dict):
                manifests.update(v for v in manifest.get("enum", []) if isinstance(v, str))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(load_yaml(SPECS[spec]))
    return manifests


def latest_examples(spec: str, repository: Path) -> list[Path]:
    """Return the examples of the newest REC release matching the spec manifest.

    Releases are directories ``REC/YYYY/MM`` below the technique's example
    directory.  Only JSON files whose ``$asm.manifest`` is accepted by the
    spec are returned, so examples of other model variants are not mixed in.
    """
    example_dir = repository / EXAMPLE_DIRS[spec]
    if not example_dir.is_dir():
        return []
    releases: dict[tuple[int, int], list[Path]] = {}
    for path in example_dir.rglob("*.json"):
        parts = path.relative_to(example_dir).parts
        if len(parts) != 4 or not _REC_RE.match(parts[0]):
            continue
        try:
            release = (int(parts[1]), int(parts[2]))
        except ValueError:
            continue
        releases.setdefault(release, []).append(path)
    manifests = spec_manifests(spec)
    for release in sorted(releases, reverse=True):
        matching = [
            path for path in sorted(releases[release])
            if _manifest_of(path) in manifests
        ]
        if matching:
            return matching
    return []


def _manifest_of(path: Path) -> str | None:
    """Return the ``$asm.manifest`` of a JSON example (``None`` if unreadable)."""
    try:
        with open(path, encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, ValueError):
        return None
    return document.get("$asm.manifest") if isinstance(document, dict) else None


def without_known_deviations(spec: str, document: object) -> tuple[object, list[str]]:
    """Return a copy of *document* without :data:`KNOWN_EXAMPLE_DEVIATIONS`.

    Returns:
        ``(cleaned document, removed)`` where *removed* lists ``parent.member``
        for each removed occurrence.
    """
    rules = KNOWN_EXAMPLE_DEVIATIONS.get(spec, ())
    removed: list[str] = []

    def clean(node: object, parent: str | None) -> object:
        if isinstance(node, list):
            return [clean(item, parent) for item in node]
        if not isinstance(node, dict):
            return node
        result = {}
        for key, value in node.items():
            if any(parent == rule_parent and key == member for rule_parent, member, _ in rules):
                removed.append(f"{parent}.{key}")
                continue
            result[key] = clean(value, key)
        return result

    return clean(document, None), removed


def with_nan_quantity(document: object) -> bool:
    """Set the first quantity value (``{"value": <number>, "unit": …}``) to ``"NaN"``.

    ASM encodes unavailable quantities as the string ``"NaN"``; the variant
    built from a real example exercises that path in every language.

    Returns:
        ``True`` if a quantity value was replaced.
    """
    if isinstance(document, dict):
        value = document.get("value")
        if "unit" in document and isinstance(value, (int, float)) and not isinstance(value, bool):
            document["value"] = "NaN"
            return True
        return any(with_nan_quantity(child) for child in document.values())
    if isinstance(document, list):
        return any(with_nan_quantity(child) for child in document)
    return False


def _with_diagnostic_trace(document: object) -> bool:
    """Add a diagnostic trace to the first measurement aggregate document.

    Diagnostic trace documents hold a ``description``, a ``data cube`` and any
    number of named ``… data cube`` members (official ``patternProperties:
    "data cube$"``), modelled as additional properties.  The official GC, DSC
    and LC examples do not cover named cubes; this small synthetic trace does.
    """
    if isinstance(document, dict):
        aggregate = document.get("measurement aggregate document")
        if isinstance(aggregate, dict) and "measurement document" in aggregate:
            aggregate["diagnostic trace aggregate document"] = {
                "diagnostic trace document": [{
                    "description": "pump pressure trace",
                    "data cube": {
                        "label": "column temperature",
                        "cube-structure": {
                            "dimensions": [{"@componentDatatype": "double", "concept": "retention time", "unit": "s"}],
                            "measures": [{"@componentDatatype": "double", "concept": "temperature", "unit": "degC"}],
                        },
                        "data": {"dimensions": [[0.0, 1.5]], "measures": [[30.0, 30.1]]},
                    },
                    "pump pressure data cube": {
                        "label": "pump pressure",
                        "cube-structure": {
                            "dimensions": [{"@componentDatatype": "double", "concept": "retention time", "unit": "s"}],
                            "measures": [{"@componentDatatype": "double", "concept": "pressure", "unit": "bar"}],
                        },
                        "data": {"dimensions": [[0.0, 1.5]], "measures": [[120.5, 121.0]]},
                    },
                }],
            }
            return True
        return any(_with_diagnostic_trace(child) for child in document.values())
    if isinstance(document, list):
        return any(_with_diagnostic_trace(child) for child in document)
    return False


_DATE_TIME_TYPE = "http://www.w3.org/2001/XMLSchema#dateTime"
_DATE_TIME_STAMP_TYPE = "http://www.w3.org/2001/XMLSchema#dateTimeStamp"
_INTEGER_TYPE = "http://www.w3.org/2001/XMLSchema#integer"


def _first(document: object, key: str) -> dict | None:
    """Return the first object reached through *key* (lists: first item)."""
    if isinstance(document, dict):
        value = document.get(key)
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict):
            return value
        children = document.values()
    elif isinstance(document, list):
        children = document
    else:
        return None
    return next((found for child in children if (found := _first(child, key)) is not None), None)


def _with_union_values(document: object, typed: bool, extended: bool) -> bool:
    """Fill the commons primitive-or-object unions of an example.

    ``DateTimeValue``, ``DateTimeStampValue`` and ``IntegerValue`` are
    ``oneOf`` a JSON primitive and an ``{"@type", "value"}`` object.  No
    official GC, DSC or LC example uses them, so this variant adds one slot of
    each union: ``start time``/``end time`` of an analysis sequence document
    (``DateTimeValue``) and, for techniques that model them (*extended*),
    ``data processing time`` of the first processed data document
    (``DateTimeStampValue``) and ``index`` of an image document
    (``IntegerValue``).  GC models neither.

    Args:
        document: Example document, modified in place.
        typed:    Use the typed-object form instead of the primitive form.
        extended: Also fill the data processing and image document slots.

    Returns:
        ``True`` when every slot was filled.
    """
    def value(primitive: object, asm_type: str) -> object:
        return {"@type": asm_type, "value": primitive} if typed else primitive

    if not isinstance(document, dict):
        return False
    technique = next((v for k, v in document.items() if k.endswith(" aggregate document")), None)
    if not isinstance(technique, dict):
        return False
    technique["analysis sequence document"] = {
        "written name": "synthetic sequence",
        "start time": value("2026-11-17T09:00:00Z", _DATE_TIME_TYPE),
        "end time": value("2026-11-17T10:30:00Z", _DATE_TIME_TYPE),
    }
    if extended:
        processed = _first(document, "processed data document")
        measurement = _first(document, "measurement document")
        if processed is None or measurement is None:
            return False
        processed["data processing document"] = {
            "data processing time": value("2026-11-17T11:00:00Z", _DATE_TIME_STAMP_TYPE),
            "method name": "synthetic union values",
        }
        measurement["image aggregate document"] = {
            "image document": [{"experimental data identifier": "image 1", "index": value(3, _INTEGER_TYPE)}],
        }
    return True


#: Synthetic variants of a spec's first example: ``(file suffix, mutation)``.
#: Each mutation must return ``True`` when it changed the document.
SYNTHETIC_VARIANTS: dict[str, tuple[tuple[str, object], ...]] = {
    spec: (
        ("diagnostic-trace", _with_diagnostic_trace),
        ("union-primitive", partial(_with_union_values, typed=False, extended=spec != "gc")),
        ("union-typed", partial(_with_union_values, typed=True, extended=spec != "gc")),
    )
    for spec in ("gc", "dsc", "hplc")
}


def prepare_examples(spec: str, examples: list[Path], work: Path) -> list[Path]:
    """Write deviation-free copies of *examples* into *work*.

    Besides one copy per example (same file name), a ``<name>.nan.json``
    variant of the first example has one quantity value set to ``"NaN"``, and
    :data:`SYNTHETIC_VARIANTS` add ``<name>.<suffix>.json`` variants.
    """
    target = work / "examples"
    target.mkdir()
    prepared = []
    for example in examples:
        with open(example, encoding="utf-8") as stream:
            cleaned, removed = without_known_deviations(spec, json.load(stream))
        for member, count in sorted(Counter(removed).items()):
            reason = next(r for p, m, r in KNOWN_EXAMPLE_DEVIATIONS[spec] if f"{p}.{m}" == member)
            print(f"[INFO] {example.name}: ignored {count} x {member!r} ({reason})")
        copy = target / example.name
        copy.write_text(json.dumps(cleaned, ensure_ascii=False), encoding="utf-8")
        prepared.append(copy)
        if example is examples[0]:
            for suffix, mutate in SYNTHETIC_VARIANTS.get(spec, ()):
                document = json.loads(json.dumps(cleaned))
                if not mutate(document):
                    raise RuntimeError(f"synthetic variant {suffix!r} does not apply to {example.name}")
                variant = target / f"{example.stem}.{suffix}.json"
                variant.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
                prepared.append(variant)
        if example is examples[0] and with_nan_quantity(cleaned):
            variant = target / f"{example.stem}.nan.json"
            variant.write_text(json.dumps(cleaned, ensure_ascii=False), encoding="utf-8")
            prepared.append(variant)
    return prepared


# ---------------------------------------------------------------------------
# Round-trip comparison
# ---------------------------------------------------------------------------


def _as_datetime(value: str) -> datetime | None:
    """Parse an ISO-8601 date-time (``Z`` suffix accepted), else ``None``."""
    if "T" not in value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_empty(value: object) -> bool:
    """Return whether *value* carries no data (null, empty list or object)."""
    return value is None or value == [] or value == {}


def compare_documents(original: object, roundtrip: object, path: str = "$") -> list[str]:
    """Return human-readable differences between two JSON documents.

    Equivalences that serializers legitimately introduce are accepted:
    numerically equal numbers (``1`` vs ``1.0``), equal instants written in
    different ISO-8601 forms, and absent vs ``null``/empty members.
    """
    if isinstance(original, dict) and isinstance(roundtrip, dict):
        differences: list[str] = []
        for key, value in original.items():
            child = f"{path}[{json.dumps(key)}]"
            if key not in roundtrip or (_is_empty(roundtrip[key]) and not _is_empty(value)):
                differences.append(f"dropped {child}")
            else:
                differences += compare_documents(value, roundtrip[key], child)
        for key, value in roundtrip.items():
            if key not in original and not _is_empty(value):
                differences.append(f"added {path}[{json.dumps(key)}] = {json.dumps(value)[:80]}")
        return differences
    if isinstance(original, list) and isinstance(roundtrip, list):
        if len(original) != len(roundtrip):
            return [f"length of {path}: {len(original)} != {len(roundtrip)}"]
        differences = []
        for index, (left, right) in enumerate(zip(original, roundtrip)):
            differences += compare_documents(left, right, f"{path}[{index}]")
        return differences
    if _is_number(original) and _is_number(roundtrip):
        equal = math.isclose(original, roundtrip, rel_tol=1e-12, abs_tol=0.0)
    elif isinstance(original, str) and isinstance(roundtrip, str):
        left, right = _as_datetime(original), _as_datetime(roundtrip)
        equal = original == roundtrip or (left is not None and left == right)
    else:
        equal = type(original) is type(roundtrip) and original == roundtrip
    if equal:
        return []
    return [f"changed {path}: {json.dumps(original)[:80]} -> {json.dumps(roundtrip)[:80]}"]


def _is_number(value: object) -> bool:
    """Return whether *value* is a JSON number (booleans excluded)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_roundtrips(examples: list[Path], outputs: Path) -> bool:
    """Compare every example with its round-tripped serialization."""
    success = True
    for example in examples:
        result = outputs / example.name
        if not result.exists():
            print(f"[ERROR] No round-trip output for {example.name}", file=sys.stderr)
            success = False
            continue
        with open(example, encoding="utf-8") as stream:
            original = json.load(stream)
        with open(result, encoding="utf-8") as stream:
            roundtrip = json.load(stream)
        differences = compare_documents(original, roundtrip)
        if differences:
            success = False
            print(f"[ERROR] {example.name}: {len(differences)} difference(s) after round-trip", file=sys.stderr)
            for difference in differences[:MAX_REPORTED_DIFFERENCES]:
                print(f"    {difference}", file=sys.stderr)
        else:
            print(f"[OK] {example.name} round-trips without loss")
    return success


# ---------------------------------------------------------------------------
# Subprocess helpers and commons preparation
# ---------------------------------------------------------------------------


def _run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> bool:
    """Run a subprocess, translating missing tools into a useful error."""
    print(f"Command: {' '.join(command)}")
    try:
        return subprocess.run(command, cwd=cwd, env=env, check=False).returncode == 0
    except OSError as exc:
        print(f"[ERROR] Could not execute {command[0]}: {exc}", file=sys.stderr)
        return False


_WORKSPACE: Path | None = None
_COMMONS: dict[str, Path | None] = {}


def _workspace() -> Path:
    """Return the per-process scratch directory (removed at exit)."""
    global _WORKSPACE
    if _WORKSPACE is None:
        _WORKSPACE = Path(tempfile.mkdtemp(prefix="asm-deserialize-"))
        atexit.register(shutil.rmtree, _WORKSPACE, ignore_errors=True)
    return _WORKSPACE


def _copy_tree(source: Path, target: Path) -> Path:
    """Copy a generated module without build artefacts."""
    shutil.copytree(
        source, target,
        ignore=shutil.ignore_patterns("node_modules", "dist", "bin", "obj", "target", "*.tgz", "__pycache__"),
    )
    return target


def commons_artifact(lang: str) -> Path | None:
    """Build the generated commons package for *lang* once per process.

    Returns the language-specific artefact location (NuGet feed, npm tarball,
    Python source copy; the Maven local repository for Java) or ``None`` when
    the build fails.
    """
    if lang in _COMMONS:
        return _COMMONS[lang]
    source = OUTPUT / "commons" / LANGUAGES[lang].output_subdir
    work = _workspace() / f"commons-{lang}"
    work.mkdir()
    artifact: Path | None = None
    print(f"\n--- Building commons ({lang}) ---")
    if not source.is_dir():
        print(f"[ERROR] Generated commons output missing: {source}", file=sys.stderr)
    elif lang == "java":
        # Installs into the local Maven repository, where spec builds resolve it.
        if _run(["mvn", "--batch-mode", "-q", "-DskipTests", "install"], _copy_tree(source, work / "src")):
            artifact = work
    elif lang == "csharp":
        project = next((p for p in sorted(source.glob("src/*/*.csproj")) if not p.stem.endswith(".Test")), None)
        feed = work / "feed"
        if project and _run(
            ["dotnet", "pack", str(_copy_tree(project.parent, work / "src") / project.name),
             "--configuration", "Release", "--output", str(feed)],
            work,
        ):
            artifact = feed
    elif lang == "python":
        artifact = _copy_tree(source, work / "src")
    elif lang == "typescript":
        build = _copy_tree(source, work / "src")
        if (
            _run(["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"], build)
            and _run(["npm", "run", "build"], build)
            and _run(["npm", "pack", "--ignore-scripts", "--pack-destination", str(work)], build)
        ):
            artifact = next(work.glob("*.tgz"), None)
    _COMMONS[lang] = artifact
    if artifact is None:
        print(f"[ERROR] Commons ({lang}) could not be built", file=sys.stderr)
    return artifact


# ---------------------------------------------------------------------------
# Language probes
# ---------------------------------------------------------------------------


def _snake(value: str) -> str:
    """Convert a generated PascalCase class name to its Python module name."""
    return "".join(("_" if char.isupper() and index else "") + char.lower() for index, char in enumerate(value))


def _io_arguments(examples: list[Path], outputs: Path) -> list[str]:
    """Return ``input output`` argument pairs for a round-trip probe."""
    return [arg for example in examples for arg in (str(example), str(outputs / example.name))]


def _verify_java(spec: str, output: Path, examples: list[Path], work: Path) -> bool:
    """Compile the spec module against commons and round-trip with Jackson."""
    if commons_artifact("java") is None:
        return False
    package = LANGUAGES["java"].package_fn(spec)
    model = ROOT_MODELS[spec]
    module = _copy_tree(output, work / "module")
    classpath_file = work / "classpath.txt"
    if not _run(
        ["mvn", "--batch-mode", "-q", "-DskipTests", "compile", "dependency:build-classpath",
         f"-Dmdep.outputFile={classpath_file}"],
        module,
    ):
        return False
    probe = work / "probe" / "AsmRoundTripProbe.java"
    probe.parent.mkdir()
    probe.write_text(
        "import com.fasterxml.jackson.databind.DeserializationFeature;\n"
        "import com.fasterxml.jackson.databind.ObjectMapper;\n"
        "import java.io.File;\n"
        f"import {package}.{model};\n"
        f"import {package}.client.ApiClient;\n"
        "public class AsmRoundTripProbe {\n"
        "  public static void main(String[] args) throws Exception {\n"
        "    ObjectMapper mapper = ApiClient.createDefaultObjectMapper()\n"
        "        .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);\n"
        "    for (int i = 0; i < args.length; i += 2) {\n"
        f"      {model} value = mapper.readValue(new File(args[i]), {model}.class);\n"
        "      mapper.writeValue(new File(args[i + 1]), value);\n"
        f"      System.out.println(\"Deserialized \" + args[i] + \" as {model}\");\n"
        "    }\n  }\n}\n",
        encoding="utf-8",
    )
    classpath = os.pathsep.join([
        str(module / "target" / "classes"),
        classpath_file.read_text(encoding="utf-8").strip(),
    ])
    if not _run(["javac", "-cp", classpath, "-d", str(probe.parent), str(probe)], work):
        return False
    outputs = work / "out"
    outputs.mkdir()
    return _run(
        ["java", "-cp", classpath + os.pathsep + str(probe.parent), "AsmRoundTripProbe",
         *_io_arguments(examples, outputs)],
        work,
    ) and check_roundtrips(examples, outputs)


def _verify_csharp(spec: str, output: Path, examples: list[Path], work: Path) -> bool:
    """Compile the spec project against the commons package and round-trip."""
    feed = commons_artifact("csharp")
    if feed is None:
        return False
    module = _copy_tree(output, work / "module")
    project = next((p for p in sorted(module.glob("src/*/*.csproj")) if not p.stem.endswith(".Test")), None)
    if project is None:
        print(f"[ERROR] No generated C# project found in {output}", file=sys.stderr)
        return False
    namespace = LANGUAGES["csharp"].package_fn(spec)
    model = ROOT_MODELS[spec]
    probe_dir = work / "probe"
    probe_dir.mkdir()
    (probe_dir / "Program.cs").write_text(
        "using System;\nusing System.IO;\nusing System.Text.Json;\n"
        "using Microsoft.Extensions.DependencyInjection;\n"
        f"using {namespace}.Client;\nusing {namespace}.Model;\n"
        # Resolve options exactly as a consumer of the generic host would.
        "var services = new ServiceCollection();\n"
        "new HostConfiguration(services);\n"
        "var options = services.BuildServiceProvider()"
        ".GetRequiredService<JsonSerializerOptionsProvider>().Options;\n"
        "for (var i = 0; i < args.Length; i += 2)\n{\n"
        f"    var value = JsonSerializer.Deserialize<{model}>(File.ReadAllText(args[i]), options)\n"
        "        ?? throw new InvalidOperationException(\"null model\");\n"
        "    File.WriteAllText(args[i + 1], JsonSerializer.Serialize(value, options));\n"
        f"    Console.WriteLine($\"Deserialized {{args[i]}} as {model}\");\n"
        "}\n",
        encoding="utf-8",
    )
    (probe_dir / "Probe.csproj").write_text(
        "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><OutputType>Exe</OutputType>"
        "<TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>"
        "<Nullable>enable</Nullable></PropertyGroup><ItemGroup>"
        f"<ProjectReference Include=\"{project}\" /></ItemGroup></Project>",
        encoding="utf-8",
    )
    # A private package cache guarantees the freshly packed commons package is
    # used rather than a previously cached build with the same version.
    env = {**os.environ, "NUGET_PACKAGES": str(_workspace() / "nuget-packages")}
    outputs = work / "out"
    outputs.mkdir()
    return _run(
        ["dotnet", "run", "--project", str(probe_dir / "Probe.csproj"), "--configuration", "Release",
         f"-p:RestoreAdditionalProjectSources={feed}", "--", *_io_arguments(examples, outputs)],
        probe_dir,
        env,
    ) and check_roundtrips(examples, outputs)


def _verify_python(spec: str, output: Path, examples: list[Path], work: Path) -> bool:
    """Install commons and spec distributions into a fresh venv and round-trip."""
    commons = commons_artifact("python")
    if commons is None:
        return False
    venv = work / "venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # Installing both distributions into one clean environment mirrors a
    # consumer's setup and checks that the spec package merges into the
    # commons ``ifpen.allotrope_models`` package without overwriting it.
    if not (
        _run([sys.executable, "-m", "venv", str(venv)], work)
        and _run(
            [str(python), "-m", "pip", "install", "-q", "--no-compile",
             str(commons), str(_copy_tree(output, work / "module"))],
            work,
        )
    ):
        return False
    package = LANGUAGES["python"].package_fn(spec)
    model = ROOT_MODELS[spec]
    probe = work / "probe.py"
    probe.write_text(
        "import sys\n"
        f"from {package}.models.{_snake(model)} import {model}\n"
        "args = sys.argv[1:]\n"
        "for source, target in zip(args[::2], args[1::2]):\n"
        "    with open(source, encoding='utf-8') as stream:\n"
        f"        value = {model}.from_json(stream.read())\n"
        "    with open(target, 'w', encoding='utf-8') as stream:\n"
        "        stream.write(value.to_json())\n"
        f"    print(f'Deserialized {{source}} as {model}')\n",
        encoding="utf-8",
    )
    outputs = work / "out"
    outputs.mkdir()
    return _run(
        [str(python), str(probe), *_io_arguments(examples, outputs)], work,
    ) and check_roundtrips(examples, outputs)


#: npm packages a models-only consumer must not receive (issue #16).
FORBIDDEN_NPM_PACKAGES = ("@angular/core", "rxjs")

#: First enum constant of a generated model file:
#: ``export namespace Peak { export const UnitEnum = { S: 's', …``.
_TS_ENUM_CONSTANT = re.compile(
    r"^export namespace (\w+) \{\s*export const (\w+) = \{\s*(\w+): '([^']*)'", re.MULTILINE,
)


def typescript_enum_constant(output: Path) -> tuple[str, str] | None:
    """Return an enum constant of a generated TypeScript package.

    Returns:
        ``(expression, value)``, e.g. ``("Peak.UnitEnum.S", "s")``, for the
        first enum constant of the ``model/`` files in name order, or ``None``
        when the package has no enum.
    """
    for source in sorted((output / "model").glob("*.ts")):
        match = _TS_ENUM_CONSTANT.search(source.read_text(encoding="utf-8"))
        if match:
            namespace, constant, member, value = match.groups()
            return f"{namespace}.{constant}.{member}", value
    return None


def forbidden_npm_packages(node_modules: Path) -> list[str]:
    """Return the :data:`FORBIDDEN_NPM_PACKAGES` installed in *node_modules*."""
    return [name for name in FORBIDDEN_NPM_PACKAGES if (node_modules / name / "package.json").exists()]


def _runtime_probes(consumer: Path, packages: dict[str, Path]) -> list[Path]:
    """Write ``import`` and ``require`` probes of one enum constant per package.

    Args:
        consumer: Consumer project directory (``"type": "module"``).
        packages: ``{npm package name: generated output directory}``.

    Returns:
        The probe scripts, to run with ``node``.
    """
    probes = []
    for index, (name, output) in enumerate(packages.items()):
        constant = typescript_enum_constant(output)
        if constant is None:
            continue
        expression, value = constant
        namespace = expression.split(".")[0]
        check = f"if ({expression} !== {json.dumps(value)}) throw new Error('{name}: {expression}');\n"
        esm = consumer / f"runtime-{index}.mjs"
        esm.write_text(f"import {{ {namespace} }} from '{name}';\n{check}", encoding="utf-8")
        cjs = consumer / f"runtime-{index}.cjs"
        cjs.write_text(f"const {{ {namespace} }} = require('{name}');\n{check}", encoding="utf-8")
        probes += [esm, cjs]
    return probes


def _verify_typescript(spec: str, output: Path, examples: list[Path], work: Path) -> bool:
    """Install commons and the spec package in a consumer and type-check each example.

    The consumer installs the packed packages like an npm user, so the
    published ``exports``, declarations and dependencies are what is tested.
    """
    tarball = commons_artifact("typescript")
    if tarball is None:
        return False
    module = _copy_tree(output, work / "module")
    # Installing the commons tarball together with the declared dependencies
    # satisfies the ``@ifpen/allotrope-models-commons`` peer dependency.
    if not (
        _run(["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund", "--no-save", str(tarball)], module)
        and _run(["npm", "run", "build"], module)
        and _run(["npm", "pack", "--ignore-scripts", "--pack-destination", str(work)], module)
    ):
        return False
    spec_tarball = next(work.glob("*.tgz"), None)
    consumer = work / "consumer"
    consumer.mkdir()
    (consumer / "package.json").write_text(
        json.dumps({"name": "asm-consumer", "private": True, "type": "module"}), encoding="utf-8",
    )
    if spec_tarball is None or not _run(
        ["npm", "install", "--no-audit", "--no-fund", str(tarball), str(spec_tarball),
         f"typescript@{TYPESCRIPT_VERSION}"],
        consumer,
    ):
        return False

    forbidden = forbidden_npm_packages(consumer / "node_modules")
    if forbidden:
        print(f"[FAIL] Installing the npm packages installs {', '.join(forbidden)}", file=sys.stderr)
        return False
    print("[OK] The npm packages install without Angular or RxJS")

    commons_name = LANGUAGES["typescript"].package_fn("")
    spec_name = LANGUAGES["typescript"].package_fn(spec)
    probes = _runtime_probes(consumer, {commons_name: OUTPUT / "commons" / "typescript", spec_name: output})
    if not probes or not all(_run(["node", probe.name], consumer) for probe in probes):
        print("[FAIL] An enum constant does not load through import and require", file=sys.stderr)
        return False
    print(f"[OK] Enum constants load through import and require ({len(probes)} probe(s))")

    model = ROOT_MODELS[spec]
    examples_ts: list[Path] = []
    for index, example in enumerate(examples):
        probe = consumer / f"asm-example-{index}.ts"
        payload = example.read_text(encoding="utf-8")
        probe.write_text(
            f"import type {{ {model} }} from '{spec_name}';\n"
            f"export const example = {payload} satisfies {model};\n",
            encoding="utf-8",
        )
        examples_ts.append(probe)
    # No --skipLibCheck: an unresolvable import in the published declarations
    # must fail instead of silently typing the models as ``any``.
    env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=8192"}
    for module_option, resolution in (("esnext", "bundler"), ("nodenext", "nodenext")):
        if not _run(
            ["npx", "tsc", "--strict", "--noEmit", "--target", "es2020",
             "--module", module_option, "--moduleResolution", resolution, *(p.name for p in examples_ts)],
            consumer,
            env,
        ):
            return False
        print(f"[OK] {len(examples)} example(s) type-check as {model} ({resolution} resolution)")
    return True


VERIFY = {
    "java": _verify_java,
    "csharp": _verify_csharp,
    "python": _verify_python,
    "typescript": _verify_typescript,
}


# ---------------------------------------------------------------------------
# Matrix
# ---------------------------------------------------------------------------


def verify_pair(spec: str, lang: str, repository: Path, *, dry_run: bool = False) -> bool:
    """Verify compilation and lossless example deserialization for one pair."""
    if spec not in SPECS or spec not in EXAMPLE_DIRS:
        print(f"[ERROR] No ASM example mapping configured for spec {spec!r}", file=sys.stderr)
        return False
    examples = latest_examples(spec, repository)
    if not examples:
        print(
            f"[ERROR] No REC example accepted by {spec} found under {repository / EXAMPLE_DIRS[spec]}",
            file=sys.stderr,
        )
        return False
    output = OUTPUT / spec / LANGUAGES[lang].output_subdir
    if not output.is_dir():
        print(f"[ERROR] Generated output missing for {spec} ({lang}): {output}", file=sys.stderr)
        return False
    print(f"\n--- Deserializing {spec} examples with {lang} ---")
    for example in examples:
        print(f"Example: {example}")
    if dry_run:
        return True
    work = Path(tempfile.mkdtemp(prefix=f"{spec}-{lang}-", dir=_workspace()))
    return VERIFY[lang](spec, output, prepare_examples(spec, examples, work), work)


def verify_matrix(specs: list[str], langs: list[str], repository: Path, *, dry_run: bool = False) -> bool:
    """Run every spec/language pair; no failed or missing pair is skipped."""
    results: dict[tuple[str, str], bool] = {}
    for spec in specs:
        for lang in langs:
            results[spec, lang] = verify_pair(spec, lang, repository, dry_run=dry_run)
            print(f"[{'PASS' if results[spec, lang] else 'FAIL'}] {spec} / {lang}")
    print("\nSummary:")
    for (spec, lang), ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {spec:<6} {lang}")
    success = all(results.values())
    print(f"\n{'[SUCCESS]' if success else '[FAILURE]'} {len(results)} deserialization checks")
    return success


def main(argv: list[str] | None = None) -> int:
    """Run the generated-client deserialization matrix from the command line."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--specs", nargs="+", default=list(SPECS), help="Instrument specs (default: all).")
    parser.add_argument("--langs", nargs="+", default=list(LANGUAGES), help="Generated languages (default: all).")
    parser.add_argument("--asm-repo", type=Path, help="Full ASM repository checkout (defaults to ASM_REPO/.env/target/asm).")
    parser.add_argument("--no-generate", action="store_true", help="Use existing generated output without refreshing it first.")
    parser.add_argument("--dry-run", action="store_true", help="Check examples and generated outputs without compiling.")
    args = parser.parse_args(argv)
    unknown_specs = set(args.specs) - set(SPECS)
    unknown_langs = set(args.langs) - set(LANGUAGES)
    if unknown_specs or unknown_langs:
        print(f"[ERROR] Unknown specs: {sorted(unknown_specs)}; unknown languages: {sorted(unknown_langs)}", file=sys.stderr)
        return 1
    try:
        repository = args.asm_repo.resolve() if args.asm_repo else find_asm_repository()
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    if not args.no_generate and not args.dry_run:
        generation = [sys.executable, str(ROOT / "generate.py"), "--specs", *args.specs, "--langs", *args.langs, "--no-verify-builds"]
        if not _run(generation, ROOT):
            print("[FAILURE] Code generation failed; deserialization checks were not run.", file=sys.stderr)
            return 1
    return 0 if verify_matrix(args.specs, args.langs, repository, dry_run=args.dry_run) else 1


if __name__ == "__main__":
    raise SystemExit(main())
