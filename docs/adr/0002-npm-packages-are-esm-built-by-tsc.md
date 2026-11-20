# npm packages are ES modules built by `tsc`, with `.js` added to relative imports

The npm packages ship runtime JavaScript as well as types: each model enum is a constant
(`PeakRetentionTime.UnitEnum.S`), and the only known consumer, an Angular 19 application built by
the esbuild `application` builder, uses those constants at runtime. The packages are therefore
built by plain `tsc` (ng-packagr would pull Angular back in, see ADR 0001) as ES modules
(`"type": "module"`, `exports` with `types`/`default`). The generated relative imports have no
extension (`export * from './peak'`). A post-generation patch adds `.js` to them so that Node's
ESM loader and TypeScript's `node16`/`nodenext` resolution can follow them. The patch changes no
model name or shape.

## Considered Options

- **CommonJS from `tsc`**: extension-less `require`s resolve, but the Angular esbuild builder
  warns about CommonJS dependencies and tree-shakes them less well.
- **One ESM file bundled by esbuild, with declarations from `tsc`**: it needs a second build
  tool, and the separate `.d.ts` files would still fail to resolve under `nodenext`.

## Consequences

- Node.js consumers need `import`, or a Node.js version whose `require` can load ES modules
  (≥ 20.19).
- `verify_deserialization.py` loads an enum constant through both `import` and `require`, and
  type-checks a consumer under both `bundler` and `nodenext` resolution.
