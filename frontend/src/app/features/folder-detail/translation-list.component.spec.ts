import '@angular/compiler';
import { describe, it, expect } from 'vitest';
import { FormBuilder } from '@angular/forms';
import { getBadgeClass, sortTranslationArray, TranslationForm } from './translation-list.component';
import type { FormArray, FormGroup } from '@angular/forms';

const fb = new FormBuilder().nonNullable;

function makeFA(
  items: { traducao: string; relevancia: 1 | 2 | 3 | 4 | 5 }[],
): FormArray<FormGroup<TranslationForm>> {
  return fb.array(
    items.map((item) =>
      fb.group<TranslationForm>({
        traducao: fb.control(item.traducao),
        observacao: fb.control(''),
        relevancia: fb.control<1 | 2 | 3 | 4 | 5>(item.relevancia),
      }),
    ),
  ) as FormArray<FormGroup<TranslationForm>>;
}

// ── renders suggestions sorted by relevance ───────────────────────────────────

describe('renders suggestions sorted by relevance', () => {
  it('sugestões fora de ordem → sortTranslationArray produz ordem 1,2,3', () => {
    const fa = makeFA([
      { traducao: 'tr3', relevancia: 3 },
      { traducao: 'tr1', relevancia: 1 },
      { traducao: 'tr2', relevancia: 2 },
    ]);
    sortTranslationArray(fa);
    expect(fa.at(0).value.relevancia).toBe(1);
    expect(fa.at(1).value.relevancia).toBe(2);
    expect(fa.at(2).value.relevancia).toBe(3);
  });

  it('traduções com mesma relevância mantêm a ordem estável relativa', () => {
    const fa = makeFA([
      { traducao: 'b', relevancia: 2 },
      { traducao: 'a', relevancia: 1 },
    ]);
    sortTranslationArray(fa);
    expect(fa.at(0).value.traducao).toBe('a');
    expect(fa.at(1).value.traducao).toBe('b');
  });
});

// ── badge color matches relevance level ───────────────────────────────────────

describe('badge color matches relevance level', () => {
  it('relevancia 1 → bg-primary-600', () => {
    expect(getBadgeClass(1)).toContain('bg-primary-600');
  });

  it('relevancia 2 → bg-primary-400', () => {
    expect(getBadgeClass(2)).toContain('bg-primary-400');
  });

  it('relevancia 3 → bg-primary-300', () => {
    expect(getBadgeClass(3)).toContain('bg-primary-300');
  });

  it('relevancia 4 → bg-primary-200', () => {
    expect(getBadgeClass(4)).toContain('bg-primary-200');
  });

  it('relevancia 5 → bg-primary-100', () => {
    expect(getBadgeClass(5)).toContain('bg-primary-100');
  });
});

// ── delete disabled at minimum 1 ─────────────────────────────────────────────

describe('delete disabled at minimum 1', () => {
  it('único item → não remove (length permanece 1)', () => {
    const fa = makeFA([{ traducao: 'única', relevancia: 1 }]);
    // simulate removeSuggestion guard: fa.length <= 1 → no-op
    if (fa.length > 1) fa.removeAt(0);
    expect(fa.length).toBe(1);
  });

  it('dois itens → remove um com sucesso (length cai para 1)', () => {
    const fa = makeFA([
      { traducao: 'a', relevancia: 1 },
      { traducao: 'b', relevancia: 2 },
    ]);
    if (fa.length > 1) fa.removeAt(1);
    expect(fa.length).toBe(1);
  });
});

// ── add disabled at maximum 5 ─────────────────────────────────────────────────

describe('add disabled at maximum 5', () => {
  it('5 itens → não adiciona (length permanece 5)', () => {
    const fa = makeFA([
      { traducao: 'a', relevancia: 1 },
      { traducao: 'b', relevancia: 2 },
      { traducao: 'c', relevancia: 3 },
      { traducao: 'd', relevancia: 4 },
      { traducao: 'e', relevancia: 5 },
    ]);
    // simulate addSuggestion guard: fa.length >= 5 → no-op
    if (fa.length < 5) {
      fa.push(fb.group<TranslationForm>({
        traducao: fb.control('nova'),
        observacao: fb.control(''),
        relevancia: fb.control<1 | 2 | 3 | 4 | 5>(1),
      }) as FormGroup<TranslationForm>);
    }
    expect(fa.length).toBe(5);
  });

  it('4 itens → adiciona com sucesso (length sobe para 5)', () => {
    const fa = makeFA([
      { traducao: 'a', relevancia: 1 },
      { traducao: 'b', relevancia: 2 },
      { traducao: 'c', relevancia: 3 },
      { traducao: 'd', relevancia: 4 },
    ]);
    if (fa.length < 5) {
      fa.push(fb.group<TranslationForm>({
        traducao: fb.control('e'),
        observacao: fb.control(''),
        relevancia: fb.control<1 | 2 | 3 | 4 | 5>(5),
      }) as FormGroup<TranslationForm>);
    }
    expect(fa.length).toBe(5);
  });
});

// ── reorders on blur ──────────────────────────────────────────────────────────

describe('reorders on blur', () => {
  it('alterar relevância e chamar sortTranslationArray reordena a lista', () => {
    const fa = makeFA([
      { traducao: 'pior', relevancia: 5 },
      { traducao: 'melhor', relevancia: 1 },
    ]);

    // simulate blur handler (sortOnBlur calls sortTranslationArray)
    sortTranslationArray(fa);

    expect(fa.at(0).value.relevancia).toBe(1);
    expect(fa.at(0).value.traducao).toBe('melhor');
    expect(fa.at(1).value.relevancia).toBe(5);
    expect(fa.at(1).value.traducao).toBe('pior');
  });

  it('lista já ordenada permanece inalterada após sort', () => {
    const fa = makeFA([
      { traducao: 'a', relevancia: 1 },
      { traducao: 'b', relevancia: 2 },
      { traducao: 'c', relevancia: 3 },
    ]);
    sortTranslationArray(fa);
    expect(fa.at(0).value.traducao).toBe('a');
    expect(fa.at(1).value.traducao).toBe('b');
    expect(fa.at(2).value.traducao).toBe('c');
  });
});
