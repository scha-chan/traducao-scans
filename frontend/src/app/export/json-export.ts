import { TextBlockExport, JsonValidationError } from '../core/api/models';

export function validatePageJson(blocks: TextBlockExport[]): JsonValidationError[] {
  const errors: JsonValidationError[] = [];

  if (!Array.isArray(blocks)) {
    errors.push({ blockIndex: -1, field: 'root', message: 'A raiz deve ser um array.' });
    return errors;
  }

  const ordens = blocks.map(b => b.ordem);
  const ordensSorted = [...ordens].sort((a, b) => a - b);
  const expectedOrdens = Array.from({ length: blocks.length }, (_, i) => i + 1);

  if (JSON.stringify(ordensSorted) !== JSON.stringify(expectedOrdens)) {
    errors.push({
      blockIndex: -1,
      field: 'ordem',
      message: `A ordem deve ser sequencial de 1 a ${blocks.length} sem lacunas.`,
    });
  }

  const seenOrdens = new Set<number>();
  blocks.forEach((block, i) => {
    if (typeof block.ordem !== 'number' || !Number.isInteger(block.ordem) || block.ordem < 1) {
      errors.push({ blockIndex: i, field: 'ordem', message: 'ordem deve ser um inteiro positivo.' });
    } else if (seenOrdens.has(block.ordem)) {
      errors.push({ blockIndex: i, field: 'ordem', message: `ordem ${block.ordem} está duplicado.` });
    }
    seenOrdens.add(block.ordem);

    if (block.tipo !== '#' && block.tipo !== '$') {
      errors.push({ blockIndex: i, field: 'tipo', message: `tipo deve ser "#" ou "$", encontrado: "${block.tipo}".` });
    }

    if (block.original === null || block.original === undefined) {
      errors.push({ blockIndex: i, field: 'original', message: 'original não pode ser nulo.' });
    }

    if (block.localizacao === null || block.localizacao === undefined) {
      errors.push({ blockIndex: i, field: 'localizacao', message: 'localizacao não pode ser nula.' });
    }

    if (!Array.isArray(block.traducoes)) {
      errors.push({ blockIndex: i, field: 'traducoes', message: 'traducoes deve ser um array.' });
    } else {
      if (block.traducoes.length < 1 || block.traducoes.length > 5) {
        errors.push({
          blockIndex: i,
          field: 'traducoes',
          message: `traducoes deve ter entre 1 e 5 itens (encontrado: ${block.traducoes.length}).`,
        });
      }

      block.traducoes.forEach((t, j) => {
        if (!t.traducao) {
          errors.push({ blockIndex: i, field: `traducoes[${j}].traducao`, message: 'traducao não pode ser vazia.' });
        }
        if (typeof t.relevancia !== 'number' || t.relevancia < 1 || t.relevancia > 5) {
          errors.push({ blockIndex: i, field: `traducoes[${j}].relevancia`, message: 'relevancia deve ser um inteiro de 1 a 5.' });
        }
      });
    }
  });

  return errors;
}

export function formatJson(blocks: TextBlockExport[]): string {
  return JSON.stringify(blocks, null, 2);
}

export function downloadJson(content: string, fileName: string): void {
  const blob = new Blob([content], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}
