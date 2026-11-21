# Plano de Testes E2E — Frontend Angular

> **Stack:** Playwright 1.48 (E2E) · Cypress 13 (Component Testing + E2E) · Angular 18 · TypeScript strict

---

## Sumário

1. [Estratégia](#1-estratégia)
2. [Inventário de cenários](#2-inventário-de-cenários)
3. [Setup](#3-setup)
4. [Playwright — implementações](#4-playwright--implementações)
5. [Cypress — implementações](#5-cypress--implementações)

---

## 1. Estratégia

### Playwright — E2E

- Fluxos completos do usuário (happy path + edge cases)
- Interceptação de rede com `page.route()`
- Guards de rota (`CanDeactivate`)
- Deep links e parâmetros de URL (`?pagina=N`)
- Progresso de processamento em tempo real
- Responsividade mobile (viewport emulation)
- Verificação de requisições HTTP disparadas (`page.waitForRequest`)

### Cypress — Component Testing

- Componentes isolados com `cy.mount()`
- Variantes de badge, estado de loading e empty state
- Lógica de filtro de arquivos da dropzone
- Interações de teclado (Escape, Enter)
- Inputs de arquivo e DataTransfer API
- Testes de função pura: `buildFolderTxt()`

> **Seletores:** prioriza-se roles ARIA (`getByRole`, `findByRole`) sobre classes CSS.
> Os atributos `aria-label` já presentes no código Angular são suficientes para a maioria
> dos locators sem adicionar `data-testid`.

---

## 2. Inventário de cenários

### Lista de pastas — `FolderListPage`

| ID | Cenário | Prioridade | Ferramenta |
|---|---|---|---|
| FL-01 | Carrega e exibe pastas retornadas pela API | CRÍTICO | PW |
| FL-02 | Exibe 5 linhas skeleton durante loading | ALTO | CY |
| FL-03 | Estado vazio: ilustração + CTA "Nova tradução" | ALTO | PW |
| FL-04 | Estado de erro com mensagem e botão "Tentar novamente" | ALTO | PW |
| FL-05 | Busca local filtra pastas por nome (debounce 200 ms) | CRÍTICO | PW |
| FL-06 | Busca é case-insensitive | MÉDIO | CY |
| FL-07 | Busca sem resultado exibe "Nenhuma pasta encontrada" + limpar | ALTO | PW |
| FL-08 | Clicar na linha navega para `/pastas/:id` | CRÍTICO | PW |
| FL-09 | Download TXT: botão desabilitado e spinner durante download | ALTO | PW |
| FL-10 | Dialog de renomear: abre com nome atual, salva e atualiza lista | ALTO | PW |
| FL-11 | Dialog de excluir: exibe nome da pasta na mensagem | ALTO | CY |
| FL-12 | Confirmar exclusão remove pasta da lista sem reload | CRÍTICO | PW |
| FL-13 | Badges de status com classes CSS corretas por variante | MÉDIO | CY |
| FL-14 | Mobile (< md): exibe cards em vez de tabela | MÉDIO | PW |

### Nova tradução — `NewTranslationPage`

| ID | Cenário | Prioridade | Ferramenta |
|---|---|---|---|
| NT-01 | Dropzone filtra: aceita `.jpg`/`.png`/`.webp`, rejeita outros | CRÍTICO | CY |
| NT-02 | Arquivos ignorados listados com motivo correto (oculto, subpasta, >20 MB) | ALTO | CY |
| NT-03 | Botão "Iniciar" desabilitado sem imagens válidas | ALTO | PW |
| NT-04 | Barra de progresso e contador "N de M" corretos a cada imagem | CRÍTICO | PW |
| NT-05 | Erro em uma imagem (500) não interrompe a fila | CRÍTICO | PW |
| NT-06 | Guard `CanDeactivate`: exibe diálogo ao navegar durante processamento | CRÍTICO | PW |
| NT-07 | Cancelar processamento: confirmação + navega para `/pastas/:id` | ALTO | PW |
| NT-08 | Conclusão: toast de sucesso + redirecionamento automático | CRÍTICO | PW |

### Detalhe da pasta — `FolderDetailPage`

| ID | Cenário | Prioridade | Ferramenta |
|---|---|---|---|
| FD-01 | Grade renderiza N miniaturas na ordem de página | ALTO | PW |
| FD-02 | Card com status ERROR exibe placeholder + botão "Tentar novamente" | ALTO | CY |
| FD-03 | Clicar no card abre modal e atualiza URL com `?pagina=N` | CRÍTICO | PW |
| FD-04 | Deep link `?pagina=4`: abre modal diretamente na página correta | CRÍTICO | PW |
| FD-05 | Header exibe "⚠ N com erro" quando há páginas com falha | MÉDIO | CY |

### Modal de revisão — `PageReviewModal`

| ID | Cenário | Prioridade | Ferramenta |
|---|---|---|---|
| MR-01 | Botões Anterior/Próxima navegam entre páginas e atualizam URL | ALTO | PW |
| MR-02 | Editar campo de tradução e Salvar: dispara PATCH + fecha modal | CRÍTICO | PW |
| MR-03 | Cancelar não chama a API e descarta alterações | ALTO | PW |
| MR-04 | Tecla Escape fecha o modal | MÉDIO | CY |
| MR-05 | Modal com alterações não salvas bloqueia "Baixar TXT final" | ALTO | PW |

---

## 3. Setup

### playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:4200',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'ng serve',
    url: 'http://localhost:4200',
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile',   use: { ...devices['Pixel 7'] } },
  ],
});
```

### cypress.config.ts

```typescript
import { defineConfig } from 'cypress';

export default defineConfig({
  component: {
    devServer: { framework: 'angular', bundler: 'webpack' },
    specPattern: 'src/**/*.cy.ts',
  },
  e2e: {
    baseUrl: 'http://localhost:4200',
    specPattern: 'cypress/e2e/**/*.cy.ts',
  },
});
```

### e2e/fixtures/folders.ts

```typescript
import type { FolderSummary } from '../../frontend/src/app/core/api/models';

export const mockFolders: FolderSummary[] = [
  { id: 'f-001', name: 'capitulo 1', status: 'DONE',
    total_pages: 30, processed_pages: 30, error_pages: 0,
    updated_at: '2026-09-24T14:10:00Z' },
  { id: 'f-002', name: 'capitulo 2', status: 'DONE_WITH_ERRORS',
    total_pages: 28, processed_pages: 28, error_pages: 2,
    updated_at: '2026-09-24T15:02:00Z' },
  { id: 'f-003', name: 'capitulo 3', status: 'INCOMPLETE',
    total_pages: 30, processed_pages: 12, error_pages: 0,
    updated_at: '2026-09-24T15:40:00Z' },
];
```

---

## 4. Playwright — implementações

### FL-01 · FL-05 · FL-12 — Lista de pastas

```typescript
import { test, expect } from '@playwright/test';
import { mockFolders } from '../fixtures/folders';

test.describe('Lista de pastas', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/folders', route =>
      route.fulfill({ json: mockFolders })
    );
  });

  test('FL-01: carrega e exibe pastas', async ({ page }) => {
    await page.goto('/');

    // Skeleton desaparece, tabela aparece
    await expect(page.getByRole('table')).toBeVisible();

    // Cada pasta tem uma linha com seu nome
    for (const folder of mockFolders) {
      await expect(page.getByRole('cell', { name: folder.name })).toBeVisible();
    }

    // Ações disponíveis para a primeira pasta
    await expect(
      page.getByRole('button', { name: /baixar txt de capitulo 1/i })
    ).toBeVisible();
  });

  test('FL-05: busca filtra por nome com debounce', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('table')).toBeVisible();

    await page.getByRole('searchbox', { name: 'Buscar pasta' }).fill('capitulo 1');
    await page.waitForTimeout(300); // debounce de 200 ms

    await expect(page.getByRole('cell', { name: 'capitulo 1' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'capitulo 2' })).toBeHidden();
  });

  test('FL-12: confirmar exclusão remove pasta da lista', async ({ page }) => {
    await page.route('**/api/folders/f-001', route =>
      route.fulfill({ status: 204, body: '' })
    );
    await page.goto('/');

    await page.getByRole('button', { name: 'Excluir capitulo 1' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();

    await page.getByRole('button', { name: 'Excluir' }).click();

    // Sem reload — Angular remove do signal localmente
    await expect(page.getByRole('cell', { name: 'capitulo 1' })).toBeHidden();
    await expect(page.getByRole('cell', { name: 'capitulo 2' })).toBeVisible();
  });
});
```

### NT-04 · NT-05 · NT-06 — Processamento, erros e guard

```typescript
import { test, expect, type Page } from '@playwright/test';

/** Seleciona N imagens via input[type=file] hidden */
async function selectImages(page: Page, count = 3) {
  const files = Array.from({ length: count }, (_, i) => ({
    name: `00${i + 1}.jpg`,
    mimeType: 'image/jpeg',
    buffer: Buffer.from('JFIF'),
  }));
  await page.locator('input[type="file"]').setInputFiles(files);
}

test.describe('Nova tradução — processamento', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/folders', route =>
      route.fulfill({ status: 201, json: { id: 'new-001', name: 'teste' } })
    );
  });

  test('NT-04: contador "N de M" e progressbar', async ({ page }) => {
    await page.route('**/api/folders/new-001/pages/process', async route => {
      await route.fulfill({ json: { page: { id: 'p', status: 'REVIEW' }, blocos: [] } });
    });

    await page.goto('/nova-traducao');
    await selectImages(page, 3);
    await page.getByRole('button', { name: /iniciar tradução/i }).click();

    // Progressbar com atributos de acessibilidade
    const bar = page.getByRole('progressbar');
    await expect(bar).toBeVisible();
    await expect(bar).toHaveAttribute('aria-valuemax', '3');

    // Aguarda conclusão
    await expect(page.getByText('3 de 3')).toBeVisible({ timeout: 10_000 });
  });

  test('NT-05: erro em uma imagem não interrompe a fila', async ({ page }) => {
    let calls = 0;
    await page.route('**/api/folders/new-001/pages/process', async route => {
      calls++;
      if (calls === 2) {
        await route.fulfill({ status: 500, json: { detail: 'OCR falhou' } });
      } else {
        await route.fulfill({ json: { page: { id: 'p', status: 'REVIEW' }, blocos: [] } });
      }
    });

    await page.goto('/nova-traducao');
    await selectImages(page, 3);
    await page.getByRole('button', { name: /iniciar/i }).click();

    // Todas as 3 imagens processadas — fila não parou
    await expect(page.getByText('3 de 3')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/1 com erro/i)).toBeVisible();
  });

  test('NT-06: guard CanDeactivate exibe confirmação', async ({ page }) => {
    // Endpoint nunca responde → mantém estado "processando"
    await page.route('**/api/folders/new-001/pages/process', () => {
      return new Promise(() => {}); // pending forever
    });

    await page.goto('/nova-traducao');
    await selectImages(page, 2);
    await page.getByRole('button', { name: /iniciar/i }).click();
    await expect(page.getByRole('progressbar')).toBeVisible();

    // Tenta navegar para fora
    await page.getByRole('link', { name: /manga translator/i }).click();

    // Guard intercepta a saída
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(
      page.getByText(/processamento será interrompido/i)
    ).toBeVisible();
    // Permanece na rota /nova-traducao
    await expect(page).toHaveURL(/nova-traducao/);
  });
});
```

### FD-04 · MR-02 — Deep link e edição no modal

```typescript
test('FD-04: deep link abre modal na página correta', async ({ page }) => {
  await page.route('**/api/folders/manga-001', route =>
    route.fulfill({ json: mockFolderDetail }) // 30 páginas
  );

  await page.goto('/pastas/manga-001?pagina=4');

  const modal = page.getByRole('dialog');
  await expect(modal).toBeVisible();
  await expect(modal.getByText(/página 4 de 30/i)).toBeVisible();
  await expect(page).toHaveURL(/pagina=4/);
});

test('MR-02: editar tradução e salvar dispara PATCH', async ({ page }) => {
  await page.route('**/api/folders/manga-001', route =>
    route.fulfill({ json: mockFolderDetail })
  );
  await page.route('**/api/pages/p-004/blocks', route =>
    route.fulfill({ status: 200, json: { ok: true } })
  );

  await page.goto('/pastas/manga-001?pagina=4');

  const cell = page.getByRole('dialog')
    .getByRole('row').first()
    .getByRole('textbox');
  await cell.fill('Nova tradução editada');

  // Garante que o PATCH é disparado ao salvar
  const [request] = await Promise.all([
    page.waitForRequest('**/api/pages/p-004/blocks'),
    page.getByRole('button', { name: /salvar/i }).click(),
  ]);
  expect(request.method()).toBe('PATCH');

  // Modal fecha após salvar
  await expect(page.getByRole('dialog')).toBeHidden();
});
```

### FL-14 — Responsividade mobile

```typescript
test('FL-14: mobile exibe layout de cards', async ({ page }) => {
  await page.route('**/api/folders', r => r.fulfill({ json: mockFolders }));

  // Emula viewport mobile (< md = 768px no Tailwind)
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  // Tabela oculta (classe hidden md:block)
  await expect(page.getByRole('table')).toBeHidden();

  // Cards visíveis com nome das pastas
  await expect(page.getByText('capitulo 1')).toBeVisible();
  await expect(page.getByText('capitulo 2')).toBeVisible();
});
```

---

## 5. Cypress — implementações

### FL-13 — UiBadgeComponent (component test parametrizado)

```typescript
import { mount } from 'cypress/angular';
import { UiBadgeComponent } from './ui-badge.component';
import type { FolderStatus } from '../../core/api/models';

const cases: Array<{ status: FolderStatus; label: string; cls: string }> = [
  { status: 'DONE',             label: 'Concluída',   cls: 'bg-emerald-100' },
  { status: 'DONE_WITH_ERRORS', label: 'Com erros',   cls: 'bg-amber-100'   },
  { status: 'INCOMPLETE',       label: 'Incompleta',  cls: 'bg-zinc-100'    },
  { status: 'PROCESSING',       label: 'Processando', cls: 'bg-primary-50'  },
];

describe('UiBadgeComponent', () => {
  cases.forEach(({ status, label, cls }) => {
    it(`status ${status}: label e classe corretos`, () => {
      mount(UiBadgeComponent, { componentProperties: { status } });

      cy.get('span')
        .should('contain.text', label)
        .and('have.class', cls);
    });
  });
});
```

### NT-01 — Filtro de arquivos da dropzone

```typescript
import { mount } from 'cypress/angular';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NewTranslationPage } from './new-translation.page';

describe('NT-01: filtro de arquivos da dropzone', () => {
  beforeEach(() => {
    mount(NewTranslationPage, {
      imports: [HttpClientTestingModule, RouterTestingModule],
    });
  });

  it('aceita .jpg, .png e .webp', () => {
    const dt = new DataTransfer();
    ['001.jpg', '002.png', 'cover.webp'].forEach(name =>
      dt.items.add(new File(['x'], name, { type: 'image/jpeg' }))
    );

    cy.get('[data-testid="dropzone"]').trigger('drop', { dataTransfer: dt });

    cy.contains('3 imagens encontradas').should('be.visible');
    cy.get('[data-testid="ignored-count"]').should('not.exist');
  });

  it('rejeita .txt e .zip com motivo "não é imagem"', () => {
    const dt = new DataTransfer();
    ['notes.txt', 'archive.zip'].forEach(name =>
      dt.items.add(new File(['x'], name, { type: 'text/plain' }))
    );

    cy.get('[data-testid="dropzone"]').trigger('drop', { dataTransfer: dt });

    cy.contains('2 arquivos ignorados').should('be.visible');
    cy.contains('ver').click();
    cy.contains('não é imagem').should('be.visible');
  });
});
```

### MR-04 — Escape fecha o modal

```typescript
import { mount } from 'cypress/angular';
import { PageReviewModalComponent } from './page-review-modal.component';
import { mockPage } from '../../fixtures/pages';

it('MR-04: Escape fecha o modal', () => {
  const onClosed = cy.spy().as('onClosed');

  mount(PageReviewModalComponent, {
    componentProperties: {
      open: true,
      page: mockPage,
      totalPages: 30,
    },
    on: { closed: onClosed },
  });

  cy.get('[role="dialog"]').should('be.visible');
  cy.get('body').type('{esc}');
  cy.get('@onClosed').should('have.been.calledOnce');
});
```

### FL-11 — Dialog de exclusão exibe nome da pasta

```typescript
import { mount } from 'cypress/angular';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { FolderListPage } from './folder-list.page';

it('FL-11: dialog de excluir exibe o nome da pasta', () => {
  cy.intercept('GET', '/api/folders', { fixture: 'folders.json' });

  mount(FolderListPage, {
    imports: [HttpClientTestingModule, RouterTestingModule],
  });

  cy.get('table').should('be.visible');
  cy.get('[aria-label="Excluir capitulo 1"]').click();

  cy.get('[role="dialog"]')
    .should('be.visible')
    .and('contain.text', 'capitulo 1');
});
```

### EXPORT-01 — buildFolderTxt (função pura)

```typescript
import { buildFolderTxt } from '../../export/txt-export';
import type { FolderExport } from '../../core/api/models';

describe('buildFolderTxt', () => {
  it('inclui texto de páginas aprovadas', () => {
    const data: FolderExport = {
      pasta: 'capitulo 1',
      paginas: [{
        pagina: 1, arquivo: '001.jpg', status: 'APPROVED',
        blocos: [{ id: 'b1', translations: [{ text: 'Olá mundo', selected: true }] }],
      }],
    };
    const txt = buildFolderTxt(data);
    expect(txt).to.include('Olá mundo');
  });

  it('sinaliza páginas com status ERROR', () => {
    const data: FolderExport = {
      pasta: 'capitulo 1',
      paginas: [{
        pagina: 2, arquivo: '002.jpg', status: 'ERROR', blocos: null,
      }],
    };
    const txt = buildFolderTxt(data);
    // Especificação seção 8.3: páginas sem resultado aparecem com aviso
    expect(txt).to.include('[SEM TRADUÇÃO]');
    expect(txt).to.include('002.jpg');
  });
});
```
