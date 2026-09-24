import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AppHeaderComponent } from './core/layout/app-header.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, AppHeaderComponent],
  template: `
    <div class="bg-zinc-50 dark:bg-zinc-950 min-h-dvh">
      <app-header />
      <main class="mx-auto max-w-7xl px-4 md:px-6 py-6">
        <router-outlet />
      </main>
    </div>
  `,
})
export class App {}
