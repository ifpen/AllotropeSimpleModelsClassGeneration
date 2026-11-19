# Allotrope Simple Models Class Generation

[![Maven Central Version][maven-central-badge]][maven-central]

![NPM Version](https://img.shields.io/npm/v/@ifpen/allotrope-models)

[![License CeCILL 2.1][license-badge]][cecill-2.1]

A set of libraries compatible with the Allotrope Simple Models.

A project from [IFP Energies Nouvelles][ifpen], a public research, innovation and
training organization in the fields of energy, transport and the environment.

## Documentation
    
Complete API documentation for all supported languages is available here:
[https://ifpen.github.io/AllotropeSimpleModelsClassGeneration/](https://ifpen.github.io/AllotropeSimpleModelsClassGeneration/)

## Philosophy

This project aims to create libraries of classes that are compatible with the ASM JSON files (ie. a compliant JSON file can be deserialized into one of the classes)

Generated classes are intended to be understandable data models, not literal translations
of every JSON Schema constraint. Prefer named, flat object schemas with simple property
types and enums. Avoid `oneOf`, `anyOf`, and `allOf` when they create anonymous or deeply
nested generated classes; if needed, accept less cross-field validation rather than
encoding every permitted property combination. For example, GC chromatogram dimensions
use independent concept and unit enums instead of a union of retention-time/seconds and
retention-volume/milliliters variants. Keep property names and value shapes compatible
with the ASM examples, and add tests to prevent accidental schema complexity from
returning.

Neither the project nor the libraries are endorsed by the Allotrope Foundation.



## Usage

The generated model classes can be used to deserialize and serialize ASM JSON
with the appropriate JSON library for the target language.

```java
import fr.ifpen.allotropeconverters.allotrope_models.gc.GasChromatographySimpleModel;

public static GasChromatographySimpleModel readAllotropeFromInputStream(InputStream inputStream) throws IOException {
    ObjectMapper objectMapper = JsonMapper.builder().addModule(new JavaTimeModule()).build();
    objectMapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    return objectMapper.readValue(
            inputStream,
            GasChromatographySimpleModel.class
    );
}
```

Each instrument package (`gc`, `dsc`, `hplc`) depends on the commons package of
the same language and reuses its classes (quantity values, core documents,
datacube) instead of re-declaring them. ASM writes an unavailable quantity as the
JSON string `"NaN"`; every client reads it into, and writes it back from, a
floating-point NaN (`QuantityValue.value`, TypeScript type `number | 'NaN'`).
In C#, resolve `JsonSerializerOptionsProvider` from the services configured by an
instrument package's `HostConfiguration`; it registers the commons converters too.

## Available instrument models

The generator currently includes Gas Chromatography (`gc`), Differential
Scanning Calorimetry (`dsc`), and Liquid Chromatography (`hplc`). The HPLC
specification targets the ASM Liquid Chromatography `REC/2026/09` tabular
manifest and projects the full schema reachable from the LC root, including
the common technique hierarchy, LC-specific detector and pump identifiers,
chromatogram datacubes, sample and injection metadata, processed data and peak
fields, and fraction collection. The shared ASM value and datacube definitions
remain in the Commons specifications; the LC document only references them.

The generated C# package and namespace follow the existing naming convention:

- NuGet package: `IFPEN.AllotropeConverters.AllotropeModels.Hplc`
- Root model namespace: `IFPEN.AllotropeConverters.AllotropeModels.Hplc.Model`
- Root model: `LiquidChromatographySimpleModel`
- Shared classes: NuGet package `IFPEN.AllotropeConverters.AllotropeModels.Commons`

Every package is versioned after its specification (`info.version`, e.g. `2026.09.0`,
published as `2026.9.0` on npm, NuGet and PyPI). The earlier GC-only NuGet package
`IFPEN.AllotropeConverters.AllotropeModels` (2025.6.x) is superseded by
`IFPEN.AllotropeConverters.AllotropeModels.Gc`.

### Pre-releases

To try new versions in other projects before a release, run the *Generate and
publish Allotrope models* workflow manually (`workflow_dispatch`) on the branch to
test, with the `prerelease` input set to `alpha.N`, `beta.N` or `rc.N`. Locally the
same option is `python generate.py --prerelease beta.1`. All packages of the run,
including commons, then get the pre-release version and depend on each other's
exact pre-release:

| Registry | Version | Install it with |
|---|---|---|
| Maven Central | `2026.09.0-beta1` | `<version>2026.09.0-beta1</version>` |
| npm | `2026.9.0-beta.1`, dist-tag `beta` (staged, see below) | `npm install @ifpen/allotrope-models-gc@beta` (plus `@ifpen/allotrope-models-commons@beta`) |
| NuGet | `2026.9.0-beta.1` | `dotnet add package IFPEN.AllotropeConverters.AllotropeModels.Gc --prerelease` |
| PyPI | `2026.9.0b1` | `pip install --pre ifpen.allotrope_models.gc` (or `==2026.9.0b1`) |

npm packages are *staged* (`npm stage publish`): no 2FA is needed in CI, and nothing is
public until a maintainer approves each staged version on npmjs.com (or with
`npm stage approve <id>`, which asks for 2FA). Approve commons first.

Pre-releases never become "latest" (npm publishes them under their own dist-tag;
NuGet and pip ignore them unless asked). Published versions are immutable in every
registry, so a fix needs the next label (`beta.2`); the final `2026.9.0` stays free.

Generate all languages for the HPLC model locally with:

```powershell
python generate.py --specs hplc
```

### ASM source repository

The complete upstream [ASM repository][asm] is the source of truth for released
JSON Schemas, example JSON documents, manifests, and related modeling resources.
Those files are licensed source material: do not copy them into this repository.
Instead, work from a separate full clone. Copy `.env.example` to `.env`; the
committed example defaults `ASM_REPO` to `./target/asm`. `.env` is git-ignored.
Paths in it are relative to the project root. A process-level `ASM_REPO`
environment variable overrides the `.env` setting.

In Docker Sandboxes, clone the full upstream repository inside the project
workspace; `target/` is ignored by Git and the sandbox retains it between runs:

```sh
cp .env.example .env
mkdir -p target
git clone https://gitlab.com/allotrope-public/asm.git target/asm
```

Before modeling against newer releases, refresh the clone without discarding
local work:

```sh
git -C target/asm pull --ff-only
```

Edit the ignored `.env` if the checkout is elsewhere. The full clone—not an
export of a single schema—is required when adding or updating models, checking real examples,
or reviewing manifests and other ASM resources. HPLC conformance tests and
description alias resolution read the relevant files directly from this checkout.
Alias lookup automatically uses the newest LC `REC/YYYY/MM` schema in the clone;
refresh the clone to make a newer release available.
The HPLC conformance tests require this checkout and fail with setup instructions
if it is missing.

For a checkout outside `target/asm`, set its path in the ignored `.env`, for
example `ASM_REPO=D:/path/to/asm` on Windows. Do not commit machine-specific
paths.

### Docker Sandbox development

The repository includes a Docker Sandbox environment that runs OpenCode with
the published mise mixin and a small local network-policy mixin. The sandbox
uses the versions in `.mise.toml` for Python, Node.js, Java, `uv`, and the
OpenAPI Generator CLI wrapper. Its egress policy allows the tool-download
hosts, OLS, and GitLab so agents can clone and refresh the complete ASM source
repository. This keeps project setup separate from Dockerfiles, Compose, and
host-installed SDKs.

Install Docker Sandboxes on Windows 11, then sign in:

```powershell
winget install Docker.sbx
sbx login
```

Windows local sandboxes require Windows Hypervisor Platform. See the
[Docker Sandboxes installation guide](https://docs.docker.com/ai/sandboxes/install/)
for platform requirements and setup.

From the repository root, review and start the environment:

```powershell
sbx env plan
sbx env run
```

On first start, install the pinned toolchain and sync the Python dependencies
from the lockfile in the OpenCode terminal:

```sh
mise install
uv sync --locked --all-extras
```

Clone the complete ASM repository inside the sandbox workspace before inspecting
or changing instrument models, or running ASM conformance tests:

```sh
cp .env.example .env
mkdir -p target
git clone https://gitlab.com/allotrope-public/asm.git target/asm
```

On later sandbox sessions, update it with `git -C target/asm pull --ff-only`.
The network policy explicitly permits `gitlab.com` for these commands.

Run project tests or generate models inside the sandbox:

```sh
uv run pytest
uv run python generate.py --dry-run
uv run python generate.py
```

The first real generation downloads the OpenAPI Generator JAR pinned by
`openapitools.json`. The `sbx` CLI and local virtualization support are needed
on the host; the language toolchain is installed inside the sandbox.

### Generating and building locally

Generation runs OpenAPI Generator on your machine. These executables must be
available on `PATH` while generating:

| Tool | Required version | Used for |
|---|---:|---|
| `python` | 3.12 or newer | Running `generate.py` and project tests |
| `node` | 20 or newer | Running the npm-installed generator CLI |
| `java` | JDK 17 | Running OpenAPI Generator |
| `openapi-generator-cli` | Version pinned in `openapitools.json` | Generating language clients |

PyYAML is a Python package dependency, not a separate executable. `npm` is
needed to install or update the generator CLI; it is not required just to invoke
an already-installed CLI. For TypeScript package builds, Node.js and npm are
both needed.

Install the Python and generator dependencies, then check that each executable
is discoverable and that Java is available to the generator:

```powershell
python -m pip install pyyaml pytest pytest-cov
npm install -g @openapitools/openapi-generator-cli
python --version
node --version
java -version
openapi-generator-cli version
```

The generator CLI reads the pinned version from `openapitools.json` and downloads
its JAR when first run. Merely adding `JAVA_HOME` is not enough if `java` itself
cannot be found by the process. On Windows, the runtime commands are
`python.exe`, `node.exe`, `java.exe`, and `openapi-generator-cli.cmd`. Add the
JDK's `bin` directory and npm's global executable directory (which contains the
`.cmd` wrapper) to `PATH`. Use `Get-Command python, node, java,
openapi-generator-cli.cmd` in PowerShell to check command discovery. The CLI
version check also confirms that its JAR can launch.

Generation does **not** require Maven or the .NET SDK. For direct host builds,
make `mvn` available on `PATH` for Java and `dotnet` for C#. TypeScript uses npm;
Python packaging uses `build` (install it with `python -m pip install build`).
You can check the optional Java and C# build commands with `mvn --version` and
`dotnet --version`.

After generation, `generate.py` builds the generated clients with the local SDKs
(disable with `--no-verify-builds`); the same step can be run on its own:

```powershell
python verify_builds.py --specs commons hplc
```

Commons is always built first and published to local feeds under
`target/local-packages/` (Maven local repository, NuGet feed, npm tarball),
because instrument packages depend on it.

#### Validating deserialization of the ASM examples

`verify_deserialization.py` checks every spec/language pair against the official
examples of the newest `REC/YYYY/MM` release in the ASM checkout whose
`$asm.manifest` the spec accepts:

```powershell
python verify_deserialization.py                       # regenerate, then all pairs
python verify_deserialization.py --no-generate --specs gc --langs java
```

Java, C# and Python deserialize each example, serialize it back and must
reproduce it without any dropped, altered or added member (Java additionally
fails on unknown properties). TypeScript type-checks each example as an object
literal with `satisfies <RootModel>` under `tsc --strict`. A variant of each
technique's first example with one quantity set to `"NaN"` is checked as well.
A few members of the official examples that the official schema does not
declare at that location (for example the misspelled `InChiKey molecular
structure`) are listed, with their reason, in `KNOWN_EXAMPLE_DEVIATIONS` and
removed before probing; every removal is printed. Maven, the .NET SDK, Node.js
and Python must be available, plus NuGet and npm registry access.

During instrument-spec generation, missing field descriptions are resolved from
the Allotrope Foundation Ontology through the EMBL-EBI OLS API. The first run
downloads the ontology and caches it under `target/ontology-cache/`; subsequent
and offline runs reuse that cache. Existing field descriptions are preserved,
and fields without an unambiguous definition are left unchanged with a warning.
Docker Sandbox egress allows both `www.ebi.ac.uk` and `gitlab.com`.

#### Adding descriptions for new fields

Add the new property to the instrument OpenAPI YAML as usual, then run generation
for that spec (for example, `python generate.py --specs gc --langs java`). The
generation step enriches missing descriptions in the YAML before invoking the
client generator; no separate enrichment command is required. A `--dry-run`
prints generator commands but does **not** enrich or edit the YAML.

When available, use the ASM `$asm.property-class` IRI to identify a field's
ontology term. Otherwise enrichment accepts only a unique exact ontology-label
match or a safe alias found in the official LC schema in the ASM checkout.
Refresh the full ASM clone before relying on a newer release. Existing
non-empty descriptions are kept. Pure `$ref` properties are left untouched to
preserve generator-safe reference shapes; add descriptions to the referenced
schema itself if needed. Fields without a reliable match produce a warning and
are left unchanged. The ontology cache is disposable and can be removed to
force a fresh OLS download.

Generated sources are build artifacts under `target/generated-sources/` and
are not committed. Registry publication is performed by the repository's CI
workflow after changes are merged to `main`.


## License

The code is available under the [CeCILL 2.1][cecill-2.1] license,
which is compatible with GNU GPL, GNU Affero GPL and EUPL.  
The [ASM JSON schemas][asm] are available under [CC-BY-NC 4.0][cc-by-nc-4.0] terms.


[//]: # (@formatter:off)

[maven-central-badge]: https://img.shields.io/maven-central/v/fr.ifpen.allotropeconverters/gc2asm

[license-badge]: https://img.shields.io/badge/License-CeCILL_2.1-green

[maven-central]: https://central.sonatype.com/artifact/fr.ifpen.allotropeconverters/gc2asm
[cecill-2.1]: https://opensource.org/license/cecill-2-1
[ifpen]: https://www.ifpenergiesnouvelles.com/
[asm]: https://www.allotrope.org/asm
[cc-by-nc-4.0]: https://creativecommons.org/licenses/by-nc/4.0/
