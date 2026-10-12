import {
  Component,
  input,
  output,
  effect,
  ElementRef,
  inject,
  OnDestroy,
} from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'ui-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (open()) {
      <div
        class="fixed inset-0 z-50 bg-zinc-950/60 backdrop-blur-sm flex items-center justify-center p-4"
        role="presentation"
      >
        <div
          #panel
          role="dialog"
          aria-modal="true"
          [attr.aria-labelledby]="labelId"
          [class]="'relative flex flex-col rounded-xl bg-white dark:bg-zinc-900 shadow-2xl outline-none ' + panelClass()"
        >
          <ng-content />
        </div>
      </div>
    }
  `,
})
export class UiDialogComponent implements OnDestroy {
  readonly open = input(false);
  readonly panelClass = input('w-[95vw] max-w-lg');
  readonly labelId = 'ui-dialog-title-' + Math.random().toString(36).slice(2);
  readonly closed = output<void>();

  private readonly el = inject(ElementRef);
  private previousFocus: HTMLElement | null = null;
  private keydownHandler = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      this.closed.emit();
    }
    if (e.key === 'Tab') {
      this.trapFocus(e);
    }
  };

  constructor() {
    effect(() => {
      if (this.open()) {
        this.previousFocus = document.activeElement as HTMLElement;
        setTimeout(() => this.focusFirst(), 0);
        document.addEventListener('keydown', this.keydownHandler);
      } else {
        document.removeEventListener('keydown', this.keydownHandler);
        this.previousFocus?.focus();
      }
    });
  }

  ngOnDestroy() {
    document.removeEventListener('keydown', this.keydownHandler);
  }

  private focusFirst() {
    const panel = this.el.nativeElement.querySelector('[role="dialog"]');
    if (!panel) return;
    const focusable = this.getFocusable(panel);
    focusable[0]?.focus();
  }

  private trapFocus(e: KeyboardEvent) {
    const panel = this.el.nativeElement.querySelector('[role="dialog"]');
    if (!panel) return;
    const focusable = this.getFocusable(panel);
    if (!focusable.length) return;
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

  private getFocusable(container: HTMLElement): HTMLElement[] {
    return Array.from(
      container.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => !el.closest('[hidden]'));
  }
}
