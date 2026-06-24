# AGENTS.md — AI Agent Guide

This file provides authoritative guidance for AI agents (Copilot, Antigravity, Cursor, etc.)
working in this repository. Read it fully before making any changes.

---

## Project Overview

**Allotrope Simple Models Class Generation** is a multi-language code-generation pipeline
maintained by [IFP Energies Nouvelles (IFPEN)](https://www.ifpenergiesnouvelles.com/).

It ingests **OpenAPI 3.1 YAML specifications** that describe
[Allotrope Simple Models (ASM)](https://www.allotrope.org/asm) and emits idiomatic client
libraries in four languages:

| Language | Package registry | Package naming |
|---|---|---|
| Java | Maven Central | `fr.ifpen.allotropeconverters:allotrope-models-{spec}` |
| TypeScript (Angular) | npm | `@ifpen/allotrope-models-{spec}` |
| C# | NuGet | `IFPEN.AllotropeConverters.AllotropeModels.{Spec}` |
| Python | PyPI | `ifpen.allotrope_models.{spec}` |

The pipeline splits schemas into two layers:

- **Commons** — shared schemas defined in `common.yaml` / `datacube.yaml`; published once as
  a base package (e.g. `allotrope-models-commons`).
- **Instrument specs** — one YAML file per instrument type (e.g. `gc.yaml`); each spec
  `$ref`s commons schemas via relative paths and is published as a separate package.

---

## Repository Layout

```
AllotropeSimpleModelsClassGeneration/
├── generate.py                    # Thin CLI entry point
├── pyproject.toml                 # Package definition, metadata, and dependencies
├── openapitools.json              # openapi-generator-cli version pin
├── allotrope_gen/                 # Orchestration package
│   ├── __init__.py                # Package version
│   ├── cli.py                     # Argument parsing and main orchestrator
│   ├── command.py                 # Command generator arguments builder
│   ├── config.py                  # Supported languages, specs, and filesystem config
│   ├── patch.py                   # pom.xml patch module
│   ├── pipeline.py                # Command subprocess execution pipeline
│   └── schema.py                  # YAML loader and schema reference collector
├── src/
│   └── main/
│       └── resources/
│           ├── common.yaml        # Shared ASM schemas (QuantityValue, units…)
│           ├── datacube.yaml      # Datacube-related shared schemas
│           ├── gc.yaml            # Gas Chromatography instrument spec
│           └── templates/
│               └── java/          # Mustache overrides for the Java generator
├── tests/                         # Unit/integration test suite
│   ├── conftest.py                # Shared pytest fixtures
│   ├── test_cli.py                # CLI logic tests
│   ├── test_command.py            # Command construction logic tests
│   ├── test_config.py             # Configuration properties tests
│   ├── test_patch.py              # Java pom.xml patching tests
│   ├── test_pipeline.py           # Pipeline runner tests
│   └── test_schema.py             # Schema collision and extraction tests
├── .github/
│   └── workflows/
│       └── generate.yml           # CI/CD: generate + publish to all registries
└── target/
    └── generated-sources/         # Output directory (git-ignored)
        ├── commons/{java,typescript,csharp,python}/
        └── gc/{java,typescript,csharp,python}/
```

> **`target/` is git-ignored.** Never commit generated sources. The CI workflow republishes
> them automatically on every push to `main` that touches a `.yaml` spec or `generate.py`.

---

## Key Entry Points

### `generate.py`

The single thin entry point for the generation pipeline. It delegates all arguments to
`allotrope_gen.cli.main()`. All language/package settings and generation orchestration live in
the `allotrope_gen` package — do **not** duplicate them in any Maven `pom.xml`.

```
python generate.py                         # generate everything
python generate.py --specs gc hplc        # only selected instrument specs
python generate.py --langs java python    # only selected languages
python generate.py --dry-run              # print commands without executing
python generate.py --commons-only         # only generate the commons libraries
python generate.py --list-specs           # list registered instrument specs
python generate.py --list-langs           # list supported languages
```

**Prerequisites** (must be on `PATH` before running):

| Tool | Version | Install |
|---|---|---|
| Python | ≥ 3.12 | system / pyenv |
| `pyyaml` | any | `pip install pyyaml` |
| `openapi-generator-cli` | pinned in `openapitools.json` | `npm install -g @openapitools/openapi-generator-cli` |
| Java JDK | 17 | temurin / system |
| Node.js | ≥ 20 | nvm / system |

On **Windows**, `generate.py` automatically invokes `openapi-generator-cli.cmd`
(the npm `.cmd` wrapper) instead of the bare executable. Do not change this unless
you also update the `_generator_cli()` function.

---

## Data-Flow Summary

```
common.yaml ──┐
datacube.yaml ─┤─ merged_commons_yaml() ──► openapi-generator ──► commons/{lang}/
               │
gc.yaml ────────┤─ schemas_referenced_from_commons()
                │   (computes importMappings)
                └──► openapi-generator ──► gc/{lang}/
```

1. **Commons merge** — `generate_commons()` merges `common.yaml` + `datacube.yaml` into a
   single `commons-merged.yaml` (written under `target/`), then calls the generator once per
   language. Schema name collisions between the two files are a hard error.
2. **Spec generation** — `generate_specs()` scans each instrument YAML for `$ref`s to
   commons files, builds `--import-mappings` so the generator does not re-emit those classes,
   then calls the generator.
3. **Java pom.xml patch** — After Java generation, `patch_java_pom()` idempotently injects
   the `central-publishing-maven-plugin` required for Maven Central deployment.

---

## Adding a New Instrument Spec

1. Drop a new OpenAPI 3.1 YAML file in `src/main/resources/` (e.g. `hplc.yaml`).
2. Add it to the `SPECS` dict in `allotrope_gen/config.py`:
   ```python
   SPECS: dict[str, Path] = {
       "gc":   RESOURCES / "gc.yaml",
       "hplc": RESOURCES / "hplc.yaml",   # ← new
   }
   ```
3. Update the CI matrix lists in `.github/workflows/generate.yml` — search for
   `# keep in sync with SPECS in allotrope_gen/config.py` and add the new spec key to every list.
4. Run `python generate.py --specs hplc --dry-run` to validate the command output before
   committing.

---

## Adding a New Language

1. Implement a `_<lang>_package(spec: str) -> str` or similar naming helper in `allotrope_gen/config.py`.
2. Add an entry to the `LANGUAGES` dict in `allotrope_gen/config.py` following the existing pattern.
3. Add the corresponding publish job to `.github/workflows/generate.yml`.

---

## Adding a New Common Schema

Add the schema to `common.yaml` or `datacube.yaml`. It will automatically be included in
the commons package. If the same name appears in both files with different content, generation
will **fail with an error** — resolve the collision manually.

---

## CI / CD

The workflow `generate.yml` runs on:

- **Push to `main`** — only when `src/main/resources/**.yaml`, `generate.py`, the `allotrope_gen/` package, or `pyproject.toml` changes.
- **Manual trigger** (`workflow_dispatch`) — accepts optional `specs`, `langs`, and
  `dry_run` inputs.

Job graph:

```
generate ──► publish-java          (Maven Central, per module)
         ──► publish-npm-commons
               └──► publish-npm-specs    (npm, per spec — depends on commons)
         ──► publish-nuget         (NuGet, per module)
         ──► publish-pypi          (PyPI, per module)
```

Required GitHub secrets:

| Secret | Used by |
|---|---|
| `MAVEN_USERNAME` | publish-java |
| `MAVEN_PASSWORD` | publish-java |
| `GPG_PRIVATE_KEY` | publish-java (artifact signing) |
| `GPG_PASSPHRASE` | publish-java |
| `NPM_TOKEN` | publish-npm-commons, publish-npm-specs |
| `NUGET_API_KEY` | publish-nuget |
| `PYPI_TOKEN` | publish-pypi |

---

## Coding Conventions

### `allotrope_gen` package

- **Python ≥ 3.12** — use modern type hints (`list[str]`, `dict[str, Path]`); avoid
  `typing` imports for built-in generics.
- All generator properties are written to a per-run JSON config file
  (`openapi-generator-config.json` inside each generator output directory) instead of CLI flags to avoid shell-quoting issues on
  Windows. Keep it this way.
- The `interpolate()` helper resolves `{spec}`, `{spec_pascal}`, `{spec_upper}` placeholders
  in `extra_props` strings. Use it for any spec-dependent property value.
- `run()` uses `shell=True` on Windows only (required by `.cmd` wrappers). Do not introduce
  platform-specific logic anywhere else.
- All code files should include high-quality, descriptive docstrings and have comprehensive unit test coverage in the `tests/` directory. Tests should be run using `pytest`.

### OpenAPI YAML specs

- Specs must be valid **OpenAPI 3.1** documents.
- Cross-file references to commons must use the relative form:
  `$ref: './common.yaml#/components/schemas/Foo'`
  or `$ref: './datacube.yaml#/components/schemas/Foo'`.
- Do not inline commons schemas inside instrument specs; always `$ref` them.
- All schemas should be defined under `components/schemas`; inline schemas in `paths`
  are not used by this pipeline.

### Java Mustache templates (`src/main/resources/templates/java/`)

- Only override templates that differ from the upstream openapi-generator defaults.
- Keep overrides minimal — prefer upstream fixes over local patches when possible.

---

## What Agents Should NOT Do

- **Do not commit to `target/`** — generated sources are ephemeral build artifacts.
- **Do not configure generation via any `pom.xml`** — `allotrope_gen/config.py` is the sole source of
  truth; Maven `pom.xml` files generated under `target/` are artifacts only and are not used in CI.
- **Do not add publishing credentials** (tokens, keys, passwords) to any tracked file.
- **Do not remove `--skip-validate-spec`** from `extra_opts` without first verifying that
  all specs pass strict OpenAPI 3.1 validation — some ASM schemas use features that the
  bundled validator rejects.
- **Do not rename the `target/generated-sources/` output structure** without updating both
  `allotrope_gen/config.py` and every `working-directory` path in `generate.yml`.
- **Do not forget to align CI/CD triggers:** Whenever you restructure packages, rename files, or add/remove dependencies (e.g., in `pyproject.toml`), you must update the triggers and paths in `.github/workflows/generate.yml` accordingly.
- **Do not let README.md drift out of date:** Always verify and update `README.md` to match changes to codebase structure, CLI syntax, prerequisites, configuration files, and examples.

---

## ASM Modeling Principles (from legacy guide)

These rules come from the earlier agent configuration and still apply to how OpenAPI
specifications are modeled. They complement (but do not override) the orchestration rules above.

1. **Extreme simplification of models**
   - The original ASM JSON Schemas are extremely complex and verbose. Your role is to
     simplify them in OpenAPI, not to reproduce their complexity.
   - Focus exclusively on generating data models (DTOs/POCOs). Do not define API `paths`
     or endpoints in the OpenAPI specs; everything lives under `components/schemas`.
   - Avoid literal translations of complex JSON Schema constructs (`anyOf`, `oneOf`, `allOf`)
     when they add noise. Flatten structures when reasonable and avoid untyped `any`/free-form
     objects.

2. **OpenAPI file organisation**
   - All specs live under `src/main/resources/`.
   - Commons bricks (`common.yaml`, `datacube.yaml`) hold shared components. Prefer enriching
     these files rather than duplicating structures in instrument specs.
   - Instrument specs (e.g. `gc.yaml`, `dsc.yaml`) should remain focused on a single
     analytical technique and reference commons via `$ref`.

3. **Versioning tied to ASM schemas**
   - The OpenAPI `info.version` must be derived from the original ASM schema `$id`.
   - Extract year and month from the ASM schema URL path segment `.../REC/YYYY/MM/...`.
   - Use the format `YYYY.MM.x` for the OpenAPI version, where `x` is a patch number.

4. **Absolute immutability of generated models**
   - Once a generated model (class/type/module) has been published, its name and structure
     are considered public and immutable.
   - You must not introduce retroactive mappings or renames (e.g. via `importMappings` or
     generator config) that would change existing model names in any language.

5. **Controlled aggregation of techniques**
   - Each analytical technique (GC, DSC, etc.) must have its own dedicated OpenAPI file
     (`gc.yaml`, `dsc.yaml`, ...). Do not embed the models for one technique inside the
     canonical file of another.
   - Do not introduce aggregated “master” OpenAPI files that bundle multiple analytical
     techniques into a single library. The rule is strictly: one technique = one file = one
     published library per language, all sharing the same commons base.

6. **Local validation and non-regression**
   - When modifying specs, validate that you do not change already-published models.
   - The recommended process is:
     1. Generate the current baseline using `python generate.py` (or the CI-equivalent
        configuration) on a clean branch.
     2. Copy `target/generated-sources/` to a temporary directory.
     3. Apply your spec changes and re-run generation.
     4. Compare both directories recursively (e.g. `diff -r`) and ensure there are no
        structural changes to previously existing models.

---

## Lessons Learned (Append Only)

- 2026-06-11 - Strict separation of analytical models: each analytical technique
  (e.g. GC, DSC) must be described in its own dedicated OpenAPI file (`gc.yaml`,
  `dsc.yaml`, etc.) and must never embed the models of another technique in its
  canonical file. Any overlap between techniques can only happen via the commons
  bricks (`common.yaml`, `datacube.yaml`).
- 2026-06-11 - Systematic verification of multi-language generation: a task is considered
  complete only after explicitly checking that classes are generated in all configured
  languages (Java, Python, TypeScript, C#, etc.) for each new or modified YAML file.
  This implies running `python generate.py` (or a focused subset) and verifying the
  presence of classes under `target/generated-sources/` for every requested language.

## License

Source code: [CeCILL 2.1](https://opensource.org/license/cecill-2-1) (GPL-compatible).  
ASM JSON schemas: [CC-BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
