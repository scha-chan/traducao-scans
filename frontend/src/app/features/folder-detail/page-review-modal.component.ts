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
import { FolderDetail, PageSummary } from '../../core/api/models';
import { PagesApi } from '../../core/api/pages.api';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

@Component({
  selector: 'app-page-review-modal',
  standalone: true,
  imports: [UiButtonComponent],
  templateUrl: './page-review-modal.component.html',
  styleUrl: './page-review-modal.component.scss',
})
export class PageReviewModalComponent implements OnInit, OnDestroy {
  private readonly pagesApi = inject(PagesApi);

  readonly folder = input.required<FolderDetail>();
  readonly page = input.required<PageSummary>();

  readonly closed = output<void>();
  readonly navigated = output<number>();

  readonly imageLoading = signal(true);

  @ViewChild('panel') panelRef!: ElementRef<HTMLElement>;

  readonly hasPrev = computed(() => this.page().page_number > 1);
  readonly hasNext = computed(() => this.page().page_number < this.folder().pages.length);

  readonly imageUrl = computed(() => this.pagesApi.imageUrl(this.page()));

  private previousActiveElement: Element | null = null;

  ngOnInit() {
    this.previousActiveElement = document.activeElement;
    document.body.style.overflow = 'hidden';
    setTimeout(() => this.focusFirst(), 0);
  }

  ngOnDestroy() {
    document.body.style.overflow = '';
    (this.previousActiveElement as HTMLElement | null)?.focus();
  }

  close() {
    this.closed.emit();
  }

  navigate(direction: -1 | 1) {
    const current = this.page().page_number;
    const target = current + direction;
    const targetPage = this.folder().pages.find((p) => p.page_number === target);
    if (targetPage) {
      this.imageLoading.set(true);
      this.navigated.emit(target);
    }
  }

  @HostListener('keydown', ['$event'])
  onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      this.close();
      return;
    }

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
    }

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
