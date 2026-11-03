import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CharactersApi } from '../../core/api/characters.api';
import { WorksApi } from '../../core/api/works.api';
import {
  Character,
  CharacterCreate,
  CharacterUpdate,
  Gender,
  SpeechRegister,
  WorkSummary,
} from '../../core/api/models';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import { UiDialogComponent } from '../../shared/ui/ui-dialog.component';
import { UiEmptyStateComponent } from '../../shared/ui/ui-empty-state.component';
import { UiSkeletonRowsComponent } from '../../shared/ui/ui-skeleton.component';

const REGISTER_LABELS: Record<SpeechRegister, string> = {
  formal: 'Formal',
  informal: 'Informal',
  childlike: 'Infantil',
  rough: 'Áspero',
  polite: 'Polido',
};

const GENDER_LABELS: Record<Gender, string> = {
  male: 'Masculino',
  female: 'Feminino',
  unknown: 'Desconhecido',
};

const SPEECH_REGISTERS: SpeechRegister[] = ['formal', 'informal', 'childlike', 'rough', 'polite'];
const GENDERS: Gender[] = ['male', 'female', 'unknown'];

interface CharacterForm {
  name_original: string;
  name_preferred: string;
  gender: Gender | '';
  speech_register: SpeechRegister | '';
  notes: string;
}

function emptyForm(): CharacterForm {
  return { name_original: '', name_preferred: '', gender: '', speech_register: '', notes: '' };
}

@Component({
  selector: 'app-character-list-page',
  standalone: true,
  imports: [
    FormsModule,
    RouterLink,
    UiButtonComponent,
    UiDialogComponent,
    UiEmptyStateComponent,
    UiSkeletonRowsComponent,
  ],
  template: `
    <div class="mx-auto max-w-5xl px-4 md:px-6 py-6">
      <!-- Breadcrumb / header -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <a routerLink="/" class="text-sm text-zinc-500 dark:text-zinc-400 hover:underline">
            Início
          </a>
          <span class="mx-1 text-zinc-400">›</span>
          <span class="text-sm text-zinc-700 dark:text-zinc-300 font-medium">
            {{ work()?.title ?? 'Obra' }}
          </span>
          <h1 class="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mt-1">Personagens</h1>
        </div>
        @if (!loading() && !loadError()) {
          <ui-button (click)="openCreate()">Novo personagem</ui-button>
        }
      </div>

      @if (loading()) {
        <ui-skeleton-rows [count]="4" />
      } @else if (loadError()) {
        <ui-empty-state icon="info" title="Erro ao carregar personagens" [description]="loadError() ?? ''">
          <button
            class="rounded-lg border border-primary-600 text-primary-700 dark:border-primary-400 dark:text-primary-300 px-4 py-2 text-sm font-medium hover:bg-primary-50 dark:hover:bg-primary-950 transition-colors"
            (click)="loadCharacters()"
          >Tentar novamente</button>
        </ui-empty-state>
      } @else if (characters().length === 0) {
        <ui-empty-state icon="info" title="Nenhum personagem cadastrado" description="Adicione o primeiro personagem desta obra.">
          <ui-button (click)="openCreate()">Novo personagem</ui-button>
        </ui-empty-state>
      } @else {
        <!-- Desktop table -->
        <div class="hidden md:block overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
          <table class="w-full text-sm">
            <thead class="bg-zinc-50 dark:bg-zinc-900">
              <tr class="text-left text-zinc-500 dark:text-zinc-400">
                <th class="px-4 py-3 font-medium">Nome original</th>
                <th class="px-4 py-3 font-medium">Nome preferido</th>
                <th class="px-4 py-3 font-medium">Gênero</th>
                <th class="px-4 py-3 font-medium">Registro de fala</th>
                <th class="px-4 py-3 font-medium text-right">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-200 dark:divide-zinc-800 bg-white dark:bg-zinc-950">
              @for (char of characters(); track char.id) {
                <tr class="hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors">
                  <td class="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">
                    {{ char.name_original }}
                  </td>
                  <td class="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    {{ char.name_preferred ?? '—' }}
                  </td>
                  <td class="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    {{ char.gender ? genderLabel(char.gender) : '—' }}
                  </td>
                  <td class="px-4 py-3">
                    @if (char.speech_register) {
                      <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                        {{ registerLabel(char.speech_register) }}
                      </span>
                    } @else {
                      <span class="text-zinc-400 dark:text-zinc-500">—</span>
                    }
                  </td>
                  <td class="px-4 py-3">
                    <div class="flex items-center justify-end gap-1">
                      <button
                        class="rounded-md px-2.5 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                        (click)="openEdit(char)"
                        aria-label="Editar {{ char.name_original }}"
                      >Editar</button>
                      <button
                        class="rounded-md px-2.5 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                        (click)="startDelete(char)"
                        aria-label="Excluir {{ char.name_original }}"
                      >Excluir</button>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Mobile cards -->
        <div class="flex flex-col gap-3 md:hidden">
          @for (char of characters(); track char.id) {
            <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 flex flex-col gap-2">
              <div class="flex items-start justify-between gap-2">
                <div>
                  <span class="font-medium text-zinc-900 dark:text-zinc-100 leading-tight">
                    {{ char.name_original }}
                  </span>
                  @if (char.name_preferred) {
                    <span class="ml-2 text-sm text-zinc-500 dark:text-zinc-400">({{ char.name_preferred }})</span>
                  }
                </div>
                @if (char.speech_register) {
                  <span class="shrink-0 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                    {{ registerLabel(char.speech_register) }}
                  </span>
                }
              </div>
              @if (char.gender) {
                <span class="text-xs text-zinc-500 dark:text-zinc-400">{{ genderLabel(char.gender) }}</span>
              }
              @if (char.notes) {
                <p class="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2">{{ char.notes }}</p>
              }
              <div class="flex items-center gap-2 pt-1">
                <button
                  class="flex-1 rounded-lg px-3 py-1.5 text-sm font-medium text-center text-primary-700 dark:text-primary-300 border border-primary-600 dark:border-primary-400 hover:bg-primary-50 dark:hover:bg-primary-950 transition-colors"
                  (click)="openEdit(char)"
                >Editar</button>
                <button
                  class="rounded-lg p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                  (click)="startDelete(char)"
                  aria-label="Excluir {{ char.name_original }}"
                >
                  <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
                    <path d="M10 11v6"/><path d="M14 11v6"/>
                    <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
                  </svg>
                </button>
              </div>
            </div>
          }
        </div>
      }
    </div>

    <!-- Create / Edit dialog -->
    <ui-dialog [open]="!!editingChar() || creating()" (closed)="cancelForm()">
      <div class="p-6 flex flex-col gap-4 w-[95vw] max-w-md">
        <h2 class="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          {{ editingChar() ? 'Editar personagem' : 'Novo personagem' }}
        </h2>

        <div class="flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-zinc-700 dark:text-zinc-300" for="name-original">
              Nome original <span class="text-red-500" aria-hidden="true">*</span>
            </label>
            <input
              id="name-original"
              type="text"
              [(ngModel)]="form.name_original"
              maxlength="255"
              class="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Ex.: 田中 一郎"
              (keydown.escape)="cancelForm()"
            />
          </div>

          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-zinc-700 dark:text-zinc-300" for="name-preferred">
              Nome preferido
            </label>
            <input
              id="name-preferred"
              type="text"
              [(ngModel)]="form.name_preferred"
              maxlength="255"
              class="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Ex.: Tanaka Ichiro"
              (keydown.escape)="cancelForm()"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1">
              <label class="text-sm font-medium text-zinc-700 dark:text-zinc-300" for="gender">
                Gênero
              </label>
              <select
                id="gender"
                [(ngModel)]="form.gender"
                class="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">—</option>
                @for (g of genders; track g) {
                  <option [value]="g">{{ genderLabel(g) }}</option>
                }
              </select>
            </div>

            <div class="flex flex-col gap-1">
              <label class="text-sm font-medium text-zinc-700 dark:text-zinc-300" for="speech-register">
                Registro de fala
              </label>
              <select
                id="speech-register"
                [(ngModel)]="form.speech_register"
                class="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">—</option>
                @for (r of registers; track r) {
                  <option [value]="r">{{ registerLabel(r) }}</option>
                }
              </select>
            </div>
          </div>

          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-zinc-700 dark:text-zinc-300" for="notes">
              Notas
            </label>
            <textarea
              id="notes"
              [(ngModel)]="form.notes"
              rows="3"
              class="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              placeholder="Observações sobre o personagem..."
            ></textarea>
          </div>
        </div>

        @if (formError()) {
          <p class="text-sm text-red-600 dark:text-red-400">{{ formError() }}</p>
        }

        <div class="flex justify-end gap-2">
          <ui-button variant="ghost" size="sm" (click)="cancelForm()">Cancelar</ui-button>
          <ui-button
            size="sm"
            [loading]="saving()"
            [disabled]="!form.name_original.trim()"
            (click)="saveForm()"
          >{{ editingChar() ? 'Salvar' : 'Criar' }}</ui-button>
        </div>
      </div>
    </ui-dialog>

    <!-- Delete dialog -->
    <ui-dialog [open]="!!deletingChar()" (closed)="cancelDelete()">
      <div class="p-6 flex flex-col gap-4">
        <h2 class="text-base font-semibold text-zinc-900 dark:text-zinc-100">Excluir personagem</h2>
        <p class="text-sm text-zinc-600 dark:text-zinc-400">
          Tem certeza que deseja excluir
          <strong class="text-zinc-900 dark:text-zinc-100">{{ deletingChar()?.name_original }}</strong>?
          Essa ação não pode ser desfeita.
        </p>
        <div class="flex justify-end gap-2">
          <ui-button variant="ghost" size="sm" (click)="cancelDelete()">Cancelar</ui-button>
          <ui-button variant="destructive" size="sm" [loading]="deleting()" (click)="confirmDelete()">
            Excluir
          </ui-button>
        </div>
      </div>
    </ui-dialog>
  `,
})
export class CharacterListPage implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly charactersApi = inject(CharactersApi);
  private readonly worksApi = inject(WorksApi);

  private readonly workId = signal('');

  readonly work = signal<WorkSummary | null>(null);
  readonly characters = signal<Character[]>([]);
  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);

  readonly creating = signal(false);
  readonly editingChar = signal<Character | null>(null);
  readonly saving = signal(false);
  readonly formError = signal<string | null>(null);

  readonly deletingChar = signal<Character | null>(null);
  readonly deleting = signal(false);

  form: CharacterForm = emptyForm();

  readonly registers = SPEECH_REGISTERS;
  readonly genders = GENDERS;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('workId') ?? '';
    this.workId.set(id);
    this.loadWork();
    this.loadCharacters();
  }

  loadWork(): void {
    const id = this.workId();
    if (!id) return;
    this.worksApi.get(id).subscribe(w => this.work.set(w));
  }

  loadCharacters(): void {
    const id = this.workId();
    if (!id) return;
    this.loading.set(true);
    this.loadError.set(null);
    this.charactersApi.listByWork(id).subscribe({
      next: chars => {
        this.characters.set(chars);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set('Não foi possível carregar os personagens.');
        this.loading.set(false);
      },
    });
  }

  registerLabel(r: SpeechRegister): string {
    return REGISTER_LABELS[r];
  }

  genderLabel(g: Gender): string {
    return GENDER_LABELS[g];
  }

  openCreate(): void {
    this.form = emptyForm();
    this.formError.set(null);
    this.creating.set(true);
  }

  openEdit(char: Character): void {
    this.form = {
      name_original: char.name_original,
      name_preferred: char.name_preferred ?? '',
      gender: char.gender ?? '',
      speech_register: char.speech_register ?? '',
      notes: char.notes ?? '',
    };
    this.formError.set(null);
    this.editingChar.set(char);
  }

  cancelForm(): void {
    this.creating.set(false);
    this.editingChar.set(null);
    this.form = emptyForm();
  }

  saveForm(): void {
    if (!this.form.name_original.trim() || this.saving()) return;
    this.saving.set(true);
    this.formError.set(null);

    const editing = this.editingChar();
    if (editing) {
      const body: CharacterUpdate = {
        name_original: this.form.name_original.trim(),
        name_preferred: this.form.name_preferred.trim() || null,
        gender: this.form.gender || null,
        speech_register: this.form.speech_register || null,
        notes: this.form.notes.trim() || null,
      };
      this.charactersApi.update(editing.id, body).subscribe({
        next: updated => {
          this.characters.update(cs => cs.map(c => (c.id === updated.id ? updated : c)));
          this.saving.set(false);
          this.cancelForm();
        },
        error: () => {
          this.formError.set('Erro ao salvar. Tente novamente.');
          this.saving.set(false);
        },
      });
    } else {
      const body: CharacterCreate = {
        name_original: this.form.name_original.trim(),
        name_preferred: this.form.name_preferred.trim() || null,
        gender: this.form.gender || null,
        speech_register: this.form.speech_register || null,
        notes: this.form.notes.trim() || null,
      };
      this.charactersApi.create(this.workId(), body).subscribe({
        next: created => {
          this.characters.update(cs => [...cs, created]);
          this.saving.set(false);
          this.cancelForm();
        },
        error: () => {
          this.formError.set('Erro ao criar personagem. Tente novamente.');
          this.saving.set(false);
        },
      });
    }
  }

  startDelete(char: Character): void {
    this.deletingChar.set(char);
  }

  cancelDelete(): void {
    this.deletingChar.set(null);
  }

  confirmDelete(): void {
    const char = this.deletingChar();
    if (!char || this.deleting()) return;
    this.deleting.set(true);
    this.charactersApi.remove(char.id).subscribe({
      next: () => {
        this.characters.update(cs => cs.filter(c => c.id !== char.id));
        this.deleting.set(false);
        this.cancelDelete();
      },
      error: () => {
        this.deleting.set(false);
      },
    });
  }
}
