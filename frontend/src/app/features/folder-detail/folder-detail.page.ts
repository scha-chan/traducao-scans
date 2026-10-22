import { Component, OnInit, signal, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FoldersApi } from '../../core/api/folders.api';
import { PagesApi } from '../../core/api/pages.api';
import { FolderDetail, PageSummary } from '../../core/api/models';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import { UiSkeletonComponent } from '../../shared/ui/ui-skeleton.component';
import { UiEmptyStateComponent } from '../../shared/ui/ui-empty-state.component';

@Component({
  selector: 'app-folder-detail-page',
  standalone: true,
  imports: [RouterLink, UiButtonComponent, UiSkeletonComponent, UiEmptyStateComponent],
  template: `
    <div class="mx-auto max-w-7xl px-4 py-8">

      <!-- Breadcrumb -->
      <nav class="flex items-center gap-1.5 text-sm text-zinc-500 dark:text-zinc-400 mb-6">
        <a routerLink="/" class="flex items-center gap-1 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors">
          <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6"/></svg>
          Pastas
        </a>
        <span>/</span>
        @if (folder()) {
          <span class="text-zinc-900 dark:text-zinc-100 font-medium">{{ folder()!.name }}</span>
        } @else {
          <span class="inline-block h-4 w-32 animate-pulse rounded bg-zinc-200 dark:bg-zinc-700"></span>
        }
      </nav>

      <!-- Loading state -->
      @if (loading()) {
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          @for (_ of skeletons; track $index) {
            <div class="flex flex-col gap-2">
              <ui-skeleton height="h-48" />
              <ui-skeleton height="h-4" width="w-2/3" />
              <ui-skeleton height="h-3" width="w-1/2" />
            </div>
          }
        </div>
      }

      <!-- Error state -->
      @else if (error()) {
        <ui-empty-state icon="info" title="Não foi possível carregar a pasta" [description]="error() ?? ''">
          <ui-button variant="primary" (click)="retry()">Tentar novamente</ui-button>
        </ui-empty-state>
      }

      <!-- Loaded -->
      @else if (folder()) {
        <!-- Header row: summary + download button -->
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
          <p class="text-sm text-zinc-500 dark:text-zinc-400">
            <span class="tabular-nums font-medium text-zinc-700 dark:text-zinc-300">{{ folder()!.total_pages }} páginas</span>
            @if (errorCount() > 0) {
              <span class="ml-2 text-amber-600 dark:text-amber-400">
                ⚠ {{ errorCount() }} com erro
              </span>
            }
          </p>
          <ui-button variant="secondary" [disabled]="true" title="Disponível após FE-20">
            ⬇ Baixar TXT final
          </ui-button>
        </div>

        <!-- Empty state (no pages) -->
        @if (folder()!.pages.length === 0) {
          <ui-empty-state icon="folder" title="Nenhuma página nesta pasta" description="Adicione imagens para iniciar a tradução.">
            <ui-button variant="primary" routerLink="/nova-traducao">Nova tradução</ui-button>
          </ui-empty-state>
        } @else {
          <!-- Thumbnail grid -->
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            @for (page of folder()!.pages; track page.id) {
              @if (page.status === 'ERROR') {
                <!-- Error card -->
                <div class="flex flex-col rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50">
                  <div class="aspect-[2/3] flex flex-col items-center justify-center gap-2 bg-zinc-100 dark:bg-zinc-900 p-3 text-center">
                    <svg class="size-8 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    <p class="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2">{{ page.error_message ?? 'Erro ao processar' }}</p>
                  </div>
                  <div class="px-2 py-1.5 flex flex-col gap-1">
                    <p class="text-xs font-medium text-zinc-700 dark:text-zinc-300">Pág. {{ page.page_number }}</p>
                    <button type="button" [disabled]="isRetrying(page.id)" (click)="reprocess(page)" class="text-xs text-primary-600 dark:text-primary-400 hover:underline disabled:opacity-50 text-left">
                      {{ isRetrying(page.id) ? 'Processando…' : 'Tentar novamente' }}
                    </button>
                  </div>
                </div>
              } @else {
                <!-- Normal card -->
                <button type="button" (click)="openPage(page)" class="flex flex-col rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700 hover:border-primary-400 dark:hover:border-primary-500 hover:shadow-md transition-all text-left focus-visible:outline-none focus-visible:ring-2 ring-primary-500 ring-offset-2">
                  <div class="aspect-[2/3] overflow-hidden bg-zinc-100 dark:bg-zinc-900">
                    <img [src]="thumbnailUrl(page)" [alt]="'Miniatura da página ' + page.page_number" class="w-full h-full object-cover" loading="lazy" />
                  </div>
                  <div class="px-2 py-1.5 flex flex-col gap-0.5">
                    <div class="flex items-center justify-between">
                      <p class="text-xs font-medium text-zinc-700 dark:text-zinc-300">Pág. {{ page.page_number }}</p>
                      @if (page.edited) {
                        <svg class="size-3 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-label="Editada manualmente"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      }
                    </div>
                    <p class="text-xs text-zinc-400 dark:text-zinc-500 tabular-nums">{{ page.block_count }} {{ page.block_count === 1 ? 'texto' : 'textos' }}</p>
                  </div>
                </button>
              }
            }
          </div>
        }
      }
    </div>
  `,
})
export class FolderDetailPage implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly foldersApi = inject(FoldersApi);
  private readonly pagesApi = inject(PagesApi);

  readonly folder = signal<FolderDetail | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  private readonly retryingIds = signal<string[]>([]);

  readonly skeletons = Array.from({ length: 12 });

  ngOnInit() {
    const folderId = this.route.snapshot.paramMap.get('folderId')!;
    this.loadFolder(folderId);
  }

  loadFolder(folderId: string) {
    this.loading.set(true);
    this.error.set(null);
    this.foldersApi.get(folderId).subscribe({
      next: (f) => {
        this.folder.set(f);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Não foi possível carregar a pasta.');
        this.loading.set(false);
      },
    });
  }

  retry() {
    const folderId = this.route.snapshot.paramMap.get('folderId')!;
    this.loadFolder(folderId);
  }

  reprocess(page: PageSummary) {
    this.retryingIds.update((ids) => [...ids, page.id]);
    this.pagesApi.reprocess(page.id).subscribe({
      next: (result) => {
        const f = this.folder();
        if (f) {
          this.folder.set({ ...f, pages: f.pages.map((p) => (p.id === page.id ? result.page : p)) });
        }
        this.retryingIds.update((ids) => ids.filter((id) => id !== page.id));
      },
      error: () => {
        this.retryingIds.update((ids) => ids.filter((id) => id !== page.id));
      },
    });
  }

  isRetrying(pageId: string): boolean {
    return this.retryingIds().includes(pageId);
  }

  thumbnailUrl(page: PageSummary): string {
    return this.pagesApi.thumbnailUrl(page);
  }

  errorCount(): number {
    return this.folder()?.pages.filter((p) => p.status === 'ERROR').length ?? 0;
  }

  openPage(page: PageSummary) {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { pagina: page.page_number },
      queryParamsHandling: 'merge',
    });
  }
}
