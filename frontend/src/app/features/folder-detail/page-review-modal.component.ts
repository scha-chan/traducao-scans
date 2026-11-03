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
import { CdkDrag, CdkDragDrop, CdkDragHandle, CdkDragPlaceholder, CdkDropList } from '@angular/cdk/drag-drop';
import { ReorderAutoOut } from '../../core/api/models';
import { BboxPx, FolderDetail, PageExport, PageSummary, TextBlockExport } from '../../core/api/models';
import { PagesApi } from '../../core/api/pages.api';
import { buildPageLines } from '../../export/txt-export';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import { PageImageViewerComponent } from './page-image-viewer.component';
import { BlockTableComponent } from './block-table.component';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const TABS: { id: 'edit' | 'order' | 'preview'; label: string }[] = [
  { id: 'edit', label: 'Editar' },
  { id: 'order', label: 'Ordenação' },
  { id: 'preview', label: 'Pré-visualizar texto' },
];

@Component({
  selector: 'app-page-review-modal',
  standalone: true,
  imports: [UiButtonComponent, PageImageViewerComponent, BlockTableComponent, CdkDropList, CdkDrag, CdkDragHandle, CdkDragPlaceholder],
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
            {{ saveErrorMessage() }}
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

          <!-- Content column: tabs + block table or preview -->
          <div class="lg:basis-3/5 min-h-0 flex flex-col overflow-hidden border-l border-zinc-200 dark:border-zinc-700">
            <!-- Tab bar -->
            <div class="flex flex-shrink-0 border-b border-zinc-200 dark:border-zinc-700 px-2 pt-1 gap-1" role="tablist">
              @for (tab of tabs; track tab.id) {
                <button
                  type="button"
                  role="tab"
                  [attr.aria-selected]="activeTab() === tab.id"
                  [attr.aria-controls]="'tab-' + tab.id + '-' + page().id"
                  class="px-3 py-1.5 text-xs font-medium rounded-t transition-colors focus-visible:outline-none focus-visible:ring-2 ring-primary-500 ring-offset-1"
                  [class.text-primary-700]="activeTab() === tab.id"
                  [class.dark:text-primary-300]="activeTab() === tab.id"
                  [class.border-b-2]="activeTab() === tab.id"
                  [class.border-primary-500]="activeTab() === tab.id"
                  [class.text-zinc-500]="activeTab() !== tab.id"
                  [class.hover:text-zinc-700]="activeTab() !== tab.id"
                  [class.dark:text-zinc-400]="activeTab() !== tab.id"
                  [class.dark:hover:text-zinc-200]="activeTab() !== tab.id"
                  (click)="setTab(tab.id)"
                >{{ tab.label }}</button>
              }
            </div>

            <!-- Edit tab -->
            <div
              [id]="'tab-edit-' + page().id"
              role="tabpanel"
              class="flex-1 min-h-0 flex overflow-hidden"
              [class.hidden]="activeTab() !== 'edit'"
            >
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

            <!-- Order tab -->
            <div
              [id]="'tab-order-' + page().id"
              role="tabpanel"
              class="flex-1 min-h-0 flex flex-col overflow-hidden"
              [class.hidden]="activeTab() !== 'order'"
            >
              <!-- Toolbar -->
              <div class="flex items-center justify-between px-3 py-2 border-b border-zinc-200 dark:border-zinc-700 flex-shrink-0 gap-2">
                <p class="text-xs text-zinc-400 dark:text-zinc-500 truncate">Arraste · Alt+↑↓ para mover o selecionado</p>
                <button
                  type="button"
                  [disabled]="reordering()"
                  (click)="recalcularOrdem()"
                  class="flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400 hover:underline disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                >
                  @if (reordering()) {
                    <svg class="size-3 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                    Calculando…
                  } @else {
                    ↻ Recalcular ordem
                  }
                </button>
              </div>

              <!-- Drag list -->
              @if (blockTable) {
                <div
                  cdkDropList
                  (cdkDropListDropped)="onOrderDrop($event)"
                  class="flex-1 overflow-y-auto divide-y divide-zinc-100 dark:divide-zinc-800"
                >
                  @for (ctrl of blockTable.form.controls; track $index; let i = $index) {
                    @let tipo = ctrl.value['tipo'];
                    <div
                      cdkDrag
                      (click)="orderFocusedIndex.set(i)"
                      class="flex items-center gap-2 px-3 py-2.5 transition-colors cursor-pointer select-none"
                      [class.bg-primary-50]="orderFocusedIndex() === i"
                      [class.dark:bg-primary-950]="orderFocusedIndex() === i"
                      [class.hover:bg-zinc-50]="orderFocusedIndex() !== i"
                      [class.dark:hover:bg-zinc-800/40]="orderFocusedIndex() !== i"
                      [attr.tabindex]="0"
                      (keydown.enter)="orderFocusedIndex.set(i)"
                    >
                      <!-- Drag handle -->
                      <div
                        cdkDragHandle
                        class="flex-shrink-0 text-zinc-300 dark:text-zinc-600 hover:text-zinc-500 dark:hover:text-zinc-400 cursor-grab active:cursor-grabbing"
                        aria-label="Arraste para reordenar"
                      >
                        <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                          <circle cx="9" cy="5" r="1" fill="currentColor"/><circle cx="15" cy="5" r="1" fill="currentColor"/>
                          <circle cx="9" cy="12" r="1" fill="currentColor"/><circle cx="15" cy="12" r="1" fill="currentColor"/>
                          <circle cx="9" cy="19" r="1" fill="currentColor"/><circle cx="15" cy="19" r="1" fill="currentColor"/>
                        </svg>
                      </div>

                      <!-- Order number -->
                      <span
                        class="text-[10px] font-mono font-bold tabular-nums w-4 text-right flex-shrink-0"
                        [class.text-primary-600]="orderFocusedIndex() === i"
                        [class.dark:text-primary-400]="orderFocusedIndex() === i"
                        [class.text-zinc-400]="orderFocusedIndex() !== i"
                      >{{ i + 1 }}</span>

                      <!-- Type badge -->
                      <span
                        class="inline-flex items-center rounded px-1 py-0.5 text-[9px] font-bold font-mono leading-none flex-shrink-0"
                        [class.bg-blue-100]="tipo === '#'"
                        [class.text-blue-700]="tipo === '#'"
                        [class.dark:bg-blue-900]="tipo === '#'"
                        [class.dark:text-blue-300]="tipo === '#'"
                        [class.bg-amber-100]="tipo === '$'"
                        [class.text-amber-700]="tipo === '$'"
                        [class.dark:bg-amber-900]="tipo === '$'"
                        [class.dark:text-amber-300]="tipo === '$'"
                      >{{ tipo }}</span>

                      <!-- Original preview -->
                      <span class="flex-1 min-w-0 text-[11px] text-zinc-700 dark:text-zinc-300 truncate font-jp">
                        {{ ctrl.value['original'] || '—' }}
                      </span>

                      <!-- CDK drag placeholder -->
                      <div *cdkDragPlaceholder class="h-10 bg-primary-50 dark:bg-primary-950/50 border-2 border-dashed border-primary-300 dark:border-primary-700 rounded"></div>
                    </div>
                  }
                </div>
              }
            </div>

            <!-- Preview tab -->
            <div
              [id]="'tab-preview-' + page().id"
              role="tabpanel"
              class="flex-1 min-h-0 overflow-y-auto p-4"
              [class.hidden]="activeTab() !== 'preview'"
            >
              @if (previewLines().length === 0) {
                <p class="text-xs text-zinc-400 dark:text-zinc-600 italic">Nenhum conteúdo para pré-visualizar.</p>
              } @else {
                <pre class="text-xs font-mono text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap leading-relaxed">{{ previewLines().join('\n') }}</pre>
              }
            </div>
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
            <ui-button variant="primary" [disabled]="saving()" (click)="save()" [title]="'Salvar (Ctrl+S)'">
              @if (blockTable?.isDirty && !saving()) {
                <span class="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mr-1.5 -mt-px" aria-hidden="true"></span>
              }
              {{ saving() ? 'Salvando…' : 'Salvar' }}
            </ui-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Unsaved changes confirmation dialog -->
    @if (unsavedDialogOpen()) {
      <div
        class="fixed inset-0 z-[60] bg-zinc-950/60 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="unsaved-dialog-title"
      >
        <div class="w-full max-w-sm rounded-xl bg-white dark:bg-zinc-900 shadow-2xl p-6">
          <h2 id="unsaved-dialog-title" class="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            Alterações não salvas
          </h2>
          <p class="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            Você tem alterações não salvas nesta página. Deseja sair mesmo assim?
          </p>
          <div class="flex justify-end gap-2 mt-5">
            <ui-button variant="secondary" (click)="cancelDiscard()">Continuar editando</ui-button>
            <ui-button variant="destructive" (click)="confirmDiscard()">Sair sem salvar</ui-button>
          </div>
        </div>
      </div>
    }
  `,
})
export class PageReviewModalComponent implements OnInit, OnDestroy {
  private readonly pagesApi = inject(PagesApi);

  readonly tabs = TABS;

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
  readonly saveErrorMessage = signal('');
  private saveErrorTimeout?: ReturnType<typeof setTimeout>;

  readonly unsavedDialogOpen = signal(false);
  private pendingAction = signal<(() => void) | null>(null);

  readonly activeTab = signal<'edit' | 'order' | 'preview'>('edit');
  readonly previewLines = signal<string[]>([]);
  readonly reordering = signal(false);
  readonly orderFocusedIndex = signal<number | null>(null);

  private blocksSub?: import('rxjs').Subscription;
  private saveSub?: import('rxjs').Subscription;
  private reorderSub?: import('rxjs').Subscription;
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
    this.reorderSub?.unsubscribe();
    clearTimeout(this.smallRectTimeout);
    clearTimeout(this.saveErrorTimeout);
    (this.previousActiveElement as HTMLElement | null)?.focus();
  }

  loadBlocks() {
    this.activeTab.set('edit');
    this.previewLines.set([]);
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
    this.blockTable.clearServerErrors();
    this.saveSub?.unsubscribe();
    this.saveSub = this.pagesApi
      .saveJson(this.page().id, this.blockTable.toTextBlocks())
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.blockTable.markAsPristine();
        },
        error: (err) => {
          this.saving.set(false);
          const body = err?.error;
          if (err?.status === 422 && body?.error?.details) {
            this.blockTable.setServerErrors(body.error.details);
            this.saveErrorMessage.set(body.error.message ?? 'Dados inválidos');
          } else {
            this.saveErrorMessage.set('Erro ao salvar — tente novamente.');
          }
          this.saveError.set(true);
          clearTimeout(this.saveErrorTimeout);
          this.saveErrorTimeout = setTimeout(() => this.saveError.set(false), 4000);
        },
      });
  }

  private guardUnsaved(action: () => void) {
    if (this.blockTable?.isDirty) {
      this.pendingAction.set(action);
      this.unsavedDialogOpen.set(true);
    } else {
      action();
    }
  }

  confirmDiscard() {
    this.unsavedDialogOpen.set(false);
    const action = this.pendingAction();
    this.pendingAction.set(null);
    action?.();
  }

  cancelDiscard() {
    this.unsavedDialogOpen.set(false);
    this.pendingAction.set(null);
  }

  setTab(tab: 'edit' | 'order' | 'preview') {
    this.activeTab.set(tab);
    if (tab === 'preview') {
      this.refreshPreview();
    }
  }

  onOrderDrop(event: CdkDragDrop<unknown>) {
    this.blockTable?.reorderAt(event.previousIndex, event.currentIndex);
    this.orderFocusedIndex.set(event.currentIndex);
  }

  recalcularOrdem() {
    if (this.reordering()) return;
    this.reordering.set(true);
    this.reorderSub?.unsubscribe();
    this.reorderSub = this.pagesApi.reorderAuto(this.page().id).subscribe({
      next: (result: ReorderAutoOut) => {
        this.blocks.set(result.blocos);
        this.orderFocusedIndex.set(null);
        this.reordering.set(false);
      },
      error: () => {
        this.reordering.set(false);
      },
    });
  }

  private refreshPreview() {
    const blocks = this.blockTable?.toTextBlocks() ?? [];
    const pageExport: PageExport = {
      pagina: this.page().page_number,
      arquivo: this.page().file_name,
      status: 'REVIEW',
      blocos: blocks,
    };
    this.previewLines.set(buildPageLines(pageExport));
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
    this.guardUnsaved(() => this.closed.emit());
  }

  navigate(direction: -1 | 1) {
    const current = this.page().page_number;
    const target = current + direction;
    const targetPage = this.folder().pages.find((p) => p.page_number === target);
    if (targetPage) {
      this.guardUnsaved(() => this.navigated.emit(target));
    }
  }

  @HostListener('keydown', ['$event'])
  onKeyDown(e: KeyboardEvent) {
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      this.save();
      return;
    }

    if (e.key === 'Escape') {
      if (this.viewerDrawMode()) return;
      this.close();
      return;
    }

    // Ignore shortcuts when focus is inside a text input
    const tag = (e.target as HTMLElement).tagName;
    const isText = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

    if (!isText) {
      // Alt+↑/↓ in order tab: move focused item
      if (e.altKey && this.activeTab() === 'order' && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
        e.preventDefault();
        const cur = this.orderFocusedIndex();
        if (cur === null || !this.blockTable) return;
        const next = e.key === 'ArrowUp' ? cur - 1 : cur + 1;
        this.blockTable.reorderAt(cur, next);
        this.orderFocusedIndex.set(next);
        return;
      }

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
