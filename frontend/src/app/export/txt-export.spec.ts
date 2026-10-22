import { describe, it, expect } from 'vitest';
import { buildFolderTxt, buildPageLines, txtFileName } from './txt-export';
import type { PageExport, TextBlockExport } from '../core/api/models';

const BOM = '﻿';

function block(ordem: number, tipo: '#' | '$', original: string, traducoes: { traducao: string; observacao: string; relevancia: 1 | 2 | 3 | 4 | 5 }[]): TextBlockExport {
  return { ordem, tipo, original, localizacao: 'Topo', traducoes };
}

function page(pagina: number, blocos: TextBlockExport[] | null, status: PageExport['status'] = 'REVIEW'): PageExport {
  return { pagina, arquivo: `${String(pagina).padStart(3, '0')}.jpg`, status, blocos };
}

// ─── T1: primeira linha é o nome da pasta ───────────────────────────────────

describe('T1 — primeira linha é o nome da pasta', () => {
  it('começa com o nome da pasta seguido de linha em branco', () => {
    const txt = buildFolderTxt({ pasta: 'Capítulo 1', paginas: [] });
    const lines = txt.replace(BOM, '').split('\n');
    expect(lines[0]).toBe('Capítulo 1');
    expect(lines[1]).toBe('');
  });
});

// ─── T2: páginas em ordem crescente ────────────────────────────────────────

describe('T2 — páginas em ordem crescente', () => {
  it('ordena páginas fora de ordem', () => {
    const txt = buildFolderTxt({
      pasta: 'Cap',
      paginas: [page(3, []), page(1, []), page(2, [])],
    });
    const headers = [...txt.matchAll(/^Página: (\d+)$/gm)].map((m) => Number(m[1]));
    expect(headers).toEqual([1, 2, 3]);
  });
});

// ─── T3: linha do bloco ─────────────────────────────────────────────────────

describe('T3 — linha do bloco', () => {
  it('formata corretamente: tipo+ordem sem espaço, seguido de original', () => {
    const lines = buildPageLines(
      page(1, [block(2, '#', 'ビグタン', [{ traducao: 'Bem...', observacao: '', relevancia: 1 }])]),
    );
    expect(lines).toContain('#2 ビグタン');
  });

  it('usa tipo $ corretamente', () => {
    const lines = buildPageLines(
      page(1, [block(1, '$', '待ど', [{ traducao: '...', observacao: '', relevancia: 1 }])]),
    );
    expect(lines).toContain('$1 待ど');
  });
});

// ─── T4: linha em branco entre cabeçalho do bloco e traduções ───────────────

describe('T4 — linha em branco entre cabeçalho e traduções', () => {
  it('insere linha vazia após a linha do bloco', () => {
    const lines = buildPageLines(
      page(1, [block(1, '#', 'texto', [{ traducao: 'tr', observacao: '', relevancia: 1 }])]),
    );
    const idx = lines.indexOf('#1 texto');
    expect(lines[idx + 1]).toBe('');
  });
});

// ─── T5: formato de cada tradução ────────────────────────────────────────────

describe('T5 — formato de cada tradução', () => {
  it('sem observação: apenas "* traducao"', () => {
    const lines = buildPageLines(
      page(1, [block(1, '#', 'orig', [{ traducao: 'Bem...', observacao: '', relevancia: 1 }])]),
    );
    expect(lines).toContain('* Bem...');
  });

  it('com observação: "* traducao (obs)"', () => {
    const lines = buildPageLines(
      page(1, [block(1, '$', 'orig', [{ traducao: '...', observacao: 'Silêncio.', relevancia: 1 }])]),
    );
    expect(lines).toContain('* ... (Silêncio.)');
  });
});

// ─── T6: traduções ordenadas por relevância ───────────────────────────────

describe('T6 — traduções por relevância crescente', () => {
  it('coloca relevância 1 antes de 2', () => {
    const lines = buildPageLines(
      page(1, [
        block(1, '#', 'orig', [
          { traducao: 'segundo', observacao: '', relevancia: 2 },
          { traducao: 'primeiro', observacao: '', relevancia: 1 },
        ]),
      ]),
    );
    const i1 = lines.indexOf('* primeiro');
    const i2 = lines.indexOf('* segundo');
    expect(i1).toBeLessThan(i2);
  });
});

// ─── T7: linhas em branco entre páginas ──────────────────────────────────

describe('T7 — duas linhas em branco entre páginas', () => {
  it('coloca 2 linhas em branco entre seções de página', () => {
    const txt = buildFolderTxt({
      pasta: 'Cap',
      paginas: [page(1, []), page(2, [])],
    });
    const body = txt.replace(BOM, '').split('\n');
    // Após "Página: 1" e seu conteúdo, deve haver 2 linhas em branco
    const idx2 = body.indexOf('Página: 2');
    // Lines immediately before "Página: 2" should both be blank
    expect(body[idx2 - 1]).toBe('');
    expect(body[idx2 - 2]).toBe('');
  });
});

// ─── T8: normalização de quebras de linha ────────────────────────────────

describe('T8 — quebras de linha viram espaço', () => {
  it('normaliza original com \\n', () => {
    const lines = buildPageLines(
      page(1, [block(1, '#', 'linha1\nlinha2', [{ traducao: 'tr', observacao: '', relevancia: 1 }])]),
    );
    expect(lines).toContain('#1 linha1 linha2');
  });

  it('remove espaços nas pontas', () => {
    const lines = buildPageLines(
      page(1, [block(1, '#', '  texto  ', [{ traducao: '  tr  ', observacao: '', relevancia: 1 }])]),
    );
    expect(lines).toContain('#1 texto');
    expect(lines).toContain('* tr');
  });
});

// ─── T9: BOM e codificação ───────────────────────────────────────────────

describe('T9 — UTF-8 com BOM', () => {
  it('começa com BOM', () => {
    const txt = buildFolderTxt({ pasta: 'Cap', paginas: [] });
    expect(txt.startsWith(BOM)).toBe(true);
  });

  it('termina com \\n', () => {
    const txt = buildFolderTxt({ pasta: 'Cap', paginas: [] });
    expect(txt.endsWith('\n')).toBe(true);
  });
});

// ─── T10: nome do arquivo ────────────────────────────────────────────────

describe('T10 — txtFileName', () => {
  it('adiciona .txt ao nome da pasta', () => {
    expect(txtFileName('capitulo 1')).toBe('capitulo 1.txt');
  });

  it('troca caracteres inválidos do Windows por _', () => {
    expect(txtFileName('cap:1/2')).toBe('cap_1_2.txt');
  });

  it('remove pontos e espaços no fim', () => {
    expect(txtFileName('capitulo 1...')).toBe('capitulo 1.txt');
  });

  it('usa "traducao" quando o nome fica vazio', () => {
    expect(txtFileName('...')).toBe('traducao.txt');
  });
});

// ─── Seção 8.3: casos especiais ─────────────────────────────────────────

describe('seção 8.3 — casos especiais', () => {
  it('página com status ERROR gera mensagem de erro', () => {
    const lines = buildPageLines({ pagina: 1, arquivo: '001.jpg', status: 'ERROR', blocos: [] });
    expect(lines).toContain('(página não traduzida — erro no processamento)');
  });

  it('página com blocos null gera mensagem de erro', () => {
    const lines = buildPageLines({ pagina: 1, arquivo: '001.jpg', status: 'REVIEW', blocos: null });
    expect(lines).toContain('(página não traduzida — erro no processamento)');
  });

  it('página sem texto gera mensagem de vazio', () => {
    const lines = buildPageLines(page(1, []));
    expect(lines).toContain('(nenhum texto detectado)');
  });

  it('não inclui mensagem de erro em página normal', () => {
    const lines = buildPageLines(
      page(1, [block(1, '#', 'orig', [{ traducao: 'tr', observacao: '', relevancia: 1 }])]),
    );
    expect(lines).not.toContain('(página não traduzida — erro no processamento)');
    expect(lines).not.toContain('(nenhum texto detectado)');
  });
});
