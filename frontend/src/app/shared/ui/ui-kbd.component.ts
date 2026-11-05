import { Component, input } from '@angular/core';

export interface KbdShortcut {
  keys: string[];
  label: string;
}

@Component({
  selector: 'ui-kbd',
  standalone: true,
  template: `
    <span class="inline-flex items-center gap-1">
      @for (key of keys(); track key) {
        <kbd
          class="inline-flex items-center justify-center rounded border border-zinc-300 bg-zinc-100 px-1.5 py-0.5 font-mono text-xs font-medium text-zinc-700 shadow-[0_1px_0_0] shadow-zinc-300 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 dark:shadow-zinc-600"
        >{{ key }}</kbd>
      }
    </span>
  `,
})
export class UiKbdComponent {
  keys = input.required<string[]>();
}

@Component({
  selector: 'ui-kbd-legend',
  standalone: true,
  imports: [UiKbdComponent],
  template: `
    <span class="inline-flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-400 dark:text-zinc-500">
      @for (shortcut of shortcuts(); track shortcut.label) {
        <span class="inline-flex items-center gap-1">
          <ui-kbd [keys]="shortcut.keys" />
          <span>{{ shortcut.label }}</span>
        </span>
      }
    </span>
  `,
})
export class UiKbdLegendComponent {
  shortcuts = input.required<KbdShortcut[]>();
}
