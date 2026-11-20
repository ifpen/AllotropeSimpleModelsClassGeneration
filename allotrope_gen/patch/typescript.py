"""
TypeScript patches (npm packages, generator ``typescript-angular``).

* :func:`keep_models_only` — every TypeScript output (issue #16).  The
  generator emits an Angular HTTP client next to the models, so the package
  required ``@angular/core`` and ``rxjs``.  The runtime files are removed and
  the package is rebuilt as a plain ES module by ``tsc``
  (``docs/adr/0001-npm-packages-keep-typescript-angular-generator.md`` and
  ``docs/adr/0002-npm-packages-are-esm-built-by-tsc.md``).
* :func:`add_peer_dependency` — spec outputs.  The commons package is shared
  by every spec package; as a peer, an application installs a single copy.
* :func:`allow_nan_strings` — properties marked ``x-asm-nan``.  ASM writes an
  unavailable quantity as the JSON string ``"NaN"``; the generated
  ``value: number`` becomes ``value: number | 'NaN'`` so such documents
  type-check.
* :func:`describe_package` — every TypeScript output.  The generated README
  (the npm page) documents an Angular HTTP client, and ``package.json``
  describes an "OpenAPI client" by "OpenAPI-Generator Contributors".

``oneOf`` primitive/object unions need no patch: the generator emits a
TypeScript union type.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from ..config import PACKAGE_AUTHOR, REPOSITORY_URL, TYPESCRIPT_VERSION
from ..readme import PackageReadme
from .common import PatchError, lower_camel, render_template, replace_exact, report, write_text

#: Angular runtime emitted by ``typescript-angular`` next to ``model/``, even
#: for a spec without paths.  Removed by :func:`keep_models_only`.
ANGULAR_RUNTIME = (
    "api",
    "api.base.service.ts",
    "api.module.ts",
    "configuration.ts",
    "encoder.ts",
    "ng-package.json",
    "param.ts",
    "provide-api.ts",
    "query.params.ts",
    "variables.ts",
)

#: Peer dependencies of the Angular runtime, dropped from ``package.json``.
ANGULAR_PEERS = ("@angular/core", "rxjs")

#: ``index.ts`` of a models-only package.
MODELS_INDEX = "export * from './model/models.js';\n"

#: Build script written by the generator, and its replacement.
_NG_BUILD = "ng-packagr -p ng-package.json"
_TSC_BUILD = "tsc -p tsconfig.json"

#: A relative module specifier (``from './x'``) without a ``.js`` extension.
_EXTENSIONLESS_IMPORT = r"(\bfrom '\.{1,2}/[^']*?)(?<!\.js)'"


def keep_models_only(output_dir: Path, dry_run: bool = False) -> None:
    """Turn a ``typescript-angular`` output into a models-only ES module package (idempotent).

    The models (``model/*.ts``) are kept unchanged except for their relative
    imports; everything else the generator emits for Angular goes:

    * the files of :data:`ANGULAR_RUNTIME` are deleted and ``index.ts``
      exports only ``./model/models.js``;
    * relative imports get a ``.js`` extension, required by Node.js ES module
      resolution and by TypeScript's ``node16``/``nodenext`` resolution of
      the published declarations;
    * ``tsconfig.json`` is replaced by ``templates/tsconfig.json`` (ES module
      output and declarations in ``dist/``);
    * ``package.json`` builds with ``tsc``, declares ``"type": "module"`` and
      an ``exports`` map, publishes ``dist/`` from the package root, has
      ``typescript`` (:data:`~allotrope_gen.config.TYPESCRIPT_VERSION`) as its
      only devDependency and no Angular or RxJS peer dependency.

    See ``docs/adr/0001-npm-packages-keep-typescript-angular-generator.md`` and
    ``docs/adr/0002-npm-packages-are-esm-built-by-tsc.md`` (issue #16).

    Args:
        output_dir: Generated TypeScript output directory.
        dry_run:    When ``True``, report but do not modify any file.

    Raises:
        PatchError: If the generated package does not have the expected shape
                    (unknown build script, ``index.ts`` not exporting the
                    models, or Angular/RxJS still referenced after the patch).
    """
    package_json = output_dir / "package.json"
    if not package_json.exists():
        print(f"[WARN] package.json not found, skipping patch: {package_json}", file=sys.stderr)
        return

    removed = [name for name in ANGULAR_RUNTIME if (output_dir / name).exists()]
    if not dry_run:
        for name in removed:
            path = output_dir / name
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    index = output_dir / "index.ts"
    exports = index.read_text(encoding="utf-8")
    if exports != MODELS_INDEX:
        if "export * from './model/models';" not in exports:
            raise PatchError(f"{index}: does not export './model/models'")
        write_text(index, MODELS_INDEX, dry_run)

    for source in sorted((output_dir / "model").glob("*.ts")):
        text = source.read_text(encoding="utf-8")
        patched = re.sub(_EXTENSIONLESS_IMPORT, r"\1.js'", text)
        if patched != text:
            write_text(source, patched, dry_run)

    write_text(output_dir / "tsconfig.json", render_template("tsconfig.json"), dry_run)
    manifest = _models_only_manifest(json.loads(package_json.read_text(encoding="utf-8")), package_json)
    write_text(package_json, json.dumps(manifest, indent=2) + "\n", dry_run)

    if not dry_run:
        _check_models_only(output_dir)
    report("npm patch", f"models-only ES module package ({len(removed)} Angular runtime file(s) removed)")


def _models_only_manifest(manifest: dict, path: Path) -> dict:
    """Return the ``package.json`` of a models-only package built by ``tsc``.

    Raises:
        PatchError: If the build script is neither the generated ng-packagr
                    one nor the ``tsc`` one of a previous run.
    """
    scripts = manifest.get("scripts", {})
    if scripts.get("build") not in (_NG_BUILD, _TSC_BUILD):
        raise PatchError(f"{path}: unexpected build script {scripts.get('build')!r}")
    manifest["scripts"] = {"prepare": "npm run build", "build": _TSC_BUILD}
    manifest["devDependencies"] = {"typescript": TYPESCRIPT_VERSION}
    peers = {k: v for k, v in manifest.get("peerDependencies", {}).items() if k not in ANGULAR_PEERS}
    if peers:
        manifest["peerDependencies"] = peers
    else:
        manifest.pop("peerDependencies", None)
    manifest.update(
        type="module",
        main="./dist/index.js",
        types="./dist/index.d.ts",
        exports={".": {"types": "./dist/index.d.ts", "default": "./dist/index.js"}},
        files=["dist"],
        sideEffects=False,
    )
    return manifest


def _check_models_only(output_dir: Path) -> None:
    """Raise :class:`PatchError` if *output_dir* still contains Angular code.

    Catches generator upgrades that add runtime files missing from
    :data:`ANGULAR_RUNTIME`, and extension-less relative imports that the
    patch did not recognise.
    """
    relative = (p.relative_to(output_dir) for p in output_dir.rglob("*.ts"))
    extra = sorted(
        r.as_posix() for r in relative
        if r.parts[0] not in ("model", "node_modules", "dist") and r != Path("index.ts")
    )
    if extra:
        raise PatchError(f"{output_dir}: unexpected TypeScript file(s) outside model/: {extra}")
    for source in [output_dir / "index.ts", output_dir / "package.json", *(output_dir / "model").glob("*.ts")]:
        text = source.read_text(encoding="utf-8")
        if re.search(r"@angular/|\brxjs\b", text):
            raise PatchError(f"{source}: still references Angular or RxJS")
        if re.search(r"""\bfrom\s*["']\.{1,2}/[^"']*(?<!\.js)["']""", text):
            raise PatchError(f"{source}: relative import without a .js extension")


def add_peer_dependency(package_json: Path, name: str, version: str, dry_run: bool = False) -> None:
    """Declare *name* as a peer dependency of a generated library (idempotent).

    Args:
        package_json: Generated ``package.json``.
        name:         npm package name of the dependency.
        version:      Exact dependency version.
        dry_run:      When ``True``, report but do not write.
    """
    if not package_json.exists():
        print(f"[WARN] package.json not found, skipping patch: {package_json}", file=sys.stderr)
        return
    manifest = json.loads(package_json.read_text(encoding="utf-8"))
    peers = manifest.setdefault("peerDependencies", {})
    if peers.get(name) == version:
        report("package.json patch", f"{name} peer dependency already present, skipping.")
        return
    peers[name] = version
    report("package.json patch", f"added peer dependency {name}@{version}")
    write_text(package_json, json.dumps(manifest, indent=2) + "\n", dry_run)


def allow_nan_strings(output_dir: Path, nan_properties: dict[str, list[str]], dry_run: bool = False) -> None:
    """Type NaN-capable number properties as ``number | 'NaN'`` (idempotent).

    Args:
        output_dir:     Generated TypeScript output directory.
        nan_properties: ``{class name: [JSON property names]}`` of the classes
                        generated in this output.
        dry_run:        When ``True``, report but do not write.

    Raises:
        PatchError: If a property declaration is not ``<name>: number;``.
    """
    patched = 0
    for name, props in nan_properties.items():
        source = output_dir / "model" / f"{lower_camel(name)}.ts"
        if not source.exists():
            continue
        text = source.read_text(encoding="utf-8")
        if "| 'NaN'" in text:
            continue
        for prop in props:
            text = replace_exact(text, rf"^(\s+'?{re.escape(prop)}'?\??: number)(;)", r"\1 | 'NaN'\2", source)
        patched += 1
        write_text(source, text, dry_run)
    report("nan patch", f"typescript: {patched} interface(s) accept the ASM \"NaN\" string")


def describe_package(output_dir: Path, readme: PackageReadme, dry_run: bool = False) -> None:
    """Write ``README.md`` and the ``package.json`` metadata (idempotent).

    The package is published from its root (see :func:`keep_models_only`),
    so npm includes ``README.md`` without further configuration.

    Args:
        output_dir: Generated TypeScript output directory.
        readme:     README, summary and keywords of the package.
        dry_run:    When ``True``, report but do not write.
    """
    write_text(output_dir / "README.md", readme.text, dry_run)
    package_json = output_dir / "package.json"
    if not package_json.exists():
        print(f"[WARN] package.json not found, skipping patch: {package_json}", file=sys.stderr)
        return
    manifest = json.loads(package_json.read_text(encoding="utf-8"))
    manifest.update(
        description=readme.summary,
        author=PACKAGE_AUTHOR,
        keywords=list(readme.keywords),
        homepage=REPOSITORY_URL,
        bugs={"url": f"{REPOSITORY_URL}/issues"},
    )
    write_text(package_json, json.dumps(manifest, indent=2) + "\n", dry_run)
    report("package.json patch", "README and package metadata set")
