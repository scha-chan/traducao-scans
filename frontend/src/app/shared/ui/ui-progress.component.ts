import { Component, input, computed } from '@angular/core';

@Component({
  selector: 'ui-progress',
  standalone: true,
  template: `
    <div class="flex flex-col gap-1.5">
      @if (label()) {
        <div
          class="flex justify-between text-sm font-medium tabular-nums text-zinc-700 dark:text-zinc-300"
          aria-live="polite"
        >
          <span>{{ label() }}</span>
          @if (sublabel()) {
            <span class="text-zinc-500 dark:text-zinc-400">{{ sublabel() }}</span>
          }
        </div>
      }
      <div
        role="progressbar"
        [attr.aria-valuenow]="value()"
        [attr.aria-valuemin]="0"
        [attr.aria-valuemax]="max()"
        [attr.aria-label]="ariaLabel()"
        class="h-3 w-full rounded-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden"
      >
        <div
          class="h-full rounded-full bg-primary-600 transition-[width] duration-300 ease-in-out"
          [style.width.%]="percent()"
        ></div>
      </div>
    </div>
  `,
})
export class UiProgressComponent {
  readonly value = input(0);
  readonly max = input(100);
  readonly label = input('');
  readonly sublabel = input('');
  readonly ariaLabel = input('Progresso');

  readonly percent = computed(() =>
    this.max() > 0 ? Math.min(100, (this.value() / this.max()) * 100) : 0
  );
}
