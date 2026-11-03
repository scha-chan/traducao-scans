import type { FolderSummary, FolderDetail, TextBlockExport } from '../../src/app/core/api/models';

export const mockFolders: FolderSummary[] = [
  {
    id: 'f-001',
    name: 'capitulo 1',
    status: 'DONE',
    total_pages: 30,
    processed_pages: 30,
    error_pages: 0,
    updated_at: '2026-09-24T14:10:00Z',
  },
  {
    id: 'f-002',
    name: 'capitulo 2',
    status: 'DONE_WITH_ERRORS',
    total_pages: 28,
    processed_pages: 28,
    error_pages: 2,
    updated_at: '2026-09-24T15:02:00Z',
  },
  {
    id: 'f-003',
    name: 'capitulo 3',
    status: 'INCOMPLETE',
    total_pages: 30,
    processed_pages: 12,
    error_pages: 0,
    updated_at: '2026-09-24T15:40:00Z',
  },
];

function makePage(n: number): FolderDetail['pages'][number] {
  const padded = String(n).padStart(3, '0');
  return {
    id: `p-${padded}`,
    page_number: n,
    file_name: `${padded}.jpg`,
    status: 'REVIEW',
    block_count: 2,
    edited: false,
    thumbnail_url: `/api/pages/p-${padded}/thumbnail`,
    image_url: `/api/pages/p-${padded}/image`,
  };
}

export const mockFolderDetail: FolderDetail = {
  id: 'manga-001',
  name: 'Capitulo 1',
  status: 'DONE',
  total_pages: 30,
  processed_pages: 30,
  error_pages: 0,
  updated_at: '2026-09-24T14:10:00Z',
  pages: Array.from({ length: 30 }, (_, i) => makePage(i + 1)),
};

export const mockBlocks: TextBlockExport[] = [
  {
    ordem: 1,
    tipo: '#',
    original: 'テスト',
    localizacao: 'Topo esquerda',
    traducoes: [{ traducao: 'Teste original', observacao: '', relevancia: 3 }],
  },
];
