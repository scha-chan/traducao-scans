import { Component, OnInit, OnDestroy, signal, inject, computed } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { switchMap, filter, take } from 'rxjs/operators';
import { FoldersApi } from '../../core/api/folders.api';
import { PagesApi } from '../../core/api/pages.api';
import { FolderDetail, PageSummary } from '../../core/api/models';
import { buildFolderTxt, downloadTxt, txtFileName } from '../../export/txt-export';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import { UiSkeletonComponent } from '../../shared/ui/ui-skeleton.component';
import { UiEmptyStateComponent } from '../../shared/ui/ui-empty-state.component';
import { UiDialogComponent } from '../../shared/ui/ui-dialog.component';
import { PageReviewModalComponent } from './page-review-modal.component';
import { ToastService } from '../../shared/ui/ui-toast/toast.service';

@Component({
  selector: 'app-folder-detail-page',
  standalone: true,
  imports: [RouterLink, UiButtonComponent, UiSkeletonComponent, UiEmptyStateComponent, UiDialogComponent, PageReviewModalComponent],
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
              <span class="ml-2 text-amber-600 dark:text-amber-400">⚠ {{ errorCount() }} com erro</span>
            }
          </p>
          <ui-button variant="secondary" [disabled]="downloading()" (click)="downloadTxtFinal()">
            @if (downloading()) { ⏳ Gerando… } @else { ⬇ Baixar TXT final }
          </ui-button>
        </div>

        <!-- Empty state (no pages) -->
        @if (folder()!.pages.length === 0) {
          <ui-empty-state icon="folder" title="Nenhuma página nesta pasta" description="Adicione imagens para iniciar a tradução.">
            <ui-button variant="primary" routerLink="/nova-traducao">Nova tradução</ui-button>
          </ui-empty-state>
        } @else {
          <!-- Pages table -->
          <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden">
            <table class="w-full text-sm">
              <thead class="bg-zinc-50 dark:bg-zinc-900">
                <tr class="text-left text-xs text-zinc-500 dark:text-zinc-400">
                  <th class="px-4 py-3 font-medium w-12">#</th>
                  <th class="px-4 py-3 font-medium">Arquivo</th>
                  <th class="px-4 py-3 font-medium w-36">Status</th>
                  <th class="px-4 py-3 font-medium w-20 text-right">Blocos</th>
                  <th class="px-4 py-3 font-medium text-right w-40">Ações</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-100 dark:divide-zinc-800 bg-white dark:bg-zinc-950">
                @for (page of folder()!.pages; track page.id) {
                  <tr class="hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors group">
                    <td class="px-4 py-3 tabular-nums text-zinc-400">{{ page.page_number }}</td>
                    <td class="px-4 py-3">
                      <div class="flex items-center gap-2">
                        <span class="text-zinc-700 dark:text-zinc-300 font-mono text-xs truncate max-w-xs" [title]="page.file_name">{{ page.file_name }}</span>
                        @if (page.edited) {
                          <svg class="size-3 shrink-0 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-label="Editada manualmente"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        }
                      </div>
                    </td>
                    <td class="px-4 py-3">
                      @if (page.status === 'PENDING') {
                        <span class="text-xs text-zinc-400">Pendente</span>
                      } @else if (page.status === 'PROCESSING') {
                        <span class="inline-flex items-center gap-1 text-xs text-primary-700 dark:text-primary-300">
                          <svg class="size-3 animate-spin shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                          Processando
                        </span>
                      } @else if (page.status === 'ERROR') {
                        <span class="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400" [title]="page.error_message ?? ''">
                          <svg class="size-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                          Erro
                        </span>
                      } @else if (page.status === 'APPROVED') {
                        <span class="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                          <svg class="size-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>
                          Aprovada
                        </span>
                      } @else {
                        <span class="inline-flex items-center gap-1 text-xs text-zinc-600 dark:text-zinc-400">
                          <svg class="size-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                          Em revisão
                        </span>
                      }
                    </td>
                    <td class="px-4 py-3 text-right tabular-nums text-zinc-500 dark:text-zinc-400">
                      @if (page.status !== 'PENDING' && page.status !== 'PROCESSING') {
                        {{ page.block_count }}
                      }
                    </td>
                    <td class="px-4 py-3">
                      <div class="flex items-center justify-end gap-1">
                        @if (page.status === 'PENDING') {
                          @if (page.slice_count === 0) {
                            <a [routerLink]="['/pastas', folderId(), 'anotar']" class="rounded px-2.5 py-1 text-xs font-medium text-indigo-700 dark:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-950 transition-colors">
                              Anotar
                            </a>
                          } @else {
                            <button type="button" [disabled]="isAnalyzing(page.id)" (click)="analyze(page)" class="rounded px-2.5 py-1 text-xs font-medium text-primary-700 dark:text-primary-300 hover:bg-primary-50 dark:hover:bg-primary-950 disabled:opacity-50 transition-colors">
                              Analisar
                            </button>
                            <a [routerLink]="['/pastas', folderId(), 'anotar']" class="rounded px-2.5 py-1 text-xs font-medium text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
                              Fatias
                            </a>
                          }
                        } @else if (page.status === 'ERROR') {
                          <button type="button" [disabled]="isRetrying(page.id)" (click)="reprocess(page)" class="rounded px-2.5 py-1 text-xs font-medium text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-950/30 disabled:opacity-50 transition-colors">
                            {{ isRetrying(page.id) ? 'Processando…' : 'Tentar novamente' }}
                          </button>
                          <a [routerLink]="['/pastas', folderId(), 'anotar']" class="rounded px-2.5 py-1 text-xs font-medium text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
                            Fatias
                          </a>
                        } @else if (page.status !== 'PROCESSING') {
                          <button type="button" (click)="openPage(page)" class="rounded px-2.5 py-1 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
                            Abrir
                          </button>
                          <a [routerLink]="['/pastas', folderId(), 'anotar']" class="rounded px-2.5 py-1 text-xs font-medium text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
                            Fatias
                          </a>
                        }
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      }
    </div>

    <!-- Force-analyze confirmation dialog -->
    <ui-dialog [open]="forceAnalyzeDialog()" (closed)="cancelForceAnalyze()">
      <div class="p-6 flex flex-col gap-4">
        <h2 class="text-base font-semibold text-zinc-900 dark:text-zinc-100">Sobrescrever edições?</h2>
        <p class="text-sm text-zinc-600 dark:text-zinc-400">
          Esta página tem edições manuais ou revisões salvas.
          Reanalisar irá substituir todo o conteúdo pelo resultado da IA.
          Esta ação não pode ser desfeita.
        </p>
        <div class="flex justify-end gap-2 pt-2">
          <ui-button variant="secondary" (click)="cancelForceAnalyze()">Cancelar</ui-button>
          <ui-button variant="destructive" (click)="confirmForceAnalyze()">Reanalisar mesmo assim</ui-button>
        </div>
      </div>
    </ui-dialog>

    <!-- Page review modal -->
    @if (activePage() && folder()) {
      <app-page-review-modal
        [folder]="folder()!"
        [page]="activePage()!"
        (closed)="closeModal()"
        (navigated)="navigateModal($event)"
        (pageReprocessed)="onPageReprocessed($event)"
      />
    }
  `,
})
export class FolderDetailPage implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly foldersApi = inject(FoldersApi);
  private readonly pagesApi = inject(PagesApi);
  private readonly toast = inject(ToastService);

  readonly folder = signal<FolderDetail | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly downloading = signal(false);

  private readonly retryingIds = signal<string[]>([]);
  private readonly analyzingIds = signal<string[]>([]);
  private readonly pollingSubscriptions = new Map<string, Subscription>();
  private readonly activePageNumber = signal<number | null>(null);

  readonly forceAnalyzeDialog = signal(false);
  private pendingForcePageId = signal<string | null>(null);

  folderId = signal('');

  readonly activePage = computed<PageSummary | null>(() => {
    const n = this.activePageNumber();
    if (n == null) return null;
    return this.folder()?.pages.find((p) => p.page_number === n) ?? null;
  });

  readonly skeletons = Array.from({ length: 12 });

  private queryParamSub?: Subscription;

  ngOnInit() {
    const folderId = this.route.snapshot.paramMap.get('folderId')!;
    this.folderId.set(folderId);
    this.loadFolder(folderId);

    this.queryParamSub = this.route.queryParamMap.subscribe((params) => {
      const pagina = params.get('pagina');
      this.activePageNumber.set(pagina ? Number(pagina) : null);
    });
  }

  ngOnDestroy() {
    this.queryParamSub?.unsubscribe();
    this.pollingSubscriptions.forEach((sub) => sub.unsubscribe());
    this.pollingSubscriptions.clear();
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
    this.updatePageStatus(page.id, 'PROCESSING');
    this.pagesApi.reprocess(page.id).subscribe({
      next: async (result) => {
        const pageId = result.page_id ?? page.id;
        try {
          await this.pagesApi.waitForEvent(pageId);
          const folderId = this.route.snapshot.paramMap.get('folderId')!;
          this.loadFolder(folderId);
        } catch {
          this.updatePageStatus(page.id, 'ERROR');
        } finally {
          this.retryingIds.update((ids) => ids.filter((id) => id !== page.id));
        }
      },
      error: () => {
        this.updatePageStatus(page.id, 'ERROR');
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

  closeModal() {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { pagina: null },
      queryParamsHandling: 'merge',
    });
  }

  navigateModal(pageNumber: number) {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { pagina: pageNumber },
      queryParamsHandling: 'merge',
    });
  }

  onPageReprocessed(page: PageSummary) {
    const f = this.folder();
    if (f) {
      this.folder.set({ ...f, pages: f.pages.map((p) => (p.id === page.id ? page : p)) });
    }
  }

  analyze(page: PageSummary) {
    if (this.isAnalyzing(page.id)) return;
    this.pagesApi.analyze(page.id).subscribe({
      next: () => {
        this.analyzingIds.update((ids) => [...ids, page.id]);
        this.updatePageStatus(page.id, 'PROCESSING');
        this.startPolling(page.id);
      },
      error: (err) => {
        if (err?.status === 409) {
          const code = err?.error?.detail?.code;
          if (code === 'HAS_MANUAL_EDITS') {
            this.pendingForcePageId.set(page.id);
            this.forceAnalyzeDialog.set(true);
          } else {
            this.toast.warning('Esta página já está sendo processada. Tente em instantes.');
          }
        } else {
          this.toast.error('Erro ao iniciar a análise. Tente novamente.');
        }
      },
    });
  }

  cancelForceAnalyze() {
    this.forceAnalyzeDialog.set(false);
    this.pendingForcePageId.set(null);
  }

  confirmForceAnalyze() {
    const pageId = this.pendingForcePageId();
    if (!pageId) return;
    this.forceAnalyzeDialog.set(false);
    this.pendingForcePageId.set(null);
    this.pagesApi.analyzeForce(pageId).subscribe({
      next: () => {
        this.analyzingIds.update((ids) => [...ids, pageId]);
        this.updatePageStatus(pageId, 'PROCESSING');
        this.startPolling(pageId);
      },
      error: () => {
        this.toast.error('Erro ao iniciar a análise. Tente novamente.');
      },
    });
  }

  isAnalyzing(pageId: string): boolean {
    return this.analyzingIds().includes(pageId);
  }

  private updatePageStatus(pageId: string, newStatus: PageSummary['status']) {
    const f = this.folder();
    if (!f) return;
    this.folder.set({
      ...f,
      pages: f.pages.map((p) => (p.id === pageId ? { ...p, status: newStatus } : p)),
    });
  }

  private startPolling(pageId: string) {
    this.pollingSubscriptions.get(pageId)?.unsubscribe();

    const delayMs = 2000;
    const sub = interval(delayMs).pipe(
      switchMap(() => this.pagesApi.getRuns(pageId)),
      filter((runs) => runs.length > 0 && (runs[0].status === 'SUCCESS' || runs[0].status === 'ERROR')),
      take(1),
    ).subscribe({
      next: (runs) => {
        this.analyzingIds.update((ids) => ids.filter((id) => id !== pageId));
        this.pollingSubscriptions.delete(pageId);

        if (runs[0].status === 'SUCCESS') {
          this.toast.success('Página analisada com sucesso.');
          // Reload the full folder to get updated page data
          const folderId = this.route.snapshot.paramMap.get('folderId')!;
          this.foldersApi.get(folderId).subscribe({
            next: (f) => this.folder.set(f),
          });
        } else {
          this.toast.error('Erro na análise da página.');
          this.updatePageStatus(pageId, 'ERROR');
        }
      },
      error: () => {
        this.analyzingIds.update((ids) => ids.filter((id) => id !== pageId));
        this.pollingSubscriptions.delete(pageId);
        this.toast.error('Erro ao verificar o status da análise.');
        this.updatePageStatus(pageId, 'ERROR');
      },
    });

    this.pollingSubscriptions.set(pageId, sub);
  }

  downloadTxtFinal() {
    const f = this.folder();
    if (!f || this.downloading()) return;
    this.downloading.set(true);
    this.foldersApi.export(f.id).subscribe({
      next: (data) => {
        const txt = buildFolderTxt(data);
        downloadTxt(txt, txtFileName(f.name));
        this.downloading.set(false);
      },
      error: () => {
        this.downloading.set(false);
      },
    });
  }
}
