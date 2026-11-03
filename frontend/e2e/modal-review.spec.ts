import { test, expect } from '@playwright/test';
import { mockFolderDetail, mockBlocks } from './fixtures/folders';

test.describe('Modal de revisão', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/folders/manga-001', route =>
      route.fulfill({ json: mockFolderDetail })
    );
    await page.route('**/api/pages/*/json', route =>
      route.fulfill({ json: mockBlocks })
    );
    await page.route('**/api/pages/*/image', route =>
      route.fulfill({ status: 200, contentType: 'image/png', body: '' })
    );
    await page.route('**/api/pages/*/thumbnail', route =>
      route.fulfill({ status: 200, contentType: 'image/png', body: '' })
    );
  });

  test('MR-01: botões Anterior/Próxima navegam entre páginas e atualizam URL', async ({
    page,
  }) => {
    await page.goto('/pastas/manga-001?pagina=4');

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5_000 });
    await expect(modal.getByText(/Página 4 de 30/)).toBeVisible();

    await modal.getByRole('button', { name: 'Próxima página' }).click();
    await expect(modal.getByText(/Página 5 de 30/)).toBeVisible();
    await expect(page).toHaveURL(/pagina=5/);

    await modal.getByRole('button', { name: 'Página anterior' }).click();
    await expect(modal.getByText(/Página 4 de 30/)).toBeVisible();
    await expect(page).toHaveURL(/pagina=4/);
  });

  test('MR-02: editar campo de tradução e Salvar dispara PUT', async ({ page }) => {
    await page.route('**/api/pages/p-004/json', route => {
      if (route.request().method() === 'PUT') {
        return route.fulfill({ status: 200, json: [] });
      }
      return route.fulfill({ json: mockBlocks });
    });

    await page.goto('/pastas/manga-001?pagina=4');

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Select the first block in the list to activate the detail panel
    await modal.getByRole('option').first().click();

    // Edit the first translation field
    const translationField = modal.getByLabel('Tradução 1');
    await translationField.fill('Nova tradução editada');

    // Save and intercept the PUT request
    const [request] = await Promise.all([
      page.waitForRequest(req =>
        req.url().includes('/api/pages/p-004/json') && req.method() === 'PUT'
      ),
      modal.getByRole('button', { name: /salvar/i }).click(),
    ]);

    expect(request.method()).toBe('PUT');
  });
});
