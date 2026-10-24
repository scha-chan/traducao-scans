import { FolderExport, PageExport } from '../core/api/models';

const BOM = '﻿';
const oneLine = (s: string) => s.replace(/\s*\r?\n\s*/g, ' ').trim();

export function buildFolderTxt(folder: FolderExport): string {
  const out: string[] = [oneLine(folder.pasta), ''];
  const pages = [...folder.paginas].sort((a, b) => a.pagina - b.pagina);

  pages.forEach((page, i) => {
    if (i > 0) out.push(''); // T7: 2ª linha em branco entre páginas
    out.push(...buildPageLines(page));
  });

  return BOM + out.join('\n') + '\n';
}

export function buildPageLines(page: PageExport): string[] {
  const out = [`Página: ${page.pagina}`];

  if (page.status === 'ERROR' || page.blocos === null) {
    return [...out, '(página não traduzida — erro no processamento)', ''];
  }
  if (page.blocos.length === 0) {
    return [...out, '(nenhum texto detectado)', ''];
  }

  for (const b of [...page.blocos].sort((x, y) => x.ordem - y.ordem)) {
    out.push(`${b.tipo}${b.ordem} ${oneLine(b.original)}`, '');
    for (const t of [...b.traducoes].sort((x, y) => x.relevancia - y.relevancia)) {
      const obs = oneLine(t.observacao);
      out.push(`* ${oneLine(t.traducao)}${obs ? ` (${obs})` : ''}`);
    }
    out.push('');
  }
  return out;
}

export function txtFileName(folderName: string): string {
  const safe = folderName.replace(/[\\/:*?"<>|]/g, '_').replace(/[. ]+$/, '').trim();
  return `${safe || 'traducao'}.txt`;
}

export function downloadTxt(content: string, fileName: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
  const a = Object.assign(document.createElement('a'), { href: url, download: fileName });
  a.click();
  URL.revokeObjectURL(url);
}
