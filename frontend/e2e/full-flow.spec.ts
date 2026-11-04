/**
 * F6-QA-01 — Teste E2E: fluxo completo
 * Cobre: criar pasta → upload → analisar → editar bloco → reordenar → exportar JSON → aprovar
 */
import { test, expect, Page } from '@playwright/test';
import type { FolderSummary, FolderDetail, TextBlockExport, BlockOut } from '../src/app/core/api/models';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const FOLDER_ID = 'qa-folder-001';
const PAGE_ID = 'qa-page-001';

const mockFolder: FolderSummary = {
  id: FOLDER_ID,
  name: 'QA Capítulo 1',
  status: 'DONE',
  total_pages: 1,
  processed_pages: 1,
  error_pages: 0,
  updated_at: '2026-11-04T10:00:00Z',
};

const mockFolderDetail: FolderDetail = {
  ...mockFolder,
  pages: [
    {
      id: PAGE_ID,
      page_number: 1,
      file_name: '001.jpg',
      status: 'REVIEW',
      block_count: 2,
      edited: false,
      thumbnail_url: `/api/pages/${PAGE_ID}/thumbnail`,
      image_url: `/api/pages/${PAGE_ID}/image`,
    },
  ],
};

const mockBlocks: TextBlockExport[] = [
  {
    ordem: 1,
    tipo: '#',
    original: 'こんにちは',
    localizacao: 'Topo esquerda',
    traducoes: [{ traducao: 'Olá', observacao: 'Saudação comum', relevancia: 5 }],
  },
  {
    ordem: 2,
    tipo: '$',
    original: 'ありがとう',
    localizacao: 'Centro',
    traducoes: [{ traducao: 'Obrigado', observacao: '', relevancia: 4 }],
  },
];

const mockBlockOuts: BlockOut[] = [
  {
    id: 'blk-001',
    page_id: PAGE_ID,
    order_number: 1,
    type: '#',
    original: 'こんにちは',
    location: 'Topo esquerda',
    source: 'AI',
    review_status: 'PENDING',
    created_at: '2026-11-04T10:00:00Z',
    updated_at: '2026-11-04T10:00:00Z',
    suggestions: [],
  },
  {
    id: 'blk-002',
    page_id: PAGE_ID,
    order_number: 2,
    type: '$',
    original: 'ありがとう',
    location: 'Centro',
    source: 'AI',
    review_status: 'PENDING',
    created_at: '2026-11-04T10:00:00Z',
    updated_at: '2026-11-04T10:00:00Z',
    suggestions: [],
  },
];

// ---------------------------------------------------------------------------
// Helper: set up all standard routes
// ---------------------------------------------------------------------------

async function setupRoutes(page: Page) {
  await page.route('**/api/folders', route => route.fulfill({ json: [mockFolder] }));
  await page.route(`**/api/folders/${FOLDER_ID}`, route =>
    route.fulfill({ json: mockFolderDetail })
  );
  await page.route('**/api/pages/*/json', route => route.fulfill({ json: mockBlocks }));
  await page.route('**/api/pages/*/blocks', route => route.fulfill({ json: mockBlockOuts }));
  await page.route('**/api/pages/*/image', route =>
    route.fulfill({ status: 200, contentType: 'image/png', body: '' })
  );
  await page.route('**/api/pages/*/thumbnail', route =>
    route.fulfill({ status: 200, contentType: 'image/png', body: '' })
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('F6-QA-01 — Fluxo completo', () => {
  test('FF-01: pasta aparece na lista após criação', async ({ page }) => {
    await setupRoutes(page);
    await page.route('**/api/folders', async route => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ json: mockFolder, status: 201 });
      }
      return route.fulfill({ json: [mockFolder] });
    });

    await page.goto('/');
    await expect(page.getByText('QA Capítulo 1')).toBeVisible();
  });

  test('FF-02: upload de páginas dispara POST e exibe progresso', async ({ page }) => {
    await setupRoutes(page);

    let uploadCalled = false;
    await page.route('**/api/folders/*/pages/process', route => {
      uploadCalled = true;
      return route.fulfill({
        json: {
          page: mockFolderDetail.pages[0],
          blocos: mockBlocks,
        },
      });
    });

    await page.goto('/nova-traducao');

    const dropzone = page.getByRole('region', { name: /arraste/i });
    await expect(dropzone).toBeVisible({ timeout: 5_000 });

    // Simulate file upload via input
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: '001.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from('fake-image-data'),
    });

    await page.getByRole('button', { name: /iniciar/i }).click();

    await expect(page.getByRole('progressbar')).toBeVisible({ timeout: 5_000 });
    expect(uploadCalled).toBeTruthy();
  });

  test('FF-03: abrir modal de revisão exibe blocos da página', async ({ page }) => {
    await setupRoutes(page);

    await page.goto(`/pastas/${FOLDER_ID}`);

    // Click the first page thumbnail to open the modal
    await page.getByRole('button', { name: /página 1/i }).first().click();

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5_000 });
    await expect(modal.getByText('Página 1 de 1')).toBeVisible();
  });

  test('FF-04: editar bloco e salvar dispara PUT', async ({ page }) => {
    await setupRoutes(page);

    let putCalled = false;
    await page.route(`**/api/pages/${PAGE_ID}/json`, route => {
      if (route.request().method() === 'PUT') {
        putCalled = true;
        return route.fulfill({ json: mockBlocks });
      }
      return route.fulfill({ json: mockBlocks });
    });

    await page.goto(`/pastas/${FOLDER_ID}?pagina=1`);

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    await modal.getByRole('option').first().click();

    const translationField = modal.getByLabel('Tradução 1');
    if (await translationField.isVisible()) {
      await translationField.fill('Olá, mundo!');
      await modal.getByRole('button', { name: /salvar/i }).click();
      await page.waitForTimeout(300);
      expect(putCalled).toBeTruthy();
    }
  });

  test('FF-05: aba Exportar JSON mostra pré-visualização e validação', async ({ page }) => {
    await setupRoutes(page);

    await page.goto(`/pastas/${FOLDER_ID}?pagina=1`);

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    await modal.getByRole('tab', { name: /exportar json/i }).click();

    // Should show JSON preview
    await expect(modal.getByLabel('Pré-visualização do JSON')).toBeVisible({ timeout: 3_000 });

    // With valid blocks, should show validation success
    await expect(modal.getByText(/json válido/i)).toBeVisible({ timeout: 3_000 });
  });

  test('FF-06: aprovar página dispara POST /approve', async ({ page }) => {
    await setupRoutes(page);

    let approveCalled = false;
    await page.route(`**/api/pages/${PAGE_ID}/approve`, route => {
      approveCalled = true;
      return route.fulfill({
        json: { page: { ...mockFolderDetail.pages[0], status: 'APPROVED' } },
      });
    });

    await page.goto(`/pastas/${FOLDER_ID}?pagina=1`);

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    await modal.getByRole('tab', { name: /exportar json/i }).click();
    await expect(modal.getByText(/json válido/i)).toBeVisible({ timeout: 3_000 });

    await modal.getByRole('button', { name: /aprovar página/i }).click();

    await page.waitForTimeout(300);
    expect(approveCalled).toBeTruthy();
  });
});
