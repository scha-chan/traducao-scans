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
          <!-- Thumbnail grid -->
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            @for (page of folder()!.pages; track page.id) {
              @if (page.status === 'PENDING') {
                <!-- Pending card: not analyzed yet -->
                <div class="flex flex-col rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50">
                  <div class="aspect-[2/3] flex flex-col items-center justify-center gap-3 bg-zinc-100 dark:bg-zinc-900 p-3 text-center">
                    <svg class="size-8 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
                    <p class="text-xs text-zinc-500 dark:text-zinc-400">Não analisada</p>
                  </div>
                  <div class="px-2 py-1.5 flex flex-col gap-1">
                    <p class="text-xs font-medium text-zinc-700 dark:text-zinc-300">Pág. {{ page.page_number }}</p>
                    <button type="button" [disabled]="isAnalyzing(page.id)" (click)="analyze(page)" class="text-xs text-primary-600 dark:text-primary-400 hover:underline disabled:opacity-50 text-left">
                      Analisar página
                    </button>
                  </div>
                </div>
              } @else if (page.status === 'PROCESSING') {
                <!-- Processing card: analysis in progress -->
                <div class="flex flex-col rounded-lg overflow-hidden border border-primary-200 dark:border-primary-800 bg-primary-50/50 dark:bg-primary-950/30">
                  <div class="aspect-[2/3] flex flex-col items-center justify-center gap-3 bg-primary-50 dark:bg-primary-950/50 p-3 text-center">
                    <svg class="size-8 text-primary-500 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                    <p class="text-xs text-primary-600 dark:text-primary-400">Analisando…</p>
                  </div>
                  <div class="px-2 py-1.5 flex flex-col gap-0.5">
                    <p class="text-xs font-medium text-zinc-700 dark:text-zinc-300">Pág. {{ page.page_number }}</p>
                    <span class="inline-flex items-center gap-1 text-xs font-medium text-primary-700 dark:text-primary-300 bg-primary-50 dark:bg-primary-950 rounded px-1.5 py-0.5 w-fit">
                      <svg class="size-3 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                      Processando
                    </span>
                  </div>
                </div>
              } @else if (page.status === 'ERROR') {
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

  readonly activePage = computed<PageSummary | null>(() => {
    const n = this.activePageNumber();
    if (n == null) return null;
    return this.folder()?.pages.find((p) => p.page_number === n) ?? null;
  });

  readonly skeletons = Array.from({ length: 12 });

  private queryParamSub?: Subscription;

  ngOnInit() {
    const folderId = this.route.snapshot.paramMap.get('folderId')!;
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
