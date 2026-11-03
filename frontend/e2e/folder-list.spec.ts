import { test, expect } from '@playwright/test';
import { mockFolders } from './fixtures/folders';

test.describe('Lista de pastas', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/folders', route =>
      route.fulfill({ json: mockFolders })
    );
  });

  test('FL-01: carrega e exibe pastas retornadas pela API', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('table')).toBeVisible();

    for (const folder of mockFolders) {
      await expect(page.getByRole('cell', { name: folder.name })).toBeVisible();
    }

    await expect(
      page.getByRole('button', { name: /baixar txt de capitulo 1/i })
    ).toBeVisible();
  });

  test('FL-05: busca filtra pastas por nome com debounce', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('table')).toBeVisible();

    await page.getByRole('searchbox', { name: 'Buscar pasta' }).fill('capitulo 1');
    await page.waitForTimeout(300);

    await expect(page.getByRole('cell', { name: 'capitulo 1' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'capitulo 2' })).toBeHidden();
  });

  test('FL-12: confirmar exclusão remove pasta da lista sem reload', async ({ page }) => {
    await page.route('**/api/folders/f-001', route =>
      route.fulfill({ status: 204, body: '' })
    );
    await page.goto('/');
    await expect(page.getByRole('table')).toBeVisible();

    await page.getByRole('button', { name: 'Excluir capitulo 1' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();

    await page.getByRole('button', { name: 'Excluir' }).click();

    await expect(page.getByRole('cell', { name: 'capitulo 1' })).toBeHidden();
    await expect(page.getByRole('cell', { name: 'capitulo 2' })).toBeVisible();
  });

  test('FL-14: mobile (< md) exibe cards em vez de tabela', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/');

    await expect(page.getByRole('table')).toBeHidden();

    await expect(page.getByText('capitulo 1')).toBeVisible();
    await expect(page.getByText('capitulo 2')).toBeVisible();
  });
});
