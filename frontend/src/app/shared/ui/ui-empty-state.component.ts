import { Component, input } from '@angular/core';

@Component({
  selector: 'ui-empty-state',
  standalone: true,
  template: `
    <div class="flex flex-col items-center justify-center gap-6 py-16 text-center">
      <div class="rounded-full bg-zinc-100 dark:bg-zinc-800 p-5">
        @if (icon() === 'folder') {
          <svg class="size-12 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
          </svg>
        } @else if (icon() === 'search') {
          <svg class="size-12 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
        } @else {
          <svg class="size-12 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        }
      </div>

      <div class="flex flex-col gap-2 max-w-sm">
        <h3 class="text-base font-semibold text-zinc-900 dark:text-zinc-100">{{ title() }}</h3>
        @if (description()) {
          <p class="text-sm text-zinc-500 dark:text-zinc-400">{{ description() }}</p>
        }
      </div>

      <ng-content />
    </div>
  `,
})
export class UiEmptyStateComponent {
  readonly icon = input<'folder' | 'search' | 'info'>('folder');
  readonly title = input('Nenhum item encontrado');
  readonly description = input('');
}
