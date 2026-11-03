import {
  Component,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import {
  FormArray,
  FormControl,
  FormGroup,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { NgClass } from '@angular/common';

export interface TranslationForm {
  traducao: FormControl<string>;
  observacao: FormControl<string>;
  relevancia: FormControl<1 | 2 | 3 | 4 | 5>;
}

interface TranslationValue {
  traducao: string;
  observacao: string;
  relevancia: 1 | 2 | 3 | 4 | 5;
}

export function getBadgeClass(relevance: number): string {
  const map: Record<number, string> = {
    1: 'bg-primary-600 text-white',
    2: 'bg-primary-400 text-white',
    3: 'bg-primary-300 text-zinc-700',
    4: 'bg-primary-200 text-zinc-700',
    5: 'bg-primary-100 text-zinc-700',
  };
  return map[relevance] ?? 'bg-zinc-200 text-zinc-700';
}

export function sortTranslationArray(fa: FormArray<FormGroup<TranslationForm>>): void {
  const values = fa.controls.map((c) => ({ ...c.value })) as TranslationValue[];
  const sorted = [...values].sort((a, b) => a.relevancia - b.relevancia);
  sorted.forEach((v, idx) => fa.at(idx).setValue(v as never, { emitEvent: false }));
}

@Component({
  selector: 'app-translation-list',
  standalone: true,
  imports: [ReactiveFormsModule, NgClass],
  template: `
<div class="space-y-2">
  @for (ctrl of sortedControls(); track ctrl; let i = $index) {
    <div class="flex gap-1.5 items-start" [formGroup]="ctrl">
      <span
        class="inline-flex items-center justify-center min-w-[1.25rem] h-5 rounded px-1 text-[10px] font-bold flex-shrink-0 mt-0.5 tabular-nums leading-none"
        [ngClass]="getBadgeClass(ctrl.controls.relevancia.value)"
        aria-hidden="true"
      >{{ ctrl.controls.relevancia.value }}</span>

      <textarea
        formControlName="traducao"
        class="field-textarea flex-1 min-w-0"
        placeholder="Tradução..."
        rows="1"
        (blur)="sortOnBlur()"
        [attr.aria-label]="'Tradução ' + (i + 1)"
        [class.border-primary-600]="ctrl.controls.traducao.invalid && ctrl.controls.traducao.touched"
      ></textarea>

      <input
        formControlName="observacao"
        class="field-input w-24 flex-shrink-0"
        placeholder="Observação opcional"
        [attr.aria-label]="'Observação ' + (i + 1)"
      />

      <button
        type="button"
        class="icon-btn text-zinc-400 hover:text-red-500 dark:hover:text-red-400 flex-shrink-0 mt-0.5 disabled:opacity-30 disabled:cursor-not-allowed"
        [disabled]="control().length <= 1"
        (click)="removeSuggestion(ctrl)"
        [attr.aria-label]="'Remover sugestão ' + (i + 1)"
      >
        <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
        </svg>
      </button>
    </div>
  }

  <button
    type="button"
    class="text-xs text-primary-600 dark:text-primary-400 hover:underline focus-visible:outline-none focus-visible:ring-2 ring-primary-500 ring-offset-1 rounded disabled:opacity-40 disabled:cursor-not-allowed"
    [disabled]="control().length >= 5"
    (click)="addSuggestion()"
    aria-label="Adicionar sugestão de tradução"
  >+ Adicionar sugestão</button>
</div>
  `,
})
export class TranslationListComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly sortTick = signal(0);

  readonly control = input.required<FormArray<FormGroup<TranslationForm>>>();

  readonly getBadgeClass = getBadgeClass;

  readonly sortedControls = computed(() => {
    this.sortTick();
    const fa = this.control();
    return [...fa.controls].sort(
      (a, b) => a.controls.relevancia.value - b.controls.relevancia.value,
    );
  });

  sortOnBlur(): void {
    sortTranslationArray(this.control());
    this.sortTick.update((v) => v + 1);
  }

  addSuggestion(): void {
    const fa = this.control();
    if (fa.length >= 5) return;
    fa.push(
      this.fb.group<TranslationForm>({
        traducao: this.fb.control('', Validators.required),
        observacao: this.fb.control(''),
        relevancia: this.fb.control<1 | 2 | 3 | 4 | 5>(1),
      }),
    );
    this.sortTick.update((v) => v + 1);
  }

  removeSuggestion(ctrl: FormGroup<TranslationForm>): void {
    const fa = this.control();
    if (fa.length <= 1) return;
    const i = fa.controls.indexOf(ctrl);
    if (i >= 0) fa.removeAt(i);
    this.sortTick.update((v) => v + 1);
  }
}
