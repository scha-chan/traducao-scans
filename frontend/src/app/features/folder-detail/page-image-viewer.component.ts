import {
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  ViewChild,
  computed,
  input,
  signal,
} from '@angular/core';
import { NgStyle } from '@angular/common';
import { TextBlockExport } from '../../core/api/models';

const ZOOM_MIN = 0.25;
const ZOOM_MAX = 8;
const ZOOM_STEP = 0.25;
const ZOOM_WHEEL_FACTOR = 0.001;

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
  /** Índice selecionado na lista (seleção bidirecional — bbox quando disponível). */
  readonly selectedBlockIndex = input<number | null>(null);

  readonly imageLoading = signal(true);
  readonly zoom = signal(1);
  readonly panX = signal(0);
  readonly panY = signal(0);

  private isDragging = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private dragStartPanX = 0;
  private dragStartPanY = 0;

  @ViewChild('container') containerRef!: ElementRef<HTMLElement>;

  readonly transform = computed(
    () =>
      `scale(${this.zoom()}) translate(${this.panX() / this.zoom()}px, ${this.panY() / this.zoom()}px)`,
  );

  readonly cursorClass = computed(() => {
    if (this.zoom() <= 1) return 'cursor-default';
    return this.isDragging ? 'cursor-grabbing' : 'cursor-grab';
  });

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
  // Pan (drag)
  // -------------------------------------------------------------------------

  onMouseDown(e: MouseEvent) {
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
    if (!this.isDragging) return;
    this.panX.set(this.dragStartPanX + (e.clientX - this.dragStartX));
    this.panY.set(this.dragStartPanY + (e.clientY - this.dragStartY));
  }

  @HostListener('document:mouseup')
  onMouseUp() {
    this.isDragging = false;
  }

  ngOnDestroy() {
    this.isDragging = false;
  }
}
