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
import fr.ifpen.allotropeconverters.allotrope_models.GasChromatographySimpleModel;

public static GasChromatographySimpleModel readAllotropeFromInputStream(InputStream inputStream) throws IOException {
    ObjectMapper objectMapper = JsonMapper.builder().addModule(new JavaTimeModule()).build();
    objectMapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    return objectMapper.readValue(
            inputStream,
            GasChromatographySimpleModel.class
    );
}
```

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

Generate all languages for the HPLC model locally with:

```powershell
python generate.py --specs hplc
```

### Docker Sandbox development

The repository includes a Docker Sandbox environment that runs OpenCode with
the published mise mixin and a small local network-policy mixin. The sandbox
uses the versions in `.mise.toml` for Python, Node.js, Java, `uv`, and the
OpenAPI Generator CLI wrapper. The policy allows the download hosts those
tools need under the sandbox's default deny-by-default egress. This keeps the
project setup separate from Dockerfiles, Compose, and host-installed SDKs.

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

Alternatively, after generation, use the repository's Docker-based verification
helper to run the language-specific verification commands in containers (Java
and C# compile; Python builds a wheel; TypeScript installs its npm dependencies):

```powershell
python verify_builds.py --specs commons hplc
```

This option requires Docker Desktop (or a Docker-compatible engine exposed as
`docker` on `PATH`) to be installed and running. The helper uses the generated
files from `target/generated-sources/`; generate the desired modules first.
Docker is used for **client build verification**, not for `generate.py` itself,
so Python, Node.js/npm, Java, and the generator CLI are still needed on the host
to generate the sources.

During instrument-spec generation, missing field descriptions are resolved from
the Allotrope Foundation Ontology through the EMBL-EBI OLS API. The first run
downloads the ontology in a few paginated requests and caches it under
`target/ontology-cache/`; subsequent and offline runs reuse that cache. Existing
field descriptions are preserved, and fields without an unambiguous ontology
definition are left unchanged with a warning. Docker Sandbox users need egress
to `www.ebi.ac.uk` for the initial ontology download.

#### Adding descriptions for new fields

Add the new property to the instrument OpenAPI YAML as usual, then run generation
for that spec (for example, `python generate.py --specs gc --langs java`). The
generation step enriches missing descriptions in the YAML before invoking the
client generator; no separate enrichment command is required. A `--dry-run`
prints generator commands but does **not** enrich or edit the YAML.

When available, use the ASM `$asm.property-class` IRI to identify a field's
ontology term. Otherwise enrichment accepts only a unique exact ontology-label
match or a safe alias supported by the checked-in official LC reference. Existing
non-empty descriptions are kept. Pure `$ref` properties are left untouched to
preserve generator-safe reference shapes; add descriptions to the referenced
schema itself if needed. Fields without a reliable match produce a warning and
are left unchanged. If a new official LC property needs alias resolution, update
`src/main/resources/_official_lc_schema_reference.json` from the authoritative
ASM schema and rerun generation. The cache is disposable and can be removed to
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
