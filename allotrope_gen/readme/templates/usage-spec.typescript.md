The package contains TypeScript interfaces and the constants of their enumerated
values (e.g. `SecondsQuantityValue.UnitEnum.S` from the commons package); it has
no client code and no runtime dependency. Type parsed ASM JSON with them:

```typescript
import { readFileSync, writeFileSync } from 'node:fs';
import type { ${root} } from '${package}';

const document: ${root} = JSON.parse(readFileSync('input.json', 'utf-8'));
console.log(document${typescript_documents}?.length);

writeFileSync('output.json', JSON.stringify(document));
```

JSON is not validated at runtime: `JSON.parse` trusts the file. Object literals
are type-checked, e.g. `const doc = { … } satisfies ${root};`.
