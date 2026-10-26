import {
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  ViewChild,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { NgStyle } from '@angular/common';
import { BboxPx, TextBlockExport } from '../../core/api/models';

const ZOOM_MIN = 0.25;
const ZOOM_MAX = 8;
const ZOOM_STEP = 0.25;
const ZOOM_WHEEL_FACTOR = 0.001;
const MIN_DRAW_PX = 10;

@Component({
  selector: 'app-page-image-viewer',
  standalone: true,
  imports: [NgStyle],
  templateUrl: './page-image-viewer.component.html',
  styleUrl: './page-image-viewer.component.scss',
})
export class PageImageViewerComponent implements OnDestroy {
  readonly ZOOM_MIN = ZOOM_MIN;
  readonly ZOOM_MAX = ZOOM_MAX;

  readonly imageUrl = input.required<string>();
  readonly altText = input<string>('Página');
  readonly blocks = input<TextBlockExport[]>([]);
  readonly selectedBlockIndex = input<number | null>(null);

  readonly regionDrawn = output<BboxPx>();
  readonly regionTooSmall = output<void>();
  readonly drawModeChange = output<boolean>();

  readonly imageLoading = signal(true);
  readonly zoom = signal(1);
  readonly panX = signal(0);
  readonly panY = signal(0);

  readonly drawModeActive = signal(false);
  readonly isDrawing = signal(false);
  readonly drawPreviewRect = signal<BboxPx | null>(null);

  private drawStartSvg = {x: 0, y: 0};
  private isDragging = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private dragStartPanX = 0;
  private dragStartPanY = 0;

  @ViewChild('container') containerRef!: ElementRef<HTMLElement>;
  @ViewChild('pageImage') imageRef!: ElementRef<HTMLImageElement>;

  readonly transform = computed(
    () =>
      `scale(${this.zoom()}) translate(${this.panX() / this.zoom()}px, ${this.panY() / this.zoom()}px)`,
  );

  readonly cursorClass = computed(() => {
    if (this.drawModeActive()) return 'cursor-crosshair';
    if (this.zoom() <= 1) return 'cursor-default';
    return this.isDragging ? 'cursor-grabbing' : 'cursor-grab';
  });

  // -------------------------------------------------------------------------
  // Draw mode
  // -------------------------------------------------------------------------

  toggleDrawMode() {
    const next = !this.drawModeActive();
    this.drawModeActive.set(next);
    this.isDrawing.set(false);
    this.drawPreviewRect.set(null);
    this.drawModeChange.emit(next);
  }

  // -------------------------------------------------------------------------
  // Zoom controls
  // -------------------------------------------------------------------------

  zoomIn() {
    this.zoom.update((z) => Math.min(ZOOM_MAX, +(z + ZOOM_STEP).toFixed(2)));
  }

  zoomOut() {
    this.zoom.update((z) => {
      const next = Math.max(ZOOM_MIN, +(z - ZOOM_STEP).toFixed(2));
      if (next <= 1) this.resetPan();
      return next;
    });
  }

  resetZoom() {
    this.zoom.set(1);
    this.resetPan();
  }

  private resetPan() {
    this.panX.set(0);
    this.panY.set(0);
  }

  // -------------------------------------------------------------------------
  // Ctrl + wheel zoom
  // -------------------------------------------------------------------------

  @HostListener('wheel', ['$event'])
  onWheel(e: WheelEvent) {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    const delta = -e.deltaY * ZOOM_WHEEL_FACTOR * this.zoom();
    this.zoom.update((z) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, +(z + delta).toFixed(3))));
    if (this.zoom() <= 1) this.resetPan();
  }

  // -------------------------------------------------------------------------
  // Escape: cancel draw mode
  // -------------------------------------------------------------------------

  @HostListener('document:keydown', ['$event'])
  onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape' && this.drawModeActive()) {
      e.stopPropagation();
      this.drawModeActive.set(false);
      this.isDrawing.set(false);
      this.drawPreviewRect.set(null);
      this.drawModeChange.emit(false);
    }
  }

  // -------------------------------------------------------------------------
  // Mouse: draw or pan
  // -------------------------------------------------------------------------

  onMouseDown(e: MouseEvent) {
    if (this.drawModeActive()) {
      const svgPos = this.clientToSvgCoords(e.clientX, e.clientY);
      if (!svgPos) return;
      this.isDrawing.set(true);
      this.drawStartSvg = svgPos;
      this.drawPreviewRect.set({x: svgPos.x, y: svgPos.y, w: 0, h: 0});
      e.preventDefault();
      return;
    }
    if (this.zoom() <= 1) return;
    this.isDragging = true;
    this.dragStartX = e.clientX;
    this.dragStartY = e.clientY;
    this.dragStartPanX = this.panX();
    this.dragStartPanY = this.panY();
    e.preventDefault();
  }

  @HostListener('document:mousemove', ['$event'])
  onMouseMove(e: MouseEvent) {
    if (this.drawModeActive() && this.isDrawing()) {
      const svgPos = this.clientToSvgCoords(e.clientX, e.clientY);
      if (!svgPos) return;
      const x = Math.min(this.drawStartSvg.x, svgPos.x);
      const y = Math.min(this.drawStartSvg.y, svgPos.y);
      const w = Math.abs(svgPos.x - this.drawStartSvg.x);
      const h = Math.abs(svgPos.y - this.drawStartSvg.y);
      this.drawPreviewRect.set({x, y, w, h});
      return;
    }
    if (!this.isDragging) return;
    this.panX.set(this.dragStartPanX + (e.clientX - this.dragStartX));
    this.panY.set(this.dragStartPanY + (e.clientY - this.dragStartY));
  }

  @HostListener('document:mouseup')
  onMouseUp() {
    if (this.drawModeActive() && this.isDrawing()) {
      this.isDrawing.set(false);
      const rect = this.drawPreviewRect();
      this.drawPreviewRect.set(null);
      if (!rect) return;
      const orig = this.svgRectToOriginalPx(rect);
      if (orig.w < MIN_DRAW_PX || orig.h < MIN_DRAW_PX) {
        this.regionTooSmall.emit();
        return;
      }
      this.regionDrawn.emit(orig);
      this.drawModeActive.set(false);
      this.drawModeChange.emit(false);
      return;
    }
    this.isDragging = false;
  }

  ngOnDestroy() {
    this.isDragging = false;
    this.isDrawing.set(false);
  }

  // -------------------------------------------------------------------------
  // Coordinate helpers
  // -------------------------------------------------------------------------

  /** Converts viewport coords to image-local SVG pixel coords (pre-zoom). */
  private clientToSvgCoords(clientX: number, clientY: number): {x: number; y: number} | null {
    const img = this.imageRef?.nativeElement;
    if (!img) return null;
    const rect = img.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return null;
    const scaleX = img.offsetWidth / rect.width;
    const scaleY = img.offsetHeight / rect.height;
    const x = Math.max(0, Math.min((clientX - rect.left) * scaleX, img.offsetWidth));
    const y = Math.max(0, Math.min((clientY - rect.top) * scaleY, img.offsetHeight));
    return {x, y};
  }

  /** Converts SVG-pixel rect to original image pixel coordinates. */
  private svgRectToOriginalPx(r: BboxPx): BboxPx {
    const img = this.imageRef?.nativeElement;
    if (!img || img.offsetWidth === 0 || img.offsetHeight === 0) return r;
    const sx = img.naturalWidth / img.offsetWidth;
    const sy = img.naturalHeight / img.offsetHeight;
    return {
      x: Math.round(r.x * sx),
      y: Math.round(r.y * sy),
      w: Math.round(r.w * sx),
      h: Math.round(r.h * sy),
    };
  }
}
