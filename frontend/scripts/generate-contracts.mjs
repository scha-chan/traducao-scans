/**
 * Gera src/app/core/api/contracts.d.ts a partir de contracts/page-export.schema.json.
 * Executado automaticamente via prebuild / pré-typecheck.
 */
import { compile } from 'json-schema-to-typescript';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const schemaPath = resolve(__dirname, '../../contracts/page-export.schema.json');
const outPath = resolve(__dirname, '../src/app/core/api/contracts.d.ts');

const schema = JSON.parse(readFileSync(schemaPath, 'utf-8'));

// Remove minItems/maxItems de arrays — esses são constraints de validação,
// não de tipo, e causariam tipos tuple desnecessários no output TypeScript.
function stripArrayLengthConstraints(obj) {
  if (Array.isArray(obj)) return obj.map(stripArrayLengthConstraints);
  if (typeof obj !== 'object' || obj === null) return obj;
  const result = { ...obj };
  if (result.type === 'array') {
    delete result.minItems;
    delete result.maxItems;
  }
  for (const key of Object.keys(result)) {
    result[key] = stripArrayLengthConstraints(result[key]);
  }
  return result;
}

const ts = await compile(stripArrayLengthConstraints(schema), 'PageExport', {
  bannerComment:
    '/* Gerado automaticamente a partir de contracts/page-export.schema.json.\n' +
    ' * Não edite este arquivo — execute `npm run generate:contracts`. */',
  style: { singleQuote: true, semi: true },
  strictIndexSignatures: true,
  unknownAny: false,
  additionalProperties: false,
});

writeFileSync(outPath, ts, 'utf-8');
console.log('✓ contracts.d.ts gerado com sucesso.');
