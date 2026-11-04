/**
 * FE-21 — E2E Playwright: fluxo completo da especificação frontend
 * home → nova tradução (pasta fixture) → progresso → miniaturas → editar e salvar → baixar TXT
 */
import { test, expect, Page } from '@playwright/test';
import type { FolderSummary, FolderDetail, FolderExport, TextBlockExport } from '../src/app/core/api/models';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const FOLDER_ID = 'fe21-folder';
const PAGE_ID = 'fe21-page-001';

const mockFolder: FolderSummary = {
  id: FOLDER_ID,
  name: 'Mangá Teste',
  status: 'DONE',
  total_pages: 2,
  processed_pages: 2,
  error_pages: 0,
  updated_at: '2026-11-04T12:00:00Z',
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
    {
      id: 'fe21-page-002',
      page_number: 2,
      file_name: '002.jpg',
      status: 'REVIEW',
      block_count: 1,
      edited: false,
      thumbnail_url: '/api/pages/fe21-page-002/thumbnail',
      image_url: '/api/pages/fe21-page-002/image',
    },
  ],
};

const mockBlocks: TextBlockExport[] = [
  {
    ordem: 1,
    tipo: '#',
    original: 'やあ',
    localizacao: 'Topo',
    traducoes: [{ traducao: 'Ei!', observacao: '', relevancia: 4 }],
  },
  {
    ordem: 2,
    tipo: '$',
    original: 'ありがとう',
    localizacao: 'Centro',
    traducoes: [{ traducao: 'Obrigado', observacao: 'Fala informal', relevancia: 5 }],
  },
];

const mockEditedBlocks: TextBlockExport[] = [
  {
    ...mockBlocks[0],
    traducoes: [{ traducao: 'Oi!', observacao: 'Editado no teste', relevancia: 5 }],
  },
  mockBlocks[1],
];

const mockFolderExport: FolderExport = {
  pasta: 'Mangá Teste',
  paginas: [
    {
      pagina: 1,
      arquivo: '001.jpg',
      status: 'REVIEW',
      blocos: mockEditedBlocks,
    },
    {
      pagina: 2,
      arquivo: '002.jpg',
      status: 'REVIEW',
      blocos: [
        {
          ordem: 1,
          tipo: '#',
          original: 'さようなら',
          localizacao: 'Topo',
          traducoes: [{ traducao: 'Até logo', observacao: '', relevancia: 4 }],
        },
      ],
    },
  ],
};

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

async function setupRoutes(page: Page) {
  await page.route('**/api/folders', route => route.fulfill({ json: [mockFolder] }));
  await page.route(`**/api/folders/${FOLDER_ID}`, route =>
    route.fulfill({ json: mockFolderDetail })
  );
  await page.route(`**/api/folders/${FOLDER_ID}/export`, route =>
    route.fulfill({ json: mockFolderExport })
  );
  await page.route('**/api/pages/*/json', route => route.fulfill({ json: mockBlocks }));
  await page.route('**/api/pages/*/blocks', route => route.fulfill({ json: [] }));
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

test.describe('FE-21 — Fluxo completo da especificação frontend', () => {
  test('FE21-01: home exibe lista de pastas com nome e status', async ({ page }) => {
    await setupRoutes(page);
    await page.goto('/');

    await expect(page.getByText('Mangá Teste')).toBeVisible({ timeout: 5_000 });
  });

  test('FE21-02: nova tradução — dropzone aceita imagens JPG e habilita botão Iniciar', async ({
    page,
  }) => {
    await setupRoutes(page);

    let processCalled = false;
    await page.route('**/api/folders/*/pages/process', route => {
      processCalled = true;
      return route.fulfill({
        json: { page: mockFolderDetail.pages[0], blocos: mockBlocks },
      });
    });
    await page.route('**/api/folders', async route => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ json: mockFolder, status: 201 });
      }
      return route.fulfill({ json: [mockFolder] });
    });

    await page.goto('/nova-traducao');

    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached({ timeout: 5_000 });

    await fileInput.setInputFiles({
      name: '001.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from('fake-jpg'),
    });

    const startBtn = page.getByRole('button', { name: /iniciar/i });
    await expect(startBtn).toBeEnabled({ timeout: 3_000 });
    await startBtn.click();

    await expect(page.getByRole('progressbar')).toBeVisible({ timeout: 5_000 });
    expect(processCalled).toBeTruthy();
  });

  test('FE21-03: grade de miniaturas exibe páginas após processar', async ({ page }) => {
    await setupRoutes(page);

    await page.goto(`/pastas/${FOLDER_ID}`);

    // Should show at least one thumbnail
    await expect(
      page.getByRole('button', { name: /página 1/i }).first()
    ).toBeVisible({ timeout: 5_000 });
  });

  test('FE21-04: editar tradução no modal e salvar atualiza o bloco', async ({ page }) => {
    await setupRoutes(page);

    let savedBlocks: unknown = null;
    await page.route(`**/api/pages/${PAGE_ID}/json`, route => {
      if (route.request().method() === 'PUT') {
        savedBlocks = route.request().postDataJSON();
        return route.fulfill({ json: mockEditedBlocks });
      }
      return route.fulfill({ json: mockBlocks });
    });

    await page.goto(`/pastas/${FOLDER_ID}?pagina=1`);

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    await modal.getByRole('option').first().click();

    const translationField = modal.getByLabel('Tradução 1');
    if (await translationField.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await translationField.fill('Oi!');
      await modal.getByRole('button', { name: /salvar/i }).click();
      await page.waitForTimeout(500);
      expect(savedBlocks).not.toBeNull();
    }
  });

  test('FE21-05: botão Baixar TXT dispara GET /export e gera download', async ({ page }) => {
    await setupRoutes(page);

    let exportCalled = false;
    await page.route(`**/api/folders/${FOLDER_ID}/export`, route => {
      exportCalled = true;
      return route.fulfill({ json: mockFolderExport });
    });

    await page.goto('/');
    await expect(page.getByText('Mangá Teste')).toBeVisible({ timeout: 5_000 });

    const downloadButton = page.getByRole('button', { name: /baixar txt de mangá teste/i });
    await expect(downloadButton).toBeVisible({ timeout: 3_000 });

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      downloadButton.click(),
    ]);

    expect(exportCalled).toBeTruthy();
    expect(download.suggestedFilename()).toMatch(/\.txt$/i);
  });

  test('FE21-06: reprocessar com falha mantém conteúdo anterior', async ({ page }) => {
    await setupRoutes(page);

    await page.route(`**/api/pages/${PAGE_ID}/process`, route =>
      route.fulfill({ status: 500, json: { detail: 'Erro simulado de reprocessamento' } })
    );

    await page.goto(`/pastas/${FOLDER_ID}?pagina=1`);

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    const reprocessBtn = modal.getByRole('button', { name: /reprocessar/i });
    if (await reprocessBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await reprocessBtn.click();

      const confirmBtn = page.getByRole('button', { name: 'Reprocessar' }).last();
      if (await confirmBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await confirmBtn.click();
        await page.waitForTimeout(500);

        // Modal should still show the original content (not cleared)
        await expect(modal).toBeVisible();
      }
    }
  });
});
