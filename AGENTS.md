## Project Overview

**Allotrope Simple Models Class Generation** is a multi-language code-generation pipeline
maintained by [IFP Energies Nouvelles (IFPEN)](https://www.ifpenergiesnouvelles.com/).

It ingests **OpenAPI 3.1 YAML specifications** that describe
[Allotrope Simple Models (ASM)](https://www.allotrope.org/asm) and emits idiomatic client
libraries in four languages:

| Language | Package registry | Package naming | Commons package |
|---|---|---|---|
| Java | Maven Central | `fr.ifpen.allotropeconverters:allotrope-models-{spec}` | `allotrope-models-commons` |
| TypeScript (Angular) | npm | `@ifpen/allotrope-models-{spec}` | `@ifpen/allotrope-models-commons` |
| C# | NuGet | `IFPEN.AllotropeConverters.AllotropeModels.{Spec}` | `IFPEN.AllotropeConverters.AllotropeModels.Commons` |
| Python | PyPI | `ifpen.allotrope_models.{spec}` | `ifpen.allotrope_models` |

Keep the `AllotropeModels`/`allotrope-models` segment: the `fr.ifpen.allotropeconverters`
family also contains converters (`gc2asm`, `ir2asm`, `ASMUtils`). Every package is published
at its spec's OpenAPI `info.version` (commons: `COMMONS_VERSION` in `allotrope_gen/config.py`);
npm, NuGet and PyPI use the unpadded form (`2026.9.0`). The bare NuGet id
`IFPEN.AllotropeConverters.AllotropeModels` and the Maven artifact `allotrope-models`
(2025.x) are the earlier all-in-one GC packages; do not reuse them.

The pipeline splits schemas into two layers:

- **Commons** — shared schemas defined in `common.yaml`, `datacube.yaml`, and `core.yaml`; published once as
  a base package (e.g. `allotrope-models-commons`).
- **Instrument specs** — one YAML file per instrument type (e.g. `gc.yaml`); each spec
  `$ref`s commons schemas via relative paths and is published as a separate package.

---

## Repository Layout

```
AllotropeSimpleModelsClassGeneration/
├── generate.py                    # Thin CLI entry point
├── verify_builds.py               # Builds generated clients (commons first, local feeds)
├── verify_deserialization.py      # Round-trips official ASM examples in every client
├── .mise.toml                     # Pinned project toolchain for Docker Sandbox
├── sbxenv.yaml                    # Docker Sandbox OpenCode environment
├── .sandbox/mise-network/          # Project-specific tool-download egress policy
├── pyproject.toml                 # Package definition, metadata, and dependencies
├── openapitools.json              # openapi-generator-cli version pin
├── allotrope_gen/                 # Orchestration package
│   ├── __init__.py                # Package version
│   ├── asm.py                     # External ASM checkout discovery
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
│           ├── core.yaml          # Shared ASM core and hierarchy models
│           ├── gc.yaml            # Gas Chromatography REC/2026/09 instrument spec
│           └── templates/
│               └── java/          # Mustache overrides for the Java generator
├── tests/                         # Unit/integration test suite
│   ├── conftest.py                # Shared pytest fixtures
│   ├── test_cli.py                # CLI logic tests
│   ├── test_command.py            # Command construction logic tests
│   ├── test_config.py             # Configuration properties tests
│   ├── test_patch.py              # Java pom.xml patching tests
│   ├── test_pipeline.py           # Pipeline runner tests
│   ├── test_schema.py             # Schema collision and extraction tests
│   ├── test_asm.py                # External ASM checkout discovery tests
│   ├── test_bundle.py             # Spec bundling / mapping classification tests
│   ├── test_commons_patches.py    # Commons dependency, NaN and C# patch tests
│   ├── test_verify_deserialization.py # Example round-trip helper tests
│   ├── test_deserialization.py    # Full spec × language example matrix (toolchains + ASM)
│   └── test_hplc_schema.py        # ASM-backed HPLC conformance tests
├── target/
│   └── asm/                       # Optional full upstream ASM clone (git-ignored)
├── .github/
│   └── workflows/
│       └── generate.yml           # CI/CD: generate + publish to all registries
└── target/
    └── generated-sources/         # Output directory (git-ignored)
        ├── commons/{java,typescript,csharp,python}/
        └── gc/{java,typescript,csharp,python}/
```

> **`target/` is git-ignored.** Never commit generated sources or the separate ASM
> checkout. The CI workflow republishes generated sources automatically on pushes
> to `main` that touch a spec or generation code.

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

**Generation prerequisites:** the executable tools below must be discoverable on `PATH`.
PyYAML is a Python package, not a command-line executable. npm is needed to install
or update the CLI, while Node.js is needed to run it. Maven and the .NET SDK are
only needed to compile generated Java and C# clients respectively, not to run
`generate.py`.

| Tool | Version | Install |
|---|---|---|
| Python | ≥ 3.12 | system / pyenv |
| PyYAML | any current version | `python -m pip install pyyaml` |
| Node.js | ≥ 20 | nvm / system |
| npm | any current version | Installed with Node.js; used to install the CLI |
| `openapi-generator-cli` | pinned in `openapitools.json` | `npm install -g @openapitools/openapi-generator-cli` |
| Java JDK (`java` on `PATH`) | 17 | temurin / system |

The generator CLI downloads and runs its pinned JAR, so Java must be visible as
`java` to the process; setting `JAVA_HOME` alone is insufficient. On Windows,
the generation-time commands are `python.exe`, `node.exe`, `java.exe`, and the
npm-installed `openapi-generator-cli.cmd`; add the JDK `bin` directory and npm's
global executable directory to `PATH`. Check setup with `python --version`,
`node --version`, `java -version`, and `openapi-generator-cli version`. npm itself
is only needed at install/update time (and for TypeScript package builds).

On **Windows**, `generate.py` automatically invokes `openapi-generator-cli.cmd`
(the npm `.cmd` wrapper) instead of the bare executable. Do not change this unless
you also update the `_generator_cli()` function.

Instrument-spec generation enriches missing field descriptions from the current
Allotrope Foundation Ontology using the EMBL-EBI OLS API (`www.ebi.ac.uk`). The
ontology is downloaded in a few paginated requests and cached at
`target/ontology-cache/afo-terms.json`; normal repeat and offline runs reuse the
cache. Existing non-empty descriptions are not changed. The Docker Sandbox
network policy must allow `www.ebi.ac.uk` for the first lookup.

When adding instrument fields, run generation for the affected spec to enrich
missing descriptions (e.g. `python generate.py --specs gc --langs java`). This
enrichment edits the source YAML before client generation; `--dry-run` does not
run it. Prefer an exact `$asm.property-class` IRI. Otherwise the resolver uses an
unambiguous exact ontology label or a unique alias supported by the official LC
schema in the ASM checkout. Pure `$ref` properties are deliberately unchanged;
document the referenced schema instead. Unresolved fields warn and remain
unchanged. Refresh the ASM checkout when new property-class mappings are needed;
do not create or update a checked-in copy of an official schema. Remove the
ontology cache to force a fresh lookup.

### Authoritative ASM source checkout

The full upstream repository at <https://gitlab.com/allotrope-public/asm> is
the source of truth for released ASM JSON Schemas, examples, manifests, and
related modeling resources. These are licensed source files: never copy them
into this repository, even as test fixtures or generated reference files. Read
them from a separate full Git clone instead. Copy `.env.example` to the
git-ignored `.env`; its `ASM_REPO=./target/asm` default locates the sandbox
clone. Relative paths in `.env` resolve from the project root. A process-level
`ASM_REPO` environment variable overrides the file setting.

In Docker Sandbox, host checkouts are inaccessible. Clone the entire upstream
repository into the ignored project `target/asm` directory:

```sh
cp .env.example .env
mkdir -p target
git clone https://gitlab.com/allotrope-public/asm.git target/asm
```

Refresh it before using a newer ASM release, without overwriting local changes:

```sh
git -C target/asm pull --ff-only
```

The sandbox network mixin allows `gitlab.com` for this clone and future fetches.
Keep the full repository, not just the current HPLC schema: agents must consult
its current schemas, samples, manifests, and other resources when adding a
technique, updating to a new release, or checking model compatibility. HPLC
schema conformance tests and ontology property-class alias lookup consume files
from the checkout directly. HPLC conformance tests require the checkout and
fail with setup instructions if it is missing. Alias lookup selects the newest
LC `REC/YYYY/MM` embedded schema present in the clone, so refresh the full clone
to use a newer release. Clone it before validating any ASM model changes. To
use a checkout elsewhere, set its path in the ignored `.env`; do not commit a
machine-specific path.

The repository provides `sbxenv.yaml` for a Docker Sandbox using the published
OpenCode workload (`agent: opencode`), Docker's published mise v3 mixin, and a
local declaration-only mixin with the project-specific tool-download egress
policy. The published mise mixin intentionally leaves language/package download
hosts to each project; keep this policy aligned with the pinned tools in
`.mise.toml`. Keep the environment file at the repository root, as configured,
and do not add a Dockerfile or Docker Compose setup for this workflow.

The host needs the Docker Sandboxes `sbx` CLI and local virtualization support;
Docker Engine is not a generation prerequisite. On Windows 11, install the CLI
with `winget install Docker.sbx` and enable Windows Hypervisor Platform as
described in the [Docker Sandboxes installation guide](https://docs.docker.com/ai/sandboxes/install/).
Review the configuration and launch from the repository root:

```powershell
sbx login
sbx env plan
sbx env run
```

On the first run in the sandbox, install the exact versions listed in
`.mise.toml` and the project dependencies:

```sh
mise install
uv sync --locked --all-extras
```

Use `uv run pytest` for tests and `uv run python generate.py` to generate
clients. The CLI wrapper is installed by mise; the OpenAPI Generator JAR remains
pinned separately by `openapitools.json` and downloads on first generation.

To verify generated client builds without installing every language SDK on the
host, `python verify_builds.py --specs commons gc hplc` runs the language builds
in Docker containers. Generate the selected modules first; Docker Engine must be
installed, available as `docker`, and running. Generation itself still requires
the host prerequisites above.

---

## Data-Flow Summary

```
common.yaml ──┐
datacube.yaml ─┤
core.yaml ─────┘─ merged_commons_yaml() ──► openapi-generator ──► commons/{lang}/
               │                                  (+ NaN / C# converter patches)
gc.yaml ────────┤─ bundle_spec()  → target/bundled-specs/gc.bundled.yaml
                │   (local copies of reachable commons schemas; import +
                │    schema mappings onto the commons package)
                └──► openapi-generator ──► gc/{lang}/
                                           (+ commons dependency declaration)
```

1. **Commons merge** — `generate_commons()` merges `common.yaml` + `datacube.yaml` + `core.yaml` into a
   single `commons-merged.yaml` (written under `target/`), then calls the generator once per
   language. Schema name collisions between the two files are a hard error.
2. **Spec generation** — `generate_specs()` bundles each instrument YAML with the commons
   schemas it reaches (`bundle_spec()`) and passes their names as both `--import-mappings` and
   `--schema-mappings`, so spec packages reference the commons classes instead of re-emitting
   them. Bundling is required: openapi-generator's OAS 3.1 parser dereferences external
   `./core.yaml#/...` refs *inline*, which silently defeats the mappings and re-emits every
   commons class under long path-derived names. Primitive aliases (e.g. `CoreTNamed`) are not
   mapped because commons has no class for them. After generation the commons package is
   declared as a dependency (Maven dependency, NuGet `PackageReference`, npm peer dependency,
   Python requirement plus imports; the spec's parent `__init__.py` files are removed because
   they belong to commons). Before generation, missing inline-field descriptions are resolved
   by exact `$asm.property-class` IRI when available, an unambiguous exact ontology label, or a
   unique official-reference alias.
   Unresolved fields remain unchanged and are reported as warnings.
3. **Java pom.xml patch** — After Java generation, `patch_java_pom()` idempotently injects
   the `central-publishing-maven-plugin` required for Maven Central deployment.
4. **Post-generation patches** (`allotrope_gen/patch.py`, each fails loudly if the generated
   code no longer matches):
   - properties marked `x-asm-nan: true` (`QuantityValue.value` and its unit wrappers) accept
     and emit the ASM `"NaN"` string — Python `AsmDouble`, C# `AsmDouble`, TS `number | 'NaN'`;
     Jackson handles it natively;
   - C#: commons exposes `CommonsJsonConverters.AddTo(options)` and every spec
     `HostConfiguration` calls it; optional enum writes are guarded (generator 7.23.0 bug).

Validate the result with `python verify_deserialization.py`: every spec/language pair must
round-trip the official REC examples losslessly (TypeScript: strict `satisfies` type-check).
Members of official examples that the official schema does not declare at that location are
not modeled; list them with a reason in `KNOWN_EXAMPLE_DEVIATIONS` instead.

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

Add the schema to `common.yaml`, `datacube.yaml`, or `core.yaml`. It will automatically be included in
the commons package. If the same name appears in both files with different content, generation
will **fail with an error** — resolve the collision manually.

---

## CI / CD

The workflow `generate.yml` runs on:

- **Push to `main`** — only when `src/main/resources/**.yaml`, `generate.py`, `verify_builds.py`,
  the `allotrope_gen/` package, `pyproject.toml`, `uv.lock`, `.mise.toml`, `openapitools.json`,
  or the workflow itself changes.
- **Manual trigger** (`workflow_dispatch`) — accepts optional `specs`, `langs`, `dry_run`,
  `verify_builds`, and `prerelease` inputs. `prerelease` (`alpha.N`, `beta.N`, `rc.N`)
  publishes every package of the run as a pre-release (`generate.py --prerelease`):
  Maven `2026.09.0-beta.1`, npm/NuGet `2026.9.0-beta.1` (npm dist-tag `beta`), PyPI
  `2026.9.0b1`. Use it from a feature branch to test packages before a release; never
  reuse a label, registries reject republished versions.

The `generate` job installs the toolchain pinned in `.mise.toml` with `jdx/mise-action`
(the same versions as the Docker Sandbox), runs `uv sync --locked --all-extras`, then
`uv run python generate.py`, which builds every generated module (commons first). Publish
jobs resolve commons from the same run's artifact (local Maven install / NuGet feed) and
npm specs wait for `publish-npm-commons`. Lint workflow changes with `actionlint`.

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
| `NPM_TOKEN` | publish-npm-commons, publish-npm-specs (fallback until npm trusted publishing is configured per package) |

PyPI uses **trusted publishing** (no secret): pypi.org has one publisher per project
(`ifpen-allotrope-models`, `-gc`, `-dsc`, `-hplc`), each naming owner `ifpen`, repository
`AllotropeSimpleModelsClassGeneration`, workflow `generate.yml` and the GitHub environment of
its module (`pypi-commons`, `pypi-gc`, `pypi-dsc`, `pypi-hplc`; pypi.org accepts a pending
publisher configuration for one project only). A *pending* publisher creates the project on
first upload. npm jobs request an OIDC token
and use npm ≥ 11.5.1, so npm trusted publishing applies once configured on each package's
settings page (packages must exist first); until then npm uses `NPM_TOKEN`.
NuGet uses **trusted publishing** (no secret): `publish-nuget` exchanges its GitHub OIDC
token through `NuGet/login` (user `mvisconte`). The nuget.org trusted publishing policy must
name repository `ifpen/AllotropeSimpleModelsClassGeneration` and workflow `generate.yml`;
renaming the workflow file breaks publishing until the policy is updated.

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
  or `$ref: './datacube.yaml#/components/schemas/Foo'` or
  `$ref: './core.yaml#/components/schemas/Foo'`.
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
- **Do not let README.md and AGENTS.md drift out of date:** Always verify and update `README.md` and `AGENTS.md` to match changes to codebase structure, CLI syntax, prerequisites, configuration files, and examples.

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
   - Prefer a single named object with simple property types and enums over unions or
     compositions, even when this means giving up cross-field validation. In particular,
     do not encode allowed concept/unit pairs as `oneOf` branches: independent enums are
     preferable to generator-created anonymous classes. Apply this to nested data shapes
     too; use the simplest shape supported by real ASM examples rather than importing a
     generic schema with unions that expand the generated model graph.
   - Add regression tests that assert generated-model-facing schemas remain free of
     unnecessary `oneOf`, `anyOf`, and `allOf` constructs.

2. **OpenAPI file organisation**
   - All specs live under `src/main/resources/`.
   - Commons bricks (`common.yaml`, `datacube.yaml`, `core.yaml`) hold shared components. Prefer enriching
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

- 2026-11-12 - Shared core hierarchy and document schemas live in `core.yaml` and are
  published through Commons; instrument specs should reference these schemas instead of
  duplicating core model definitions.
- 2026-11-12 - GC targets the local Allotrope Simple Model Gas Chromatography
  `REC/2026/09` tabular schema.

- 2026-06-11 - Strict separation of analytical models: each analytical technique
  (e.g. GC, DSC) must be described in its own dedicated OpenAPI file (`gc.yaml`,
  `dsc.yaml`, etc.) and must never embed the models of another technique in its
  canonical file. Any overlap between techniques can only happen via the commons
  bricks (`common.yaml`, `datacube.yaml`, `core.yaml`).
- 2026-06-11 - Systematic verification of multi-language generation: a task is considered
  complete only after explicitly checking that classes are generated in all configured
  languages (Java, Python, TypeScript, C#, etc.) for each new or modified YAML file.
  This implies running `python generate.py` (or a focused subset) and verifying the
  presence of classes under `target/generated-sources/` for every requested language.
- 2026-11-18 - openapi-generator (7.23.0) inlines external `$ref`s of OAS 3.1 specs, so
  `--import-mappings` alone never matched and every spec package duplicated the commons
  classes. Specs are now bundled and mapped with import + schema mappings; check new specs
  with `verify_deserialization.py`, not only by compiling.
- 2026-11-18 - Validation-only `oneOf`/`anyOf` (e.g. `required: [retention time]` vs
  `[retention volume]`) and `$ref` with sibling keywords break generated models (wrapper
  classes, silently dropped siblings). Merge properties into one object and use named unit
  wrappers such as `NanometersQuantityValue` instead.
- 2026-11-18 - Property names must match the official REC schema exactly (e.g.
  `peak width at 4.4 % of height`); ASM unit symbols use Greek mu U+03BC (`μm`, `μL`).

## License

Source code: [CeCILL 2.1](https://opensource.org/license/cecill-2-1) (GPL-compatible).  
ASM JSON schemas: [CC-BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
