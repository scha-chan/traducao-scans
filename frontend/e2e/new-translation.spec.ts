import { test, expect, type Page } from '@playwright/test';

async function selectImages(page: Page, count = 3) {
  const files = Array.from({ length: count }, (_, i) => ({
    name: `00${i + 1}.jpg`,
    mimeType: 'image/jpeg',
    buffer: Buffer.from('JFIF'),
  }));
  await page.locator('input[type="file"]').setInputFiles(files);
  await page.getByLabel('Nome da pasta').fill('test');
}

test.describe('Nova tradução — processamento', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/folders', route =>
      route.fulfill({ status: 201, json: { id: 'new-001', name: 'test' } })
    );
  });

  test('NT-04: contador "N de M" e progressbar', async ({ page }) => {
    await page.route('**/api/folders/new-001/pages/process', async route => {
      await route.fulfill({
        json: { page: { id: 'p', status: 'REVIEW' }, blocos: [] },
      });
    });

    await page.goto('/nova-traducao');
    await selectImages(page, 3);
    await page.getByRole('button', { name: /iniciar tradução/i }).click();

    const bar = page.getByRole('progressbar');
    await expect(bar).toBeVisible();
    await expect(bar).toHaveAttribute('aria-valuemax', '3');

    await expect(page.getByText('3 de 3')).toBeVisible({ timeout: 10_000 });
  });

  test('NT-05: erro em uma imagem não interrompe a fila', async ({ page }) => {
    let calls = 0;
    await page.route('**/api/folders/new-001/pages/process', async route => {
      calls++;
      if (calls === 2) {
        await route.fulfill({ status: 500, json: { detail: 'OCR falhou' } });
      } else {
        await route.fulfill({
          json: { page: { id: 'p', status: 'REVIEW' }, blocos: [] },
        });
      }
    });

    await page.goto('/nova-traducao');
    await selectImages(page, 3);
    await page.getByRole('button', { name: /iniciar/i }).click();

    await expect(page.getByText('3 de 3')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/1 com erro/i)).toBeVisible();
  });

  test('NT-06: guard CanDeactivate exibe confirmação ao navegar durante processamento', async ({
    page,
  }) => {
    await page.route('**/api/folders/new-001/pages/process', () => {
      return new Promise(() => {});
    });

    await page.goto('/nova-traducao');
    await selectImages(page, 2);
    await page.getByRole('button', { name: /iniciar/i }).click();
    await expect(page.getByRole('progressbar')).toBeVisible();

    const dialogPromise = page.waitForEvent('dialog');
    await page.getByRole('link', { name: /manga translator/i }).click();

    const dialog = await dialogPromise;
    expect(dialog.message()).toMatch(/processamento será interrompido/i);
    await dialog.dismiss();

    await expect(page).toHaveURL(/nova-traducao/);
  });

  test('NT-08: conclusão redireciona automaticamente para a pasta', async ({ page }) => {
    await page.route('**/api/folders/new-001/pages/process', async route => {
      await route.fulfill({
        json: { page: { id: 'p', status: 'REVIEW' }, blocos: [] },
      });
    });

    await page.goto('/nova-traducao');
    await selectImages(page, 2);
    await page.getByRole('button', { name: /iniciar/i }).click();

    await expect(page).toHaveURL(/\/pastas\/new-001/, { timeout: 15_000 });
  });
});
