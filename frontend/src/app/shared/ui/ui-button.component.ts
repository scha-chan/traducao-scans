import { Component, input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'destructive';
export type ButtonSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'ui-button',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-button.component.html',
  styleUrl: './ui-button.component.scss',
})
export class UiButtonComponent {
  readonly variant = input<ButtonVariant>('primary');
  readonly size = input<ButtonSize>('md');
  readonly loading = input(false);
  readonly disabled = input(false);
  readonly type = input<'button' | 'submit' | 'reset'>('button');

  readonly classes = computed(() => {
    const base =
      'inline-flex items-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';

    const variants: Record<ButtonVariant, string> = {
      primary:
        'bg-primary-600 hover:bg-primary-700 active:bg-primary-800 text-white ring-primary-500',
      secondary:
        'border border-primary-600 text-primary-700 hover:bg-primary-50 dark:border-primary-400 dark:text-primary-300 dark:hover:bg-primary-950 ring-primary-500',
      ghost:
        'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800 ring-zinc-400',
      destructive:
        'bg-red-600 hover:bg-red-700 active:bg-red-800 text-white ring-red-500',
    };

    const sizes: Record<ButtonSize, string> = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-sm',
      lg: 'px-5 py-2.5 text-base',
    };

    return [base, variants[this.variant()], sizes[this.size()]].join(' ');
  });
}
