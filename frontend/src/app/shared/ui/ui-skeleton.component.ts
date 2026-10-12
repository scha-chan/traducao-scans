import { Component, input } from '@angular/core';

@Component({
  selector: 'ui-skeleton',
  standalone: true,
  template: `
    <div
      class="animate-pulse rounded-md bg-zinc-200 dark:bg-zinc-700"
      [class]="heightClass() + ' ' + widthClass()"
      aria-hidden="true"
    ></div>
  `,
})
export class UiSkeletonComponent {
  readonly height = input('h-4');
  readonly width = input('w-full');

  readonly heightClass = this.height;
  readonly widthClass = this.width;
}

@Component({
  selector: 'ui-skeleton-rows',
  standalone: true,
  imports: [UiSkeletonComponent],
  template: `
    <div class="flex flex-col gap-3" aria-busy="true" aria-label="Carregando...">
      @for (_ of rows(); track $index) {
        <ui-skeleton height="h-10" />
      }
    </div>
  `,
})
export class UiSkeletonRowsComponent {
  readonly count = input(5);
  readonly rows = () => Array.from({ length: this.count() });
}
