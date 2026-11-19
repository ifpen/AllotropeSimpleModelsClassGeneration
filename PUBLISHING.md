# Publishing the Allotrope model packages

This document describes how the generated libraries are versioned, published and
released, how each registry is configured, and how to recover from the failures
seen so far. The workflow is `.github/workflows/generate.yml`; all package names and
versions are derived from `allotrope_gen/config.py`.

> [!IMPORTANT]
> **Final versions are published only by publishing a GitHub release** whose tag matches
> the package versions (`v2026.09.0`). Pushes and merges to `main` only generate and build;
> manual runs publish pre-releases only. The rules are implemented in
> `allotrope_gen/release.py` (unit-tested in `tests/test_release.py`).

## 1. What is published

Every run publishes one *commons* package and one package per instrument spec, in four
languages. Instrument packages depend on the commons package of the same version.

| Module | Maven Central | npm | NuGet | PyPI |
|---|---|---|---|---|
| commons | `fr.ifpen.allotropeconverters:allotrope-models-commons` | `@ifpen/allotrope-models-commons` | `IFPEN.AllotropeConverters.AllotropeModels.Commons` | `ifpen-allotrope-models` (`ifpen.allotrope_models`) |
| GC | `…:allotrope-models-gc` | `@ifpen/allotrope-models-gc` | `IFPEN.AllotropeConverters.AllotropeModels.Gc` | `ifpen-allotrope-models-gc` |
| DSC | `…:allotrope-models-dsc` | `@ifpen/allotrope-models-dsc` | `IFPEN.AllotropeConverters.AllotropeModels.Dsc` | `ifpen-allotrope-models-dsc` |
| HPLC | `…:allotrope-models-hplc` | `@ifpen/allotrope-models-hplc` | `IFPEN.AllotropeConverters.AllotropeModels.Hplc` | `ifpen-allotrope-models-hplc` |

How each registry authenticates the workflow:

| Registry | Authentication | Repository secrets |
|---|---|---|
| Maven Central | Central Portal **user token** + GPG signature | `MAVEN_USERNAME`, `MAVEN_PASSWORD`, `GPG_PRIVATE_KEY`, `GPG_PASSPHRASE` |
| npm | **Staged publishing** (`npm stage publish`), approved by a maintainer; OIDC trusted publishing once configured, `NPM_TOKEN` as fallback | `NPM_TOKEN` (until trusted publishing is enabled on every package) |
| NuGet | **Trusted publishing** (GitHub OIDC → `NuGet/login`) | none |
| PyPI | **Trusted publishing** (GitHub OIDC → `pypa/gh-action-pypi-publish`) | none |

### Legacy packages (do not reuse)

Before 2026, a single GC-only model was published as `fr.ifpen.allotropeconverters:allotrope-models`
(Maven, `2025-03` … `2025-06.02`), `IFPEN.AllotropeConverters.AllotropeModels` (NuGet,
`2025.6.4`, `2025.6.5`) and `@ifpen/allotrope-models` (npm, up to `2025.6.4`). They are
superseded by the `…-gc` / `.Gc` packages; deprecate them (§7.4) and never publish to these
ids again. The `fr.ifpen.allotropeconverters` group also contains converters (`gc2asm`,
`ir2asm`, `ASMUtils`), which is why the model packages keep the `allotrope-models` /
`AllotropeModels` segment.

## 2. Versions

Each module is published at its spec's OpenAPI `info.version` (`YYYY.MM.x`, derived from the
ASM `REC/YYYY/MM` release — see AGENTS.md). The commons version is `COMMONS_VERSION` in
`allotrope_gen/config.py`. Registries spell the same version differently; the generator writes
every form (`version_placeholders()`):

| | Maven | npm / NuGet | PyPI |
|---|---|---|---|
| Release | `2026.09.0` | `2026.9.0` | `2026.9.0` |
| Pre-release `beta.1` | `2026.09.0-beta1` | `2026.9.0-beta.1` | `2026.9.0b1` |
| Pre-release `rc.2` | `2026.09.0-rc2` | `2026.9.0-rc.2` | `2026.9.0rc2` |

- Pre-release labels are `alpha.N`, `beta.N` or `rc.N` (`generate.py --prerelease`, workflow
  input `prerelease`); anything else is rejected before generation.
- Maven pre-releases have **no dot** in the qualifier: Central's validator rejected
  `…-2026.09.0-beta.1.pom` bundles with *"Bundle has content that does NOT have a .pom file"*.
- Instrument packages declare the commons dependency with the *exact* version of the run,
  including its pre-release label (`cfg.commons_version` templates).
- **Versions are immutable.** No registry lets a version be replaced; Maven Central and NuGet
  never delete. A fix needs a new version: the next pre-release label (`beta.2`), or a patch
  bump of `info.version` / `COMMONS_VERSION` (`2026.09.1`). Bump `COMMONS_VERSION` whenever a
  commons schema changes, and the spec's `info.version` whenever its spec changes.

## 3. How a run is started

The `prepare` job turns the triggering event into a plan (`python -m allotrope_gen.release`):

| Trigger | Publishes | Notes |
|---|---|---|
| **GitHub release published**, tag `v2026.09.0` | **Final versions** of all modules and languages | The tag must equal `COMMONS_VERSION` and every spec's `info.version`, and the release must *not* be marked as pre-release; otherwise the run fails before generating. |
| GitHub release published, tag `v2026.09.0-beta.2`, marked as **pre-release** | That pre-release (label `beta.2`) | Same version check; the label must be `alpha.N`, `beta.N` or `rc.N`. |
| Manual run with `prerelease: beta.N` | That pre-release | Inputs `specs` / `langs` select subsets; any branch. |
| Manual run without `prerelease`, or with `dry_run` | Nothing | Builds only (or, with `dry_run`, prints the generator commands). |
| Push to `main` touching specs, generator, dependencies, toolchain or workflow | Nothing | Generates and builds every module (verification). |

- `dry_run: true` installs the toolchain and prints the generator commands only; it does not
  generate, build, sign or publish. Use it to check the CI setup.
- A manual run can target any branch; the workflow file of that branch is used. Pre-releases
  are published from feature branches this way.
- The release tag uses the **Maven** spelling of the version (`v2026.09.0`), the pre-release
  label keeps its dot (`v2026.09.0-beta.2`); each registry then gets its own spelling (§2).
- **Re-running failed jobs** reuses the workflow file and the generated artifact of the
  original run. After changing the workflow, start a *new* run instead.

From a terminal (needs a token with *Actions: Read and write*):

```sh
gh workflow run generate.yml --ref <branch> -f prerelease=beta.1                 # pre-release
gh workflow run generate.yml --ref <branch> -f prerelease=beta.1 -f dry_run=true # setup check
gh run watch                                                                     # follow it
```

## 4. Pipeline

```
prepare (plan) ──► generate ──► publish-java        (matrix: commons, gc, dsc, hplc)
                     ──► publish-npm-commons
                           └──► publish-npm-specs   (matrix: gc, dsc, hplc)
                     ──► publish-nuget       (matrix: commons, gc, dsc, hplc)
                     ──► publish-pypi        (matrix: commons, gc, dsc, hplc; environment pypi-<module>)
```

- **prepare** plans the run (`allotrope_gen.release`): selected specs and languages,
  pre-release label, whether to publish; it validates the release tag against the versions.
  Publish jobs run only when the plan says `publish`.
- **generate** installs the toolchain pinned in `.mise.toml` (`jdx/mise-action`), runs
  `uv sync --locked --all-extras` and `uv run python generate.py [--prerelease …]`, which
  generates every module and builds it (`verify_builds.py`, commons first). The output is
  uploaded as the `generated-sources` artifact; every publish job starts from it.
- **publish-java**: `mvn deploy -P sign-artifacts` with the `central-publishing-maven-plugin`
  (0.12.0, `autoPublish`). Spec modules first `mvn install` the commons module of the
  artifact. The job waits until Central has *validated* the bundle; publication to
  `repo1.maven.org` follows asynchronously.
- **publish-npm-commons / -specs**: `npm stage publish ./dist --access public --tag <tag>`
  (tag `latest`, or `alpha`/`beta`/`rc` for pre-releases). Spec jobs build and pack the
  commons of the artifact to satisfy their peer dependency, because a *staged* commons is not
  installable from the registry.
- **publish-nuget**: `NuGet/login` exchanges the job's OIDC token for a short-lived API key;
  spec modules restore commons from a local feed packed from the artifact; `dotnet nuget push
  --skip-duplicate`.
- **publish-pypi**: `python -m build`, then `pypa/gh-action-pypi-publish` (OIDC,
  `skip-existing`), each module in its own GitHub environment `pypi-<module>`.

## 5. Registry configuration

### 5.1 Maven Central

1. The namespace `fr.ifpen.allotropeconverters` must be **verified** on
   <https://central.sonatype.com> for the publishing account.
2. Generate a **user token** (central.sonatype.com → *Account* → *Generate User Token*) and
   store its two parts as `MAVEN_USERNAME` and `MAVEN_PASSWORD`. The account password or an
   old OSSRH token is rejected with `401`.
3. Signing: `GPG_PRIVATE_KEY` (ASCII-armored private key) and `GPG_PASSPHRASE`. The public key
   must be published on a public key server (e.g. `keys.openpgp.org`); Central checks
   signatures against it.
4. Generated poms carry the required metadata (name, description, URL, licence, developer,
   SCM) from `LANGUAGES["java"].extra_props`; the publishing plugin is injected by
   `patch_java_pom()` (`_CENTRAL_PLUGIN_VERSION`).
5. Deployments are listed at <https://central.sonatype.com/publishing/deployments>; a failed
   validation shows the reason per component there.

### 5.2 npm

1. The organization/scope `@ifpen` must exist and the publishing account must be allowed to
   publish to it.
2. **First publish of a new package** (npm configures trusted publishers per *existing*
   package): store a granular access token as `NPM_TOKEN`, with *Read and write* on the
   `@ifpen` **scope** (a token limited to one package cannot create new ones — npm answers
   `404` on `PUT`). Staging needs no 2FA bypass.
3. **Trusted publishing** (afterwards, per package): on npmjs.com, package → *Settings* →
   *Trusted publisher* → GitHub Actions, organization `ifpen`, repository
   `AllotropeSimpleModelsClassGeneration`, workflow `generate.yml`, no environment. Allow
   *stage publish*. npm checks the package's `repository.url`
   (`https://github.com/ifpen/AllotropeSimpleModelsClassGeneration`). The jobs install npm
   11.21.1 (trusted publishing needs ≥ 11.5.1) and request `id-token: write`; npm uses OIDC
   when a trusted publisher exists and falls back to `NPM_TOKEN` otherwise. Once all packages
   have one, delete the token.
4. **Approval**: every run only *stages* versions. A maintainer approves them on npmjs.com, or
   with `npm stage list` / `npm stage approve <id>` (2FA required). Approve **commons first**,
   then the specs; until approval, the versions are not installable. A staged version can be
   rejected with `npm stage reject <id>`.

### 5.3 NuGet

One trusted publishing policy on nuget.org (owner `mvisconte`): GitHub Actions, repository
owner `ifpen`, repository `AllotropeSimpleModelsClassGeneration`, workflow **`generate.yml`**,
package glob `*`. The job logs in with `NuGet/login` (`user: mvisconte`); there is no API-key
secret. Renaming the workflow file breaks publishing until the policy is updated.

### 5.4 PyPI

One trusted publisher per project, all with owner `ifpen`, repository
`AllotropeSimpleModelsClassGeneration`, workflow `generate.yml` and the module's environment:

| Project | Environment |
|---|---|
| `ifpen-allotrope-models` | `pypi-commons` |
| `ifpen-allotrope-models-gc` | `pypi-gc` |
| `ifpen-allotrope-models-dsc` | `pypi-dsc` |
| `ifpen-allotrope-models-hplc` | `pypi-hplc` |

- PyPI accepts a given (repository, workflow, environment) configuration for **one** project
  only, hence one GitHub environment per module. GitHub creates the environments on first use;
  protection rules (required reviewers) can be added to them to require an approval before
  PyPI publishing.
- New projects are created through *pending* publishers; an account may hold **at most 3
  pending publishers** at a time. A pending publisher becomes a normal one after the first
  successful upload, which frees the slot.
- Enter project names without spaces; PyPI normalizes `.`/`_`/`-`, so `ifpen-allotrope-models`
  matches the `ifpen.allotrope_models` distribution.

## 6. Procedures

### 6.1 Check before publishing

```sh
uv run pytest                                  # unit tests (+ ASM conformance with target/asm)
uv run python verify_deserialization.py        # regenerate; every spec × language must
                                               # round-trip the official ASM examples
uv run python generate.py --prerelease beta.1  # optional: build with pre-release versions
```

### 6.2 Publish a pre-release from a branch

1. Push the branch. Pick the next unused label (`beta.1`, `beta.2`, …): check the versions
   already on the registries, including staged npm versions.
2. Optionally run with `dry_run: true` to check the CI setup.
3. Run the workflow on the branch with `prerelease: <label>`.
4. Approve the staged npm versions (commons first).
5. Wait for Maven Central publication (usually minutes, sometimes longer), then check that
   all packages are installable (§6.4).

### 6.3 Publish a release

1. Make sure `COMMONS_VERSION` and every spec's `info.version` equal the release version and
   are unpublished (§2). All modules are released together at one version.
2. Merge the pull request into `main` (this only builds).
3. On GitHub, *Releases → Draft a new release*: tag **`v<version>`** (e.g. `v2026.09.0`) on
   `main`, title and release notes, *not* marked as pre-release → *Publish release*.
   From a terminal: `gh release create v2026.09.0 --target main --title "2026.9.0" --notes-file notes.md`.
4. Watch the run started by the release; a tag/version mismatch fails in `prepare`, before
   anything is built (delete the release and its tag, fix, and publish again).
5. Approve the staged npm versions (commons first), check installability (§6.4).

A pre-release can also be published this way: tag `v2026.09.0-rc.1`, release marked as
*pre-release*. This keeps a GitHub release (with notes) per published pre-release.

### 6.4 Check that a version is installable

```sh
pip install --pre ifpen-allotrope-models-gc==2026.9.0b1
dotnet add package IFPEN.AllotropeConverters.AllotropeModels.Gc --version 2026.9.0-beta.1
npm view @ifpen/allotrope-models-gc@beta version
curl -sI https://repo1.maven.org/maven2/fr/ifpen/allotropeconverters/allotrope-models-gc/2026.09.0-beta1/allotrope-models-gc-2026.09.0-beta1.pom
```

### 6.5 Add a new instrument spec

Besides AGENTS.md (*Adding a New Instrument Spec*), register its packages before the first run:
PyPI pending publisher `ifpen-allotrope-models-<spec>` with environment `pypi-<spec>`; npm
first publish through `NPM_TOKEN` (scope-wide), then a trusted publisher on the new package.
Maven (namespace) and NuGet (glob `*`) need no change.

### 6.6 Rotate credentials

Maven user token and GPG key: replace the repository secrets. npm: replace `NPM_TOKEN` (or
remove it once every package has a trusted publisher). NuGet and PyPI use no long-lived
secret.

## 7. Re-runs, failures and troubleshooting

### 7.1 Partial runs

Publish jobs are independent (`fail-fast: false`): a failure in one registry does not stop the
others. NuGet (`--skip-duplicate`) and PyPI (`skip-existing`) skip versions that already
exist, so a new run of the same version only completes what is missing. Maven Central rejects
a version that is already *published*, and npm a version that is already staged or published;
deselect those languages (`langs`) when completing a partial release.

### 7.2 Errors seen so far

| Symptom | Cause | Fix |
|---|---|---|
| PyPI `403 Forbidden`, NuGet `401 … X-NuGet-ApiKey`, log shows an empty secret | Secret missing (a configured secret shows as `***`) | Configure trusted publishing (§5.3, §5.4) |
| PyPI `invalid-publisher: valid token, but no corresponding publisher` | No (pending) publisher for that project/environment | Register it (§5.4) |
| PyPI *"A pending trusted publisher matching this configuration has already been registered"* | Same repository/workflow/environment as another project | Use the module's environment (§5.4) |
| PyPI *"Invalid project name"* | Leading/trailing space or quote pasted into the name | Type the name |
| Maven `401` on *Uploading bundle* | Not a Central Portal user token | §5.1 step 2 |
| Maven *"Bundle has content that does NOT have a .pom file"* | Dot in the pre-release qualifier (`-beta.1`) | Maven form `-beta1` (already generated) |
| Maven `429` downloading plugins | Maven Central rate limit | Re-run; dependencies are cached (`cache: maven`) |
| npm `404 Not Found - PUT …/@ifpen%2f…` | Token cannot write to the `@ifpen` scope | Scope-wide token (§5.2) |
| npm `EOTP` (*requires a one-time password*) | `npm publish` with a token on a 2FA account | The workflow stages (`npm stage publish`); approve on npmjs.com |
| `gh`: *forbids access via a fine-grained personal access token … lifetime greater than 366 days* | `ifpen` organization policy | Token with ≤ 366 days lifetime |
| `gh workflow run`: `403 Resource not accessible by personal access token` | Token lacks *Actions: Read and write* | Add the permission (organization approval may be required) |

### 7.3 Inspecting a run

```sh
gh run list --workflow generate.yml --limit 5
gh run view <run-id> --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
gh run view <run-id> --log-failed
```

### 7.4 Deprecate the legacy packages

- NuGet: nuget.org → `IFPEN.AllotropeConverters.AllotropeModels` → *Manage package* →
  *Deprecation* → *Legacy*, alternate package `IFPEN.AllotropeConverters.AllotropeModels.Gc`.
- npm: `npm deprecate @ifpen/allotrope-models "Superseded by @ifpen/allotrope-models-gc"`.
- Maven Central cannot deprecate; optionally publish a relocation pom for
  `allotrope-models` pointing to `allotrope-models-gc`.
