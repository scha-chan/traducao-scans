import { Component, OnInit, OnDestroy, signal, inject, computed } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { FoldersApi } from '../../core/api/folders.api';
import { PagesApi } from '../../core/api/pages.api';
import { FolderDetail, PageSummary } from '../../core/api/models';
import { buildFolderTxt, downloadTxt, txtFileName } from '../../export/txt-export';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import { UiSkeletonComponent } from '../../shared/ui/ui-skeleton.component';
import { UiEmptyStateComponent } from '../../shared/ui/ui-empty-state.component';
import { PageReviewModalComponent } from './page-review-modal.component';

@Component({
  selector: 'app-folder-detail-page',
  standalone: true,
  imports: [RouterLink, UiButtonComponent, UiSkeletonComponent, UiEmptyStateComponent, PageReviewModalComponent],
  templateUrl: './folder-detail.page.html',
  styleUrl: './folder-detail.page.scss',
})
export class FolderDetailPage implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly foldersApi = inject(FoldersApi);
  private readonly pagesApi = inject(PagesApi);

  readonly folder = signal<FolderDetail | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly downloading = signal(false);

  private readonly retryingIds = signal<string[]>([]);
  private readonly activePageNumber = signal<number | null>(null);

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
