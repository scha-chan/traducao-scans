import {
  Component,
  OnChanges,
  SimpleChanges,
  computed,
  input,
  output,
  signal,
  inject,
} from '@angular/core';
export type BlockSaveState = 'idle' | 'saving' | 'saved' | 'error';
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
import { TranslationListComponent, TranslationForm } from './translation-list.component';

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
  imports: [ReactiveFormsModule, UiDialogComponent, UiButtonComponent, TranslationListComponent],
  templateUrl: './block-table.component.html',
  styleUrl: './block-table.component.scss',
})
export class BlockTableComponent implements OnChanges {
  private readonly fb = inject(NonNullableFormBuilder);

  readonly blocks = input.required<TextBlockExport[]>();
  readonly loading = input<boolean>(false);
  readonly saveState = input<BlockSaveState>('idle');

  readonly selectedIndex = signal<number | null>(null);
  readonly form = this.fb.array<FormGroup<BlockForm>>([]);

  readonly selectedIndexChange = output<number | null>();

  private deleteConfirmOpen = signal(false);
  private blockToDelete = signal<number | null>(null);
  readonly showDeleteDialog = this.deleteConfirmOpen.asReadonly();
  readonly deleteTarget = this.blockToDelete.asReadonly();

  readonly selectedBlock = computed(() => {
    const i = this.selectedIndex();
    return i !== null ? (this.form.at(i) as FormGroup<BlockForm>) : null;
  });

  readonly selectedTranslations = computed(() => {
    const i = this.selectedIndex();
    return i !== null ? this.translationsAt(i) : null;
  });

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
      relevancia: this.fb.control<1 | 2 | 3 | 4 | 5>((t?.relevancia ?? 1) as 1 | 2 | 3 | 4 | 5),
    });
  }

  // ── Selection ──────────────────────────────────────────────────────────────

  select(index: number) {
    const next = this.selectedIndex() === index ? null : index;
    this.selectedIndex.set(next);
    this.selectedIndexChange.emit(next);
  }

  selectNext() {
    const i = this.selectedIndex();
    const max = this.form.length - 1;
    if (max < 0) return;
    const next = i === null ? 0 : Math.min(i + 1, max);
    this.selectedIndex.set(next);
    this.selectedIndexChange.emit(next);
  }

  selectPrev() {
    const i = this.selectedIndex();
    const max = this.form.length - 1;
    if (max < 0) return;
    const next = i === null ? max : Math.max(i - 1, 0);
    this.selectedIndex.set(next);
    this.selectedIndexChange.emit(next);
  }

  toggleType() {
    const block = this.selectedBlock();
    if (!block) return;
    const current = block.controls.tipo.value;
    block.controls.tipo.setValue(current === '#' ? '$' : '#');
  }

  setType(tipo: '#' | '$') {
    this.selectedBlock()?.controls.tipo.setValue(tipo);
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

  reorderAt(from: number, to: number) {
    const n = this.form.length;
    if (from === to || from < 0 || to < 0 || from >= n || to >= n) return;
    const control = this.form.at(from);
    this.form.removeAt(from, { emitEvent: false });
    this.form.insert(to, control, { emitEvent: false });
    this.form.markAsDirty();
    const sel = this.selectedIndex();
    if (sel === null) return;
    if (sel === from) { this.selectedIndex.set(to); return; }
    if (from < to && sel > from && sel <= to) this.selectedIndex.update((s) => (s ?? 0) - 1);
    else if (from > to && sel >= to && sel < from) this.selectedIndex.update((s) => (s ?? 0) + 1);
  }

  // ── Add / delete block ─────────────────────────────────────────────────────

  addBlock() {
    this.form.push(this.makeBlock());
    const newIdx = this.form.length - 1;
    this.selectedIndex.set(newIdx);
    this.selectedIndexChange.emit(newIdx);
  }

  addBlockWithBbox(bbox: BboxPx) {
    this.form.push(this.makeBlock({ bbox }));
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

  // ── Dirty / server errors ──────────────────────────────────────────────────

  get isDirty(): boolean {
    return this.form.dirty;
  }

  markAsPristine() {
    this.form.markAsPristine();
  }

  setServerErrors(errors: Record<string, string>) {
    for (const [path, message] of Object.entries(errors)) {
      const blockMatch = path.match(/^\[(\d+)\]\.(.+)$/);
      if (blockMatch) {
        const idx = parseInt(blockMatch[1], 10);
        const field = blockMatch[2];
        const blockGroup = this.form.at(idx) as FormGroup<BlockForm> | undefined;
        if (!blockGroup) continue;
        const translationMatch = field.match(/^traducoes\[(\d+)\]\.(.+)$/);
        if (translationMatch) {
          const tIdx = parseInt(translationMatch[1], 10);
          const tField = translationMatch[2] as keyof TranslationForm;
          const ctrl = blockGroup.controls.traducoes.at(tIdx)?.controls[tField];
          ctrl?.setErrors({ serverError: message });
        } else {
          const ctrl = blockGroup.controls[field as keyof BlockForm];
          (ctrl as FormControl | undefined)?.setErrors({ serverError: message });
        }
      }
    }
  }

  clearServerErrors() {
    this.form.controls.forEach((g) => {
      const bg = g as FormGroup<BlockForm>;
      (['tipo', 'original', 'localizacao'] as const).forEach((f) => {
        if (bg.controls[f].hasError('serverError')) bg.controls[f].setErrors(null);
      });
      bg.controls.traducoes.controls.forEach((tg) => {
        (['traducao', 'observacao', 'relevancia'] as const).forEach((f) => {
          if (tg.controls[f].hasError('serverError')) tg.controls[f].setErrors(null);
        });
      });
    });
  }

  // ── Serialise ──────────────────────────────────────────────────────────────

  toTextBlocks(): TextBlockExport[] {
    return this.form.controls.map((g, i) => {
      const block: TextBlockExport = {
        ordem: i + 1,
        tipo: (g.value.tipo ?? '#') as '#' | '$',
        original: g.value.original ?? '',
        localizacao: g.value.localizacao ?? '',
        traducoes: (g.value.traducoes ?? []).map((t) => ({
          traducao: t.traducao ?? '',
          observacao: t.observacao ?? '',
          relevancia: (t.relevancia ?? 1) as 1 | 2 | 3 | 4 | 5,
        })),
      };
      const bbox = g.value.bbox;
      if (bbox) block.bbox = bbox;
      return block;
    });
  }
}
