import {
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  OnInit,
  ViewChild,
  computed,
  input,
  output,
  signal,
  inject,
} from '@angular/core';
import { BboxPx, FolderDetail, PageSummary, TextBlockExport } from '../../core/api/models';
import { PagesApi } from '../../core/api/pages.api';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import { PageImageViewerComponent } from './page-image-viewer.component';
import { BlockTableComponent } from './block-table.component';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

@Component({
  selector: 'app-page-review-modal',
  standalone: true,
  imports: [UiButtonComponent, PageImageViewerComponent, BlockTableComponent],
  template: `
    <!-- Overlay -->
    <div
      class="fixed inset-0 z-50 bg-zinc-950/60 backdrop-blur-sm flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      [attr.aria-labelledby]="'modal-title-' + page().id"
      #overlay
    >
      <!-- Panel -->
      <div
        class="relative w-[95vw] h-[90dvh] flex flex-col rounded-xl bg-white dark:bg-zinc-900 shadow-2xl overflow-hidden"
        #panel
      >
        <!-- Toast: região pequena demais -->
        @if (smallRectToast()) {
          <div
            class="absolute top-16 left-1/2 -translate-x-1/2 z-10 rounded-lg px-4 py-2 text-sm bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 shadow pointer-events-none"
            role="status"
            aria-live="polite"
          >
            Retângulo muito pequeno — arraste uma área maior (mín. 10×10 px).
          </div>
        }

        <!-- Toast: erro ao salvar -->
        @if (saveError()) {
          <div
            class="absolute top-16 left-1/2 -translate-x-1/2 z-10 rounded-lg px-4 py-2 text-sm bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 shadow pointer-events-none"
            role="alert"
            aria-live="assertive"
          >
            Erro ao salvar — tente novamente.
          </div>
        }

        <!-- Header -->
        <div class="h-14 flex items-center justify-between px-4 border-b border-zinc-200 dark:border-zinc-700 flex-shrink-0">
          <div class="flex items-center gap-2 min-w-0">
            <p [id]="'modal-title-' + page().id" class="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate">
              {{ folder().name }} — Página {{ page().page_number }} de {{ folder().pages.length }}
            </p>
            <span class="text-xs text-zinc-400 dark:text-zinc-500 hidden sm:block truncate">({{ page().file_name }})</span>
          </div>
          <div class="flex items-center gap-1 flex-shrink-0">
            <button
              type="button"
              [disabled]="!hasPrev()"
              (click)="navigate(-1)"
              class="flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Página anterior"
            >
              <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6"/></svg>
              <span class="hidden sm:inline">Anterior</span>
            </button>
            <button
              type="button"
              [disabled]="!hasNext()"
              (click)="navigate(1)"
              class="flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Próxima página"
            >
              <span class="hidden sm:inline">Próxima</span>
              <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button
              type="button"
              (click)="close()"
              class="ml-2 rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              aria-label="Fechar modal"
            >
              <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </div>

        <!-- Body: 40% image | 60% block table + panel -->
        <div class="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden">
          <!-- Image column -->
          <div class="h-[35dvh] lg:h-auto lg:basis-2/5 lg:max-w-[40%] min-h-0">
            <app-page-image-viewer
              [imageUrl]="imageUrl()"
              [altText]="'Página ' + page().page_number"
              [blocks]="blocks()"
              [selectedBlockIndex]="selectedBlockIndex()"
              (regionDrawn)="onRegionDrawn($event)"
              (regionTooSmall)="onRegionTooSmall()"
              (drawModeChange)="viewerDrawMode.set($event)"
            />
          </div>

          <!-- Content column: compact list + detail panel -->
          <div class="lg:basis-3/5 min-h-0 flex overflow-hidden">
            @if (blocksError()) {
              <div class="p-4 text-sm text-red-600 dark:text-red-400 flex-1">
                Não foi possível carregar os blocos.
                <button type="button" class="underline ml-1" (click)="loadBlocks()">Tentar novamente</button>
              </div>
            }
            @else {
              <app-block-table
                [blocks]="blocks()"
                [loading]="blocksLoading()"
                (selectedIndexChange)="onBlockSelected($event)"
              />
            }
          </div>
        </div>

        <!-- Footer -->
        <div class="h-16 flex items-center justify-between px-4 border-t border-zinc-200 dark:border-zinc-700 flex-shrink-0">
          <span class="text-xs text-zinc-400 dark:text-zinc-500 hidden sm:block">
            J/K: navegar · T: alternar tipo · ←/→: página
          </span>
          <div class="flex items-center gap-2">
            <ui-button variant="secondary" (click)="close()">Cancelar</ui-button>
            <ui-button variant="secondary" [disabled]="true" title="Disponível em FE-22">
              ↻ Reprocessar
            </ui-button>
            <ui-button variant="primary" [disabled]="saving()" (click)="save()">
              {{ saving() ? 'Salvando…' : 'Salvar' }}
            </ui-button>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class PageReviewModalComponent implements OnInit, OnDestroy {
  private readonly pagesApi = inject(PagesApi);

  readonly folder = input.required<FolderDetail>();
  readonly page = input.required<PageSummary>();

  readonly closed = output<void>();
  readonly navigated = output<number>();


  @ViewChild('panel') panelRef!: ElementRef<HTMLElement>;
  @ViewChild(BlockTableComponent) blockTable!: BlockTableComponent;

  readonly hasPrev = computed(() => this.page().page_number > 1);
  readonly hasNext = computed(() => this.page().page_number < this.folder().pages.length);

  readonly imageUrl = computed(() => this.pagesApi.imageUrl(this.page()));

  readonly blocks = signal<TextBlockExport[]>([]);
  readonly blocksLoading = signal(false);
  readonly blocksError = signal(false);
  readonly selectedBlockIndex = signal<number | null>(null);

  readonly viewerDrawMode = signal(false);
  readonly smallRectToast = signal(false);
  private smallRectTimeout?: ReturnType<typeof setTimeout>;

  readonly saving = signal(false);
  readonly saveError = signal(false);
  private saveErrorTimeout?: ReturnType<typeof setTimeout>;

  private blocksSub?: import('rxjs').Subscription;
  private saveSub?: import('rxjs').Subscription;
  private previousActiveElement: Element | null = null;

  ngOnInit() {
    this.previousActiveElement = document.activeElement;
    document.body.style.overflow = 'hidden';
    setTimeout(() => this.focusFirst(), 0);
    this.loadBlocks();
  }

  ngOnDestroy() {
    document.body.style.overflow = '';
    this.blocksSub?.unsubscribe();
    this.saveSub?.unsubscribe();
    clearTimeout(this.smallRectTimeout);
    clearTimeout(this.saveErrorTimeout);
    (this.previousActiveElement as HTMLElement | null)?.focus();
  }

  loadBlocks() {
    this.blocksLoading.set(true);
    this.blocksError.set(false);
    this.blocksSub?.unsubscribe();
    this.blocksSub = this.pagesApi.getJson(this.page().id).subscribe({
      next: (data) => {
        this.blocks.set(data);
        this.blocksLoading.set(false);
      },
      error: () => {
        this.blocksError.set(true);
        this.blocksLoading.set(false);
      },
    });
  }

  save() {
    if (this.saving()) return;
    this.saving.set(true);
    this.saveError.set(false);
    this.saveSub?.unsubscribe();
    this.saveSub = this.pagesApi
      .saveJson(this.page().id, this.blockTable.toTextBlocks())
      .subscribe({
        next: () => {
          this.saving.set(false);
        },
        error: () => {
          this.saving.set(false);
          this.saveError.set(true);
          clearTimeout(this.saveErrorTimeout);
          this.saveErrorTimeout = setTimeout(() => this.saveError.set(false), 4000);
        },
      });
  }

  onBlockSelected(index: number | null) {
    this.selectedBlockIndex.set(index);
  }

  onRegionDrawn(bbox: BboxPx) {
    this.blockTable.addBlockWithBbox(bbox);
  }

  onRegionTooSmall() {
    clearTimeout(this.smallRectTimeout);
    this.smallRectToast.set(true);
    this.smallRectTimeout = setTimeout(() => this.smallRectToast.set(false), 3000);
  }

  close() {
    this.closed.emit();
  }

  navigate(direction: -1 | 1) {
    const current = this.page().page_number;
    const target = current + direction;
    const targetPage = this.folder().pages.find((p) => p.page_number === target);
    if (targetPage) {
      this.navigated.emit(target);
    }
  }

  @HostListener('keydown', ['$event'])
  onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      if (this.viewerDrawMode()) return;
      this.close();
      return;
    }

    // Ignore shortcuts when focus is inside a text input
    const tag = (e.target as HTMLElement).tagName;
    const isText = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

    if (!isText) {
      if (e.key === 'ArrowLeft' && this.hasPrev()) {
        this.navigate(-1);
        return;
      }
      if (e.key === 'ArrowRight' && this.hasNext()) {
        this.navigate(1);
        return;
      }
      if (e.key === 'j' || e.key === 'J') {
        this.blockTable?.selectNext();
        return;
      }
      if (e.key === 'k' || e.key === 'K') {
        this.blockTable?.selectPrev();
        return;
      }
      if (e.key === 't' || e.key === 'T') {
        this.blockTable?.toggleType();
        return;
      }
    }

    // Focus trap
    if (e.key === 'Tab') {
      const panel = this.panelRef?.nativeElement;
      if (!panel) return;
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  private focusFirst() {
    const panel = this.panelRef?.nativeElement;
    if (!panel) return;
    const first = panel.querySelector<HTMLElement>(FOCUSABLE);
    first?.focus();
  }
}
