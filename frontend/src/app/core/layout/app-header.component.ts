import { Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink],
  template: `
    <header class="sticky top-0 z-30 h-14 flex items-center justify-between px-4 md:px-6 bg-white/90 backdrop-blur border-b border-zinc-200 dark:bg-zinc-900/90 dark:border-zinc-800">
      <a routerLink="/" class="flex items-center gap-2 text-zinc-900 dark:text-zinc-100 font-semibold text-lg no-underline">
        <svg xmlns="http://www.w3.org/2000/svg" class="size-6 text-primary-600" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2Zm-7 3a5 5 0 1 1 0 10A5 5 0 0 1 12 6Zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"/>
        </svg>
        <span>Manga Translator</span>
      </a>

      <a
        routerLink="/nova-traducao"
        [class.opacity-50]="processing()"
        [class.pointer-events-none]="processing()"
        [attr.aria-disabled]="processing() || null"
        [title]="processing() ? 'Processamento em andamento' : null"
        class="inline-flex items-center gap-2 rounded-lg px-4 py-2 bg-primary-600 hover:bg-primary-700 active:bg-primary-800 text-white font-medium focus-visible:outline-none focus-visible:ring-2 ring-primary-500 ring-offset-2 transition-colors text-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 5v14M5 12h14"/>
        </svg>
        Nova tradução
      </a>
    </header>
  `,
})
export class AppHeaderComponent {
  readonly processing = signal(false);
}
