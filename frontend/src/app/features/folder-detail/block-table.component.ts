import {
  Component,
  OnChanges,
  SimpleChanges,
  input,
  output,
  signal,
  inject,
} from '@angular/core';
import {
  ReactiveFormsModule,
  FormArray,
  FormControl,
  FormGroup,
  NonNullableFormBuilder,
  Validators,
} from '@angular/forms';
import { BboxPx, TextBlockExport, Translation } from '../../core/api/models';
import { UiDialogComponent } from '../../shared/ui/ui-dialog.component';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';

interface TranslationForm {
  traducao: FormControl<string>;
  observacao: FormControl<string>;
  relevancia: FormControl<1 | 2 | 3 | 4 | 5>;
}

interface BlockForm {
  tipo: FormControl<'#' | '$'>;
  original: FormControl<string>;
  localizacao: FormControl<string>;
  traducoes: FormArray<FormGroup<TranslationForm>>;
  bbox: FormControl<BboxPx | null>;
}

@Component({
  selector: 'app-block-table',
  standalone: true,
  imports: [ReactiveFormsModule, UiDialogComponent, UiButtonComponent],
  templateUrl: './block-table.component.html',
  styleUrl: './block-table.component.scss',
})
export class BlockTableComponent implements OnChanges {
  private readonly fb = inject(NonNullableFormBuilder);

  readonly blocks = input.required<TextBlockExport[]>();
  readonly loading = input<boolean>(false);

  readonly selectedIndex = signal<number | null>(null);
  readonly form = this.fb.array<FormGroup<BlockForm>>([]);

  readonly selectedIndexChange = output<number | null>();

  readonly RELEVANCE_OPTIONS: (1 | 2 | 3 | 4 | 5)[] = [1, 2, 3, 4, 5];

  private deleteConfirmOpen = signal(false);
  private blockToDelete = signal<number | null>(null);
  readonly showDeleteDialog = this.deleteConfirmOpen.asReadonly();
  readonly deleteTarget = this.blockToDelete.asReadonly();

  ngOnChanges(changes: SimpleChanges) {
    if (changes['blocks']) {
      this.buildForm(this.blocks());
      this.selectedIndex.set(null);
      this.selectedIndexChange.emit(null);
    }
  }

  private buildForm(blocks: TextBlockExport[]) {
    this.form.clear({ emitEvent: false });
    const sorted = [...blocks].sort((a, b) => a.ordem - b.ordem);
    for (const b of sorted) {
      this.form.push(this.makeBlock(b), { emitEvent: false });
    }
  }

  private makeBlock(b?: Partial<TextBlockExport>): FormGroup<BlockForm> {
    const defaultTranslations: Partial<Translation>[] = b?.traducoes?.length
      ? b.traducoes
      : [{ traducao: '', observacao: '', relevancia: 1 }];
    return this.fb.group<BlockForm>({
      tipo: this.fb.control<'#' | '$'>(b?.tipo ?? '#', Validators.required),
      original: this.fb.control(b?.original ?? '', Validators.required),
      localizacao: this.fb.control(b?.localizacao ?? '', Validators.required),
      traducoes: this.fb.array<FormGroup<TranslationForm>>(
        defaultTranslations.map((t) => this.makeTranslation(t)),
      ),
      bbox: this.fb.control<BboxPx | null>(b?.bbox ?? null),
    });
  }

  private makeTranslation(t?: Partial<Translation>): FormGroup<TranslationForm> {
    return this.fb.group<TranslationForm>({
      traducao: this.fb.control(t?.traducao ?? '', Validators.required),
      observacao: this.fb.control(t?.observacao ?? ''),
      relevancia: this.fb.control<1 | 2 | 3 | 4 | 5>(t?.relevancia ?? 1),
    });
  }

  // ── Selection ──────────────────────────────────────────────────────────────

  select(index: number) {
    const next = this.selectedIndex() === index ? null : index;
    this.selectedIndex.set(next);
    this.selectedIndexChange.emit(next);
  }

  // ── Block order ────────────────────────────────────────────────────────────

  moveUp(i: number, event: Event) {
    event.stopPropagation();
    if (i <= 0) return;
    const a = this.form.at(i - 1) as FormGroup<BlockForm>;
    const b = this.form.at(i) as FormGroup<BlockForm>;
    this.form.setControl(i - 1, b);
    this.form.setControl(i, a);
    const sel = this.selectedIndex();
    if (sel === i) this.selectedIndex.set(i - 1);
    else if (sel === i - 1) this.selectedIndex.set(i);
  }

  moveDown(i: number, event: Event) {
    event.stopPropagation();
    if (i >= this.form.length - 1) return;
    this.moveUp(i + 1, event);
  }

  // ── Add / delete block ─────────────────────────────────────────────────────

  addBlock() {
    this.form.push(this.makeBlock());
    const newIdx = this.form.length - 1;
    this.selectedIndex.set(newIdx);
    this.selectedIndexChange.emit(newIdx);
  }

  addBlockWithBbox(bbox: BboxPx) {
    this.form.push(this.makeBlock({bbox}));
    const newIdx = this.form.length - 1;
    this.selectedIndex.set(newIdx);
    this.selectedIndexChange.emit(newIdx);
  }

  deleteBlock(i: number, event: Event) {
    event.stopPropagation();
    this.blockToDelete.set(i);
    this.deleteConfirmOpen.set(true);
  }

  confirmDelete() {
    const i = this.blockToDelete();
    if (i === null) return;
    this.form.removeAt(i);
    const sel = this.selectedIndex();
    if (sel === i) {
      this.selectedIndex.set(null);
      this.selectedIndexChange.emit(null);
    } else if (sel !== null && sel > i) {
      this.selectedIndex.update((s) => (s ?? 0) - 1);
    }
    this.deleteConfirmOpen.set(false);
    this.blockToDelete.set(null);
  }

  cancelDelete() {
    this.deleteConfirmOpen.set(false);
    this.blockToDelete.set(null);
  }

  // ── Translations ───────────────────────────────────────────────────────────

  translationsAt(i: number): FormArray<FormGroup<TranslationForm>> {
    return this.form.at(i).controls.traducoes;
  }

  addTranslation(blockIdx: number, event: Event) {
    event.stopPropagation();
    const fa = this.translationsAt(blockIdx);
    if (fa.length >= 5) return;
    fa.push(this.makeTranslation());
  }

  removeTranslation(blockIdx: number, tIdx: number, event: Event) {
    event.stopPropagation();
    const fa = this.translationsAt(blockIdx);
    if (fa.length <= 1) return;
    fa.removeAt(tIdx);
  }

  sortTranslationsOnBlur(blockIdx: number) {
    const fa = this.translationsAt(blockIdx);
    const values = fa.controls.map((c) => ({ ...c.value })) as {
      traducao: string;
      observacao: string;
      relevancia: number;
    }[];
    const sorted = [...values].sort((a, b) => a.relevancia - b.relevancia);
    sorted.forEach((v, i) => fa.at(i).setValue(v as never, { emitEvent: false }));
  }

  // ── Serialise ──────────────────────────────────────────────────────────────

  toTextBlocks(): TextBlockExport[] {
    return this.form.controls.map((g, i) => ({
      ordem: i + 1,
      tipo: (g.value.tipo ?? '#') as '#' | '$',
      original: g.value.original ?? '',
      localizacao: g.value.localizacao ?? '',
      traducoes: (g.value.traducoes ?? []).map((t) => ({
        traducao: t.traducao ?? '',
        observacao: t.observacao ?? '',
        relevancia: (t.relevancia ?? 1) as 1 | 2 | 3 | 4 | 5,
      })),
    }));
  }
}
