import { test, expect } from '@playwright/test';
import { mockFolderDetail, mockBlocks } from './fixtures/folders';

test.describe('Detalhe da pasta', () => {
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

  test('FD-03: clicar no card abre modal e atualiza URL com ?pagina=N', async ({
    page,
  }) => {
    await page.goto('/pastas/manga-001');

    const firstCard = page.getByRole('button').filter({ hasText: 'Pág. 1' }).first();
    await expect(firstCard).toBeVisible({ timeout: 5_000 });
    await firstCard.click();

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();
    await expect(page).toHaveURL(/pagina=1/);
  });

  test('FD-04: deep link ?pagina=4 abre modal diretamente na página correta', async ({
    page,
  }) => {
    await page.goto('/pastas/manga-001?pagina=4');

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5_000 });
    await expect(modal.getByText(/Página 4 de 30/)).toBeVisible();
    await expect(page).toHaveURL(/pagina=4/);
  });
});
