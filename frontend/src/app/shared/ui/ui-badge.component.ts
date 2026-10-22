import { Component, input, computed } from '@angular/core';

export type BadgeStatus = 'DONE' | 'DONE_WITH_ERRORS' | 'INCOMPLETE' | 'PROCESSING';

const STATUS_CONFIG: Record<BadgeStatus, { label: string; classes: string; icon: string }> = {
  DONE: {
    label: 'Concluída',
    classes: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
    icon: `<svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>`,
  },
  DONE_WITH_ERRORS: {
    label: 'Com erros',
    classes: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    icon: `<svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  },
  INCOMPLETE: {
    label: 'Incompleta',
    classes: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
    icon: `<svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  },
  PROCESSING: {
    label: 'Processando',
    classes: 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300',
    icon: `<svg class="size-3.5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>`,
  },
};

@Component({
  selector: 'ui-badge',
  standalone: true,
  templateUrl: './ui-badge.component.html',
  styleUrl: './ui-badge.component.scss',
})
export class UiBadgeComponent {
  readonly status = input.required<BadgeStatus>();
  readonly config = computed(() => STATUS_CONFIG[this.status()]);
}
