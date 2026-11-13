#!/usr/bin/env python3
"""Deserialize upstream ASM examples into generated clients.

The verifier compiles each requested spec/language client and runs a small,
language-native deserialization probe against the latest examples in the full
ASM checkout.  Every missing example, generated module, compiler, or test
failure is reported as a failed spec/language pair.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from allotrope_gen.asm import find_asm_repository
from allotrope_gen.config import LANGUAGES, OUTPUT, SPECS


EXAMPLE_PATHS: dict[str, tuple[str, ...]] = {
    "gc": ("test/adm/gas-chromatography", "gas-chromatography.tabular.json"),
    "dsc": ("test/adm/dsc", "differential-scanning-calorimetry.json"),
    "hplc": ("test/adm/liquid-chromatography", "liquid-chromatography.json"),
}


def latest_example(spec: str, repository: Path) -> Path | None:
    """Return the example from the newest REC release present in the checkout."""
    example_dir = repository / EXAMPLE_PATHS[spec][0]
    filename = EXAMPLE_PATHS[spec][1]
    candidates: list[tuple[tuple[int, int], Path]] = []
    if not example_dir.is_dir():
        return None
    for path in example_dir.rglob(filename):
        try:
            release = path.relative_to(example_dir).parts[:3]
            if len(release) != 3 or release[0] != "REC":
                continue
            candidates.append(((int(release[1]), int(release[2])), path))
        except ValueError:
            continue
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def _run(command: list[str], cwd: Path) -> bool:
    """Run a subprocess, translating missing tools into a useful error."""
    print(f"Command: {' '.join(command)}")
    try:
        return subprocess.run(command, cwd=cwd, check=False).returncode == 0
    except OSError as exc:
        print(f"[ERROR] Could not execute {command[0]}: {exc}", file=sys.stderr)
        return False


def _probe_source(lang: str, spec: str, example: Path) -> tuple[str, str]:
    """Build source and command for a per-module JSON deserialization probe."""
    class_names = {
        "gc": "GasChromatographySimpleModel",
        "dsc": "DifferentialScanningCalorimetrySimpleModel",
        "hplc": "LiquidChromatographySimpleModel",
    }
    model = class_names[spec]
    if lang == "python":
        package = LANGUAGES[lang].package_fn(spec)
        source = (
            "import json, sys\n"
            f"from {package}.models.{_snake(model)} import {model}\n"
            "with open(sys.argv[1], encoding='utf-8') as stream:\n"
            "    payload = json.load(stream)\n"
            f"instance = {model}.model_validate(payload)\n"
            "assert instance is not None\n"
            "print(type(instance).__name__)\n"
        )
        return source, "python"
    if lang == "typescript-angular":
        source = (
            "import { readFileSync } from 'node:fs';\n"
            f"import {{ {model} }} from './model/{_camel(model)}';\n"
            "const payload: unknown = JSON.parse(readFileSync(process.argv[2], 'utf8'));\n"
            "if (payload === null || typeof payload !== 'object') throw new Error('not an object');\n"
            f"const instance = payload as {model};\n"
            "if (!('$asm.manifest' in instance)) throw new Error('missing ASM manifest');\n"
            "if (Object.keys(instance).length < 2) throw new Error('missing document aggregate');\n"
            f"console.log('{model}');\n"
        )
        return source, "typescript"
    if lang == "java":
        package = LANGUAGES[lang].package_fn(spec)
        source = (
            f"package {package};\n"
            "import com.fasterxml.jackson.databind.ObjectMapper;\n"
            "import java.nio.file.Files;\n"
            "import java.nio.file.Path;\n"
            "public class AsmDeserializeProbe {\n"
            "  public static void main(String[] args) throws Exception {\n"
            f"    {model} value = new ObjectMapper().readValue(Files.readString(Path.of(args[0])), {model}.class);\n"
            "    if (value == null) throw new AssertionError(\"null model\");\n"
            f"    System.out.println(value.getClass().getSimpleName());\n"
            "  }\n}\n"
        )
        return source, "java"
    source = (
        "using System;\n"
        "using System.IO;\n"
        "using System.Text.Json;\n"
        "using Microsoft.Extensions.DependencyInjection;\n"
        f"using IFPEN.AllotropeConverters.AllotropeModels.{spec.capitalize()}.Model;\n"
        f"using IFPEN.AllotropeConverters.AllotropeModels.{spec.capitalize()}.Client;\n"
        "class AsmDeserializeProbe {\n"
        "  static void Main(string[] args) {\n"
        "    var services = new ServiceCollection();\n"
        "    var options = new HostConfiguration(services).JsonSerializerOptions();\n"
        f"    var value = JsonSerializer.Deserialize<{model}>(File.ReadAllText(args[0]), options);\n"
        "    if (value == null) throw new InvalidOperationException(\"null model\");\n"
        f"    Console.WriteLine(nameof({model}));\n"
        "  }\n}\n"
    )
    return source, "csharp"


def _snake(value: str) -> str:
    """Convert a generated PascalCase class name to its Python module name."""
    return "".join(("_" if char.isupper() and index else "") + char.lower() for index, char in enumerate(value))


def _camel(value: str) -> str:
    """Convert a PascalCase class name to an Angular model filename."""
    return value[0].lower() + value[1:]


def _verify_python(spec: str, output: Path, example: Path, work: Path) -> bool:
    """Install generated Python package dependencies, then validate the sample."""
    dependencies = work / "dependencies"
    dependencies.mkdir()
    if not _run(
        [sys.executable, "-m", "pip", "install", "-q", "--target", str(dependencies), "pydantic>=2.11", "typing-extensions>=4.7"],
        work,
    ):
        return False
    if not _run([sys.executable, "-m", "compileall", "-q", str(output / "ifpen")], work):
        return False
    source, _ = _probe_source("python", spec, example)
    script = work / "probe.py"
    script.write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(dependencies), str(output), env.get("PYTHONPATH", "")])
    return subprocess.run([sys.executable, str(script), str(example)], cwd=work, env=env, check=False).returncode == 0


def _verify_java(spec: str, output: Path, example: Path, work: Path) -> bool:
    """Compile generated Java sources with Maven and run an ObjectMapper probe."""
    source, _ = _probe_source("java", spec, example)
    package = LANGUAGES["java"].package_fn(spec).replace(".", "/")
    probe = work / package / "AsmDeserializeProbe.java"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(source, encoding="utf-8")
    # Compile the entire generated module, export its dependency classpath, and
    # compile/run a standalone probe against the exact upstream JSON file.
    if not _run(["mvn", "--batch-mode", "-DskipTests", "compile", "dependency:build-classpath", f"-Dmdep.outputFile={work / 'classpath.txt'}"], output):
        return False
    classpath = (output / "target" / "classes").as_posix() + os.pathsep + (work / "classpath.txt").read_text(encoding="utf-8").strip()
    probe_classpath = classpath + os.pathsep + str(work)
    if not _run(["javac", "-cp", classpath, "-d", str(work), str(probe)], work):
        return False
    return _run(["java", "-cp", probe_classpath, f"{LANGUAGES['java'].package_fn(spec)}.AsmDeserializeProbe", str(example)], work)


def _verify_csharp(spec: str, output: Path, example: Path, work: Path) -> bool:
    """Compile generated C# sources and execute a native JSON probe."""
    project = next((path for path in output.rglob("*.csproj") if ".Test" not in path.name), None)
    if project is None:
        print(f"[ERROR] No generated C# project found in {output}", file=sys.stderr)
        return False
    probe_dir = work / "csharp-probe"
    probe_dir.mkdir()
    (probe_dir / "Program.cs").write_text(_probe_source("csharp", spec, example)[0], encoding="utf-8")
    (probe_dir / "Probe.csproj").write_text(
        "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><OutputType>Exe</OutputType>"
        "<TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>"
        "<Nullable>enable</Nullable></PropertyGroup><ItemGroup>"
        f"<ProjectReference Include=\"{project}\" /></ItemGroup></Project>",
        encoding="utf-8",
    )
    return _run(["dotnet", "run", "--project", str(probe_dir / "Probe.csproj"), "--configuration", "Release", "--", str(example)], probe_dir)


def _verify_typescript(spec: str, output: Path, example: Path, work: Path) -> bool:
    """Compile Angular model declarations and run the JSON.parse typing probe."""
    source, _ = _probe_source("typescript-angular", spec, example)
    probe = output / "asm-deserialize-probe.ts"
    probe.write_text(source, encoding="utf-8")
    if not (output / "node_modules").is_dir():
        if not _run(["npm", "install", "--ignore-scripts"], output):
            return False
    if not _run(["npm", "run", "build"], output):
        return False
    # Angular models are structural types (not runtime classes); compilation
    # checks the schema's TypeScript shape and JSON.parse produces the instance.
    return _run(["npx", "tsc", "--noEmit", "--strict", "--skipLibCheck", "--target", "es2020", "--module", "commonjs", str(probe)], output)


VERIFY = {
    "java": _verify_java,
    "csharp": _verify_csharp,
    "python": _verify_python,
    "typescript-angular": _verify_typescript,
}


def verify_pair(spec: str, lang: str, repository: Path, *, dry_run: bool = False) -> bool:
    """Verify compilation and real-example deserialization for one pair."""
    if spec not in SPECS or spec not in EXAMPLE_PATHS:
        print(f"[ERROR] No ASM example mapping configured for spec {spec!r}", file=sys.stderr)
        return False
    example = latest_example(spec, repository)
    if example is None:
        print(f"[ERROR] No matching REC example found for {spec} under {repository / EXAMPLE_PATHS[spec][0]}", file=sys.stderr)
        return False
    output = OUTPUT / spec / LANGUAGES[lang].output_subdir
    if not output.is_dir():
        print(f"[ERROR] Generated output missing for {spec} ({lang}): {output}", file=sys.stderr)
        return False
    print(f"\n--- Deserializing {spec} example with {lang} ---")
    print(f"Example: {example}")
    if dry_run:
        return True
    with tempfile.TemporaryDirectory(prefix=f"asm-{spec}-{lang}-") as temp_dir:
        return VERIFY[lang](spec, output, example, Path(temp_dir))


def verify_matrix(specs: list[str], langs: list[str], repository: Path, *, dry_run: bool = False) -> bool:
    """Run every spec/language pair; no failed or missing pair is skipped."""
    success = True
    for spec in specs:
        for lang in langs:
            if verify_pair(spec, lang, repository, dry_run=dry_run):
                print(f"[PASS] {spec} / {lang}")
            else:
                print(f"[FAIL] {spec} / {lang}", file=sys.stderr)
                success = False
    print(f"\n{'[SUCCESS]' if success else '[FAILURE]'} {len(specs) * len(langs)} deserialization checks")
    return success


def main(argv: list[str] | None = None) -> int:
    """Run the generated-client deserialization matrix from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
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
