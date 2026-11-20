import {
  Component,
  ElementRef,
  HostListener,
  OnInit,
  ViewChild,
  signal,
  computed,
  inject,
} from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ActivatedRoute, Router } from '@angular/router';
import { FoldersApi } from '../../core/api/folders.api';
import { PagesApi } from '../../core/api/pages.api';
import { NotificationService } from '../../core/notifications/notification.service';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import type {
  AnnotationBBox,
  PageSummary,
  SliceType,
} from '../../core/api/models';

interface Slice {
  id: string;
  order: number;
  type: SliceType;
  bbox: AnnotationBBox;
}

type DragMode = 'none' | 'creating' | 'moving' | 'resizing';

interface ResizeHandle {
  cursor: string;
  dx: number;
  dy: number;
}

const HANDLE_SIZE = 8;
const MIN_SLICE_PX = 10;

@Component({
  selector: 'app-annotation-page',
  standalone: true,
  imports: [UiButtonComponent],
  template: `
    <div class="annotation-layout">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <h2 class="sidebar-title">Anotador de regiões</h2>
          <p class="sidebar-sub">
            Imagem {{ currentIndex() + 1 }} de {{ pages().length }}
          </p>
        </div>

        <div class="page-nav">
          <button class="nav-btn" [disabled]="currentIndex() === 0" (click)="prevPage()" title="Anterior (←)">‹</button>
          <span class="page-counter">{{ currentPage()?.file_name ?? '' }}</span>
          <button
            class="nav-btn"
            [disabled]="currentIndex() === pages().length - 1"
            (click)="nextPage()"
            title="Próxima (→)"
          >›</button>
          <button
            class="nav-btn remove-page-btn"
            [disabled]="pages().length <= 1"
            (click)="removePage(currentIndex())"
            title="Remover esta imagem da anotação"
          >🗑</button>
        </div>

        <div class="slices-list">
          @for (s of currentSlices(); track s.id; let i = $index) {
            <div
              class="slice-item"
              [class.selected]="selectedId() === s.id"
              [class.dragging]="dragSliceSourceIdx() === i"
              [class.drag-over]="dragSliceOverIdx() === i && dragSliceSourceIdx() !== i"
              draggable="true"
              tabindex="0"
              (click)="selectSlice(s.id)"
              (keyup.enter)="selectSlice(s.id)"
              (dragstart)="onSliceDragStart(i)"
              (dragover)="onSliceDragOver($event, i)"
              (drop)="onSliceDrop(i)"
              (dragend)="onSliceDragEnd()"
            >
              <span class="badge" [class.speech]="s.type === '#'" [class.scene]="s.type === '$'">
                {{ s.type }}
              </span>
              <span class="slice-order">{{ s.order }}</span>
              <span class="slice-info">{{ s.bbox.width }}×{{ s.bbox.height }}</span>
              <button class="delete-btn" (click)="deleteSlice(s.id); $event.stopPropagation()">✕</button>
            </div>
          }
          @if (currentSlices().length === 0) {
            <p class="no-slices">Arraste sobre a imagem para criar fatias</p>
          }
        </div>

        <div class="sidebar-actions">
          <div class="tip">
            <kbd>T</kbd> alterna tipo · <kbd>Del</kbd> exclui · <kbd>←/→</kbd> navega
          </div>
          <ui-button
            variant="primary"
            [disabled]="!canProcess()"
            [loading]="processing()"
            (click)="processAll()"
          >
            @if (processing()) { Enviando… } @else { Processar pasta }
          </ui-button>
          @if (!allPagesAnnotated()) {
            <p class="warn">Anote pelo menos 1 fatia em cada imagem para processar</p>
          }
        </div>
      </aside>

      <!-- Canvas area -->
      <main class="canvas-area">
        @if (loadingImage()) {
          <div class="loading">Carregando…</div>
        }
        <!-- <img> must stay in DOM even while loading so (load) can fire -->
        <div
          class="canvas-wrapper"
          [style.display]="loadingImage() ? 'none' : 'block'"
          [style.width.px]="displayW()"
          [style.height.px]="displayH()"
        >
          <img
            #imgEl
            [src]="currentImageUrl()"
            [style.width.px]="displayW()"
            [style.height.px]="displayH()"
            (load)="onImageLoad()"
            alt="página"
            draggable="false"
          />
          <canvas
            #canvasEl
            [width]="displayW()"
            [height]="displayH()"
            (mousedown)="onMouseDown($event)"
            (mousemove)="onMouseMove($event)"
            (mouseup)="onMouseUp($event)"
            (mouseleave)="onMouseUp($event)"
          ></canvas>
        </div>
      </main>
    </div>
  `,
  styles: [`
    :host { display: block; height: 100vh; overflow: hidden; }

    .annotation-layout {
      display: flex;
      height: 100vh;
      background: var(--surface-1, #0f0f0f);
      color: var(--text-1, #e8e8e8);
    }

    .sidebar {
      width: 260px;
      min-width: 260px;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--border, #2a2a2a);
      background: var(--surface-2, #1a1a1a);
      padding: 16px;
      gap: 12px;
      overflow: hidden;
    }

    .sidebar-title { font-size: 14px; font-weight: 600; margin: 0; }
    .sidebar-sub { font-size: 12px; color: var(--text-3, #888); margin: 0; }

    .page-nav {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .nav-btn {
      width: 28px; height: 28px;
      border: 1px solid var(--border, #2a2a2a);
      background: var(--surface-3, #222);
      color: inherit; cursor: pointer; border-radius: 4px; font-size: 16px;
    }
    .nav-btn:disabled { opacity: 0.35; cursor: default; }
    .remove-page-btn { font-size: 13px; }
    .page-counter { flex: 1; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    .slices-list {
      flex: 1; overflow-y: auto;
      display: flex; flex-direction: column; gap: 4px;
    }

    .slice-item {
      display: flex; align-items: center; gap: 6px;
      padding: 6px 8px;
      border: 1px solid transparent;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      background: var(--surface-3, #222);
    }
    .slice-item.selected { border-color: #3b82f6; background: rgba(59,130,246,.12); }
    .slice-item:hover:not(.selected) { background: var(--surface-4, #2a2a2a); }
    .slice-item.dragging { opacity: 0.4; }
    .slice-item.drag-over { border-color: #3b82f6; background: rgba(59,130,246,.18); }

    .badge {
      width: 20px; height: 20px; border-radius: 4px;
      display: flex; align-items: center; justify-content: center;
      font-size: 11px; font-weight: 700;
    }
    .badge.speech { background: #1d4ed8; color: #fff; }
    .badge.scene  { background: #92400e; color: #fbbf24; }

    .slice-order { font-weight: 600; }
    .slice-info { flex: 1; color: var(--text-3, #888); }
    .delete-btn {
      background: none; border: none; color: var(--text-3, #888);
      cursor: pointer; font-size: 12px; padding: 2px 4px;
    }
    .delete-btn:hover { color: #ef4444; }

    .no-slices { font-size: 12px; color: var(--text-3, #888); text-align: center; padding: 24px 0; }

    .sidebar-actions { display: flex; flex-direction: column; gap: 8px; }

    .tip {
      font-size: 11px; color: var(--text-3, #888);
      line-height: 1.6;
    }
    kbd {
      background: var(--surface-3, #222); border: 1px solid var(--border, #333);
      border-radius: 3px; padding: 1px 4px; font-size: 10px;
    }

    .warn { font-size: 11px; color: #f59e0b; margin: 0; }

    .canvas-area {
      flex: 1;
      overflow: auto;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding: 16px;
      background: #111;
    }

    .loading { align-self: center; color: var(--text-3, #888); font-size: 14px; }

    .canvas-wrapper { position: relative; }
    .canvas-wrapper img { display: block; user-select: none; }
    .canvas-wrapper canvas {
      position: absolute; top: 0; left: 0;
      cursor: crosshair;
    }
  `],
})
export class AnnotationPage implements OnInit {
  @ViewChild('canvasEl') canvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('imgEl') imgRef!: ElementRef<HTMLImageElement>;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private foldersApi = inject(FoldersApi);
  private pagesApi = inject(PagesApi);
  private notifications = inject(NotificationService);

  folderId = '';
  pages = signal<PageSummary[]>([]);
  currentIndex = signal(0);
  loadingImage = signal(true);

  // slices per page_id
  private allSlices = signal<Map<string, Slice[]>>(new Map());

  selectedId = signal<string | null>(null);
  processing = signal(false);

  // natural image dimensions
  private naturalW = 0;
  private naturalH = 0;
  displayW = signal(800);
  displayH = signal(600);

  private dragMode: DragMode = 'none';
  private dragStart = { x: 0, y: 0 };
  private movingSliceOrigBbox: AnnotationBBox | null = null;
  private activeResizeHandle: ResizeHandle | null = null;
  private nextOrder = signal(1);

  currentPage = computed(() => this.pages()[this.currentIndex()] ?? null);
  currentImageUrl = computed(() => {
    const p = this.currentPage();
    return p ? this.pagesApi.imageUrl(p) : '';
  });
  currentSlices = computed(() => {
    const p = this.currentPage();
    if (!p) return [];
    return (this.allSlices().get(p.id) ?? []).slice().sort((a, b) => a.order - b.order);
  });
  allPagesAnnotated = computed(() =>
    this.pages().every(p => (this.allSlices().get(p.id)?.length ?? 0) > 0)
  );
  canProcess = computed(() => this.allPagesAnnotated() && !this.processing());

  ngOnInit(): void {
    this.folderId = this.route.snapshot.paramMap.get('folderId') ?? '';
    const startPageId = this.route.snapshot.queryParamMap.get('pageId');
    this.foldersApi.get(this.folderId).subscribe({
      next: folder => {
        const sorted = [...folder.pages].sort((a, b) => a.page_number - b.page_number);
        this.pages.set(sorted);
        if (startPageId) {
          const idx = sorted.findIndex(p => p.id === startPageId);
          if (idx >= 0) this.currentIndex.set(idx);
        }
        if (sorted.length > 0) this.loadingImage.set(true);
        this._loadExistingSlices(sorted);
      },
      error: () => this.router.navigate(['/']),
    });
  }

  private _loadExistingSlices(pages: PageSummary[]): void {
    const withSlices = pages.filter(p => p.slice_count > 0);
    if (withSlices.length === 0) return;
    forkJoin(
      withSlices.map(p => this.pagesApi.getSlices(p.id).pipe(catchError(() => of([]))))
    ).subscribe(results => {
      const pageIds = withSlices.map(p => p.id);
      const m = new Map<string, Slice[]>();
      results.forEach((slices, i) => {
        if (slices.length > 0) {
          m.set(pageIds[i], slices.map(s => ({
            id: s.id,
            order: s.order_number,
            type: s.type,
            bbox: { x: s.bbox_x, y: s.bbox_y, width: s.bbox_width, height: s.bbox_height },
          })));
          const max = Math.max(...slices.map(s => s.order_number));
          this.nextOrder.set(Math.max(this.nextOrder(), max + 1));
        }
      });
      this.allSlices.set(m);
    });
  }

  onImageLoad(): void {
    if (!this.imgRef) return;
    const img = this.imgRef.nativeElement;
    this.naturalW = img.naturalWidth;
    this.naturalH = img.naturalHeight;
    const maxW = Math.min(window.innerWidth - 300, 1200);
    const scale = Math.min(1, maxW / this.naturalW);
    this.displayW.set(Math.round(this.naturalW * scale));
    this.displayH.set(Math.round(this.naturalH * scale));
    this.loadingImage.set(false);
    this.redraw();
  }

  // ── Keyboard shortcuts ──────────────────────────────────────────────────

  @HostListener('document:keydown', ['$event'])
  onKey(e: KeyboardEvent): void {
    if ((e.target as HTMLElement).tagName === 'INPUT') return;
    if (e.key === 'ArrowLeft') { e.preventDefault(); this.prevPage(); }
    if (e.key === 'ArrowRight') { e.preventDefault(); this.nextPage(); }
    if ((e.key === 'Delete' || e.key === 'Backspace') && this.selectedId()) {
      e.preventDefault();
      this.deleteSlice(this.selectedId()!);
    }
    if (e.key === 't' || e.key === 'T') {
      const id = this.selectedId();
      if (id) this.toggleType(id);
    }
  }

  // ── Navigation ───────────────────────────────────────────────────────────

  prevPage(): void {
    if (this.currentIndex() > 0) {
      this.currentIndex.update(i => i - 1);
      this.loadingImage.set(true);
    }
  }

  nextPage(): void {
    if (this.currentIndex() < this.pages().length - 1) {
      this.currentIndex.update(i => i + 1);
      this.loadingImage.set(true);
    }
  }

  // ── Slice management ─────────────────────────────────────────────────────

  private getSlices(): Slice[] {
    const p = this.currentPage();
    if (!p) return [];
    return this.allSlices().get(p.id) ?? [];
  }

  private setSlices(slices: Slice[]): void {
    const p = this.currentPage();
    if (!p) return;
    const m = new Map(this.allSlices());
    m.set(p.id, slices);
    this.allSlices.set(m);
  }

  selectSlice(id: string): void {
    this.selectedId.set(id);
    this.redraw();
  }

  deleteSlice(id: string): void {
    const remaining = this.getSlices().filter(s => s.id !== id);
    this.renumber(remaining);
    this.setSlices(remaining);
    if (this.selectedId() === id) this.selectedId.set(null);
    this.redraw();
  }

  toggleType(id: string): void {
    const slices = this.getSlices().map(s =>
      s.id === id ? { ...s, type: (s.type === '#' ? '$' : '#') as SliceType } : s
    );
    this.setSlices(slices);
    this.redraw();
  }

  private renumber(slices: Slice[]): void {
    slices.forEach((s, i) => { s.order = i + 1; });
    this.nextOrder.set(slices.length + 1);
  }

  // ── Mouse events ─────────────────────────────────────────────────────────

  onMouseDown(e: MouseEvent): void {
    const { x, y } = this.canvasPos(e);
    // Check resize handles first
    const sel = this.getSlices().find(s => s.id === this.selectedId());
    if (sel) {
      const handle = this.hitTestHandle(sel.bbox, x, y);
      if (handle) {
        this.dragMode = 'resizing';
        this.dragStart = { x, y };
        this.movingSliceOrigBbox = { ...sel.bbox };
        this.activeResizeHandle = handle;
        return;
      }
    }
    // Hit test existing slices (topmost first)
    const hit = this.hitTestSlice(x, y);
    if (hit) {
      this.selectedId.set(hit.id);
      this.dragMode = 'moving';
      this.dragStart = { x, y };
      this.movingSliceOrigBbox = { ...hit.bbox };
      this.redraw();
      return;
    }
    // Create new slice
    this.selectedId.set(null);
    this.dragMode = 'creating';
    this.dragStart = { x, y };
  }

  onMouseMove(e: MouseEvent): void {
    if (this.dragMode === 'none') {
      this.updateCursor(e);
      return;
    }
    const { x, y } = this.canvasPos(e);
    if (this.dragMode === 'creating') {
      this.redrawWithGhost(this.dragStart.x, this.dragStart.y, x, y);
    } else if (this.dragMode === 'moving') {
      this.moveSelected(x - this.dragStart.x, y - this.dragStart.y);
    } else if (this.dragMode === 'resizing') {
      this.resizeSelected(x - this.dragStart.x, y - this.dragStart.y);
    }
  }

  onMouseUp(e: MouseEvent): void {
    if (this.dragMode === 'creating') {
      const { x, y } = this.canvasPos(e);
      this.finishCreate(this.dragStart.x, this.dragStart.y, x, y);
    }
    this.dragMode = 'none';
    this.activeResizeHandle = null;
    this.movingSliceOrigBbox = null;
    this.redraw();
  }

  // ── Drag helpers ──────────────────────────────────────────────────────────

  private canvasPos(e: MouseEvent): { x: number; y: number } {
    const rect = this.canvasRef.nativeElement.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  private finishCreate(x1: number, y1: number, x2: number, y2: number): void {
    const bbox = this.normBbox(x1, y1, x2, y2);
    if (bbox.width < MIN_SLICE_PX || bbox.height < MIN_SLICE_PX) return;
    const natural = this.toNatural(bbox);
    const order = this.nextOrder();
    const slice: Slice = {
      id: `slice-${Date.now()}-${Math.random()}`,
      order,
      type: '#',
      bbox: natural,
    };
    const slices = [...this.getSlices(), slice];
    this.nextOrder.update(n => n + 1);
    this.setSlices(slices);
    this.selectedId.set(slice.id);
    this.redraw();
  }

  private moveSelected(dx: number, dy: number): void {
    if (!this.movingSliceOrigBbox) return;
    const id = this.selectedId();
    if (!id) return;
    const orig = this.toDisplay(this.movingSliceOrigBbox);
    const newDisplay: AnnotationBBox = {
      x: Math.max(0, Math.min(orig.x + dx, this.displayW() - orig.width)),
      y: Math.max(0, Math.min(orig.y + dy, this.displayH() - orig.height)),
      width: orig.width,
      height: orig.height,
    };
    const slices = this.getSlices().map(s =>
      s.id === id ? { ...s, bbox: this.toNatural(newDisplay) } : s
    );
    this.setSlices(slices);
    this.redraw();
  }

  private resizeSelected(dx: number, dy: number): void {
    if (!this.movingSliceOrigBbox || !this.activeResizeHandle) return;
    const id = this.selectedId();
    if (!id) return;
    const orig = this.toDisplay(this.movingSliceOrigBbox);
    const h = this.activeResizeHandle;
    let { x, y, width, height } = orig;
    if (h.dx === -1) { x += dx; width -= dx; }
    else if (h.dx === 1) { width += dx; }
    if (h.dy === -1) { y += dy; height -= dy; }
    else if (h.dy === 1) { height += dy; }
    if (width < MIN_SLICE_PX) { width = MIN_SLICE_PX; }
    if (height < MIN_SLICE_PX) { height = MIN_SLICE_PX; }
    const slices = this.getSlices().map(s =>
      s.id === id ? { ...s, bbox: this.toNatural({ x, y, width, height }) } : s
    );
    this.setSlices(slices);
    this.redraw();
  }

  // ── Coordinate utils ──────────────────────────────────────────────────────

  private scaleX(): number { return this.naturalW > 0 ? this.displayW() / this.naturalW : 1; }
  private scaleY(): number { return this.naturalH > 0 ? this.displayH() / this.naturalH : 1; }

  private toDisplay(b: AnnotationBBox): AnnotationBBox {
    return {
      x: Math.round(b.x * this.scaleX()),
      y: Math.round(b.y * this.scaleY()),
      width: Math.round(b.width * this.scaleX()),
      height: Math.round(b.height * this.scaleY()),
    };
  }

  private toNatural(b: AnnotationBBox): AnnotationBBox {
    return {
      x: Math.round(b.x / this.scaleX()),
      y: Math.round(b.y / this.scaleY()),
      width: Math.round(b.width / this.scaleX()),
      height: Math.round(b.height / this.scaleY()),
    };
  }

  private normBbox(x1: number, y1: number, x2: number, y2: number): AnnotationBBox {
    return {
      x: Math.min(x1, x2), y: Math.min(y1, y2),
      width: Math.abs(x2 - x1), height: Math.abs(y2 - y1),
    };
  }

  // ── Hit testing ───────────────────────────────────────────────────────────

  private hitTestSlice(x: number, y: number): Slice | null {
    const slices = this.getSlices();
    for (let i = slices.length - 1; i >= 0; i--) {
      const d = this.toDisplay(slices[i].bbox);
      if (x >= d.x && x <= d.x + d.width && y >= d.y && y <= d.y + d.height) {
        return slices[i];
      }
    }
    return null;
  }

  private hitTestHandle(bbox: AnnotationBBox, x: number, y: number): ResizeHandle | null {
    const d = this.toDisplay(bbox);
    const handles: { bx: number; by: number; handle: ResizeHandle }[] = [
      { bx: d.x,            by: d.y,             handle: { cursor: 'nw-resize', dx: -1, dy: -1 } },
      { bx: d.x + d.width,  by: d.y,             handle: { cursor: 'ne-resize', dx:  1, dy: -1 } },
      { bx: d.x,            by: d.y + d.height,  handle: { cursor: 'sw-resize', dx: -1, dy:  1 } },
      { bx: d.x + d.width,  by: d.y + d.height,  handle: { cursor: 'se-resize', dx:  1, dy:  1 } },
    ];
    for (const { bx, by, handle } of handles) {
      if (Math.abs(x - bx) <= HANDLE_SIZE && Math.abs(y - by) <= HANDLE_SIZE) return handle;
    }
    return null;
  }

  private updateCursor(e: MouseEvent): void {
    const { x, y } = this.canvasPos(e);
    const canvas = this.canvasRef.nativeElement;
    const sel = this.getSlices().find(s => s.id === this.selectedId());
    if (sel) {
      const h = this.hitTestHandle(sel.bbox, x, y);
      if (h) { canvas.style.cursor = h.cursor; return; }
    }
    const hit = this.hitTestSlice(x, y);
    canvas.style.cursor = hit ? 'move' : 'crosshair';
  }

  // ── Drawing ────────────────────────────────────────────────────────────────

  private redraw(): void {
    if (!this.canvasRef) return;
    const ctx = this.canvasRef.nativeElement.getContext('2d')!;
    ctx.clearRect(0, 0, this.displayW(), this.displayH());
    for (const s of this.getSlices()) {
      this.drawSlice(ctx, s, s.id === this.selectedId());
    }
  }

  private redrawWithGhost(x1: number, y1: number, x2: number, y2: number): void {
    this.redraw();
    const ctx = this.canvasRef.nativeElement.getContext('2d')!;
    const b = this.normBbox(x1, y1, x2, y2);
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 3]);
    ctx.strokeRect(b.x, b.y, b.width, b.height);
    ctx.setLineDash([]);
  }

  private drawSlice(ctx: CanvasRenderingContext2D, s: Slice, selected: boolean): void {
    const d = this.toDisplay(s.bbox);
    const color = s.type === '#' ? '#3b82f6' : '#f59e0b';
    ctx.strokeStyle = color;
    ctx.lineWidth = selected ? 2 : 1.5;
    ctx.setLineDash(selected ? [] : [5, 3]);
    ctx.strokeRect(d.x + 0.5, d.y + 0.5, d.width, d.height);
    ctx.setLineDash([]);

    // Fill with low-opacity background
    ctx.fillStyle = s.type === '#' ? 'rgba(59,130,246,0.08)' : 'rgba(245,158,11,0.08)';
    ctx.fillRect(d.x, d.y, d.width, d.height);

    // Order badge
    const badgeW = 20;
    const badgeH = 18;
    ctx.fillStyle = color;
    ctx.fillRect(d.x, d.y, badgeW, badgeH);
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(s.order), d.x + badgeW / 2, d.y + badgeH / 2);

    // Type label next to badge
    ctx.fillStyle = color;
    ctx.fillRect(d.x + badgeW, d.y, 16, badgeH);
    ctx.fillStyle = '#fff';
    ctx.fillText(s.type, d.x + badgeW + 8, d.y + badgeH / 2);

    // Resize handles on selected
    if (selected) {
      const corners = [
        { x: d.x, y: d.y },
        { x: d.x + d.width, y: d.y },
        { x: d.x, y: d.y + d.height },
        { x: d.x + d.width, y: d.y + d.height },
      ];
      ctx.fillStyle = '#fff';
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      for (const c of corners) {
        ctx.fillRect(c.x - HANDLE_SIZE / 2, c.y - HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE);
        ctx.strokeRect(c.x - HANDLE_SIZE / 2, c.y - HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE);
      }
    }
  }

  // ── Remove page ──────────────────────────────────────────────────────────

  removePage(index: number): void {
    const updated = [...this.pages()];
    if (updated.length <= 1) return;
    const removed = updated.splice(index, 1)[0];
    const m = new Map(this.allSlices());
    m.delete(removed.id);
    this.allSlices.set(m);
    this.pages.set(updated);
    const newIndex = Math.min(index, updated.length - 1);
    this.currentIndex.set(newIndex);
    this.loadingImage.set(true);
  }

  // ── Slice drag-and-drop reorder ───────────────────────────────────────────

  dragSliceSourceIdx = signal<number | null>(null);
  dragSliceOverIdx = signal<number | null>(null);

  onSliceDragStart(idx: number): void {
    this.dragSliceSourceIdx.set(idx);
  }

  onSliceDragOver(e: DragEvent, idx: number): void {
    e.preventDefault();
    this.dragSliceOverIdx.set(idx);
  }

  onSliceDrop(idx: number): void {
    const from = this.dragSliceSourceIdx();
    this.dragSliceSourceIdx.set(null);
    this.dragSliceOverIdx.set(null);
    if (from === null || from === idx) return;
    const slices = [...this.getSlices()];
    const [moved] = slices.splice(from, 1);
    slices.splice(idx, 0, moved);
    this.renumber(slices);
    this.setSlices(slices);
    this.selectedId.set(moved.id);
    this.redraw();
  }

  onSliceDragEnd(): void {
    this.dragSliceSourceIdx.set(null);
    this.dragSliceOverIdx.set(null);
  }

  // ── Suggest regions ───────────────────────────────────────────────────────

  suggesting = signal(false);

  suggestRegions(): void {
    const p = this.currentPage();
    if (!p || this.suggesting()) return;
    this.suggesting.set(true);
    this.pagesApi.detect(p.id).subscribe({
      next: out => {
        const existing = this.getSlices();
        const startOrder = existing.length + 1;
        const newSlices: Slice[] = out.regions.map((r, i) => ({
          id: `suggest-${Date.now()}-${i}`,
          order: startOrder + i,
          type: '#' as SliceType,
          bbox: r.bbox,
        }));
        this.setSlices([...existing, ...newSlices]);
        this.nextOrder.set(startOrder + newSlices.length);
        this.suggesting.set(false);
        this.redraw();
      },
      error: () => this.suggesting.set(false),
    });
  }

  // ── Process all ───────────────────────────────────────────────────────────

  processAll(): void {
    if (!this.canProcess()) return;
    this.processing.set(true);

    const annotationsPages = this.pages().map(p => ({
      page_id: p.id,
      regions: (this.allSlices().get(p.id) ?? []).map(s => ({
        order: s.order,
        type: s.type,
        bbox: s.bbox,
      } satisfies import('../../core/api/models').AnnotationRegion)),
    }));

    this.foldersApi.annotate(this.folderId, { pages: annotationsPages }).subscribe({
      next: () => {
        this.notifications.add(
          'Anotações enviadas',
          `${this.pages().length} página(s) enviada(s) para processamento`,
          'success',
        );
        this.router.navigate(['/pastas', this.folderId]);
      },
      error: () => {
        this.notifications.add('Erro', 'Falha ao enviar anotações', 'error');
        this.processing.set(false);
      },
    });
  }
}
