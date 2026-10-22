import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { FoldersApi } from '../../core/api/folders.api';
import { FolderSummary } from '../../core/api/models';
import { UiBadgeComponent } from '../../shared/ui/ui-badge.component';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import { UiDialogComponent } from '../../shared/ui/ui-dialog.component';
import { UiEmptyStateComponent } from '../../shared/ui/ui-empty-state.component';
import { UiSkeletonRowsComponent } from '../../shared/ui/ui-skeleton.component';

@Component({
  selector: 'app-folder-list-page',
  standalone: true,
  imports: [
    FormsModule,
    RouterLink,
    UiBadgeComponent,
    UiButtonComponent,
    UiDialogComponent,
    UiEmptyStateComponent,
    UiSkeletonRowsComponent,
  ],
  template: `
    <div class="mx-auto max-w-7xl px-4 md:px-6 py-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <h1 class="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">Pastas traduzidas</h1>

        @if (!loading() && !error() && folders().length > 0) {
          <div class="relative w-full sm:w-72">
            <svg
              class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 size-4 text-zinc-400"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"
            >
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              type="search"
              placeholder="Buscar pasta..."
              [ngModel]="searchInput()"
              (ngModelChange)="onSearchChange($event)"
              class="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 pl-9 pr-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              aria-label="Buscar pasta"
            />
          </div>
        }
      </div>

      @if (loading()) {
        <ui-skeleton-rows [count]="5" />
      } @else if (error()) {
        <ui-empty-state icon="info" title="Erro ao carregar pastas" [description]="error() ?? ''">
          <button class="rounded-lg border border-primary-600 text-primary-700 dark:border-primary-400 dark:text-primary-300 px-4 py-2 text-sm font-medium hover:bg-primary-50 dark:hover:bg-primary-950 transition-colors" (click)="loadFolders()">Tentar novamente</button>
        </ui-empty-state>
      } @else if (folders().length === 0) {
        <ui-empty-state icon="folder" title="Nenhuma pasta traduzida ainda" description="Inicie uma nova tradução para começar.">
          <a routerLink="/nova-traducao" class="inline-flex items-center gap-2 rounded-lg px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium text-sm transition-colors">Nova tradução</a>
        </ui-empty-state>
      } @else if (filteredFolders().length === 0) {
        <ui-empty-state icon="search" title="Nenhuma pasta encontrada" [description]="'Nenhum resultado para: ' + searchInput()">
          <button class="rounded-lg px-4 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors" (click)="clearSearch()">Limpar busca</button>
        </ui-empty-state>
      } @else {
        <!-- Desktop table -->
        <div class="hidden md:block overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
          <table class="w-full text-sm">
            <thead class="bg-zinc-50 dark:bg-zinc-900">
              <tr class="text-left text-zinc-500 dark:text-zinc-400">
                <th class="px-4 py-3 font-medium">Nome</th>
                <th class="px-4 py-3 font-medium">Páginas</th>
                <th class="px-4 py-3 font-medium">Status</th>
                <th class="px-4 py-3 font-medium">Atualizado</th>
                <th class="px-4 py-3 font-medium text-right">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-200 dark:divide-zinc-800 bg-white dark:bg-zinc-950">
              @for (folder of filteredFolders(); track folder.id) {
                <tr
                  class="hover:bg-zinc-50 dark:hover:bg-zinc-900/50 cursor-pointer group transition-colors"
                  (click)="open(folder)"
                >
                  <td class="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">
                    {{ folder.name }}
                  </td>
                  <td class="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    {{ pagesLabel(folder) }}
                  </td>
                  <td class="px-4 py-3">
                    <ui-badge [status]="folder.status" />
                  </td>
                  <td class="px-4 py-3 text-zinc-500 dark:text-zinc-400 tabular-nums">
                    {{ formatDate(folder.updated_at) }}
                  </td>
                  <td class="px-4 py-3">
                    <div class="flex items-center justify-end gap-1">
                      <button
                        class="rounded-md px-2.5 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                        (click)="open(folder); $event.stopPropagation()"
                      >Abrir</button>
                      <button
                        class="rounded-md px-2.5 py-1.5 text-xs font-medium text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                        (click)="startRename(folder); $event.stopPropagation()"
                        title="Renomear"
                        aria-label="Renomear {{ folder.name }}"
                      >
                        <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      </button>
                      <button
                        class="rounded-md px-2.5 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                        (click)="startDelete(folder); $event.stopPropagation()"
                        title="Excluir"
                        aria-label="Excluir {{ folder.name }}"
                      >
                        <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
                      </button>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Mobile cards -->
        <div class="flex flex-col gap-3 md:hidden">
          @for (folder of filteredFolders(); track folder.id) {
            <div
              class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 flex flex-col gap-3"
            >
              <div class="flex items-start justify-between gap-2">
                <span class="font-medium text-zinc-900 dark:text-zinc-100 leading-tight">
                  {{ folder.name }}
                </span>
                <ui-badge [status]="folder.status" />
              </div>

              <div class="flex items-center gap-4 text-xs text-zinc-500 dark:text-zinc-400">
                <span>{{ pagesLabel(folder) }} páginas</span>
                <span>{{ formatDate(folder.updated_at) }}</span>
              </div>

              <div class="flex items-center gap-2">
                <button
                  class="flex-1 rounded-lg px-3 py-1.5 text-sm font-medium text-center text-primary-700 dark:text-primary-300 border border-primary-600 dark:border-primary-400 hover:bg-primary-50 dark:hover:bg-primary-950 transition-colors"
                  (click)="open(folder)"
                >Abrir</button>
                <button
                  class="rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                  (click)="startRename(folder)"
                  aria-label="Renomear {{ folder.name }}"
                >
                  <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button
                  class="rounded-lg p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                  (click)="startDelete(folder)"
                  aria-label="Excluir {{ folder.name }}"
                >
                  <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
                </button>
              </div>
            </div>
          }
        </div>
      }
    </div>

    <!-- Rename dialog -->
    <ui-dialog [open]="!!renamingFolder()" (closed)="cancelRename()">
      <div class="p-6 flex flex-col gap-4">
        <h2 id="rename-title" class="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          Renomear pasta
        </h2>
        <input
          #renameInput
          type="text"
          [(ngModel)]="renameValue"
          maxlength="120"
          class="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
          (keydown.enter)="confirmRename()"
          (keydown.escape)="cancelRename()"
          aria-label="Novo nome da pasta"
        />
        <div class="flex justify-end gap-2">
          <ui-button variant="ghost" size="sm" (click)="cancelRename()">Cancelar</ui-button>
          <ui-button
            size="sm"
            [loading]="renaming()"
            [disabled]="!renameValue.trim()"
            (click)="confirmRename()"
          >Salvar</ui-button>
        </div>
      </div>
    </ui-dialog>

    <!-- Delete dialog -->
    <ui-dialog [open]="!!deletingFolder()" (closed)="cancelDelete()">
      <div class="p-6 flex flex-col gap-4">
        <h2 class="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          Excluir pasta
        </h2>
        <p class="text-sm text-zinc-600 dark:text-zinc-400">
          Tem certeza que deseja excluir
          <strong class="text-zinc-900 dark:text-zinc-100">{{ deletingFolder()?.name }}</strong>?
          Essa ação não pode ser desfeita.
        </p>
        <div class="flex justify-end gap-2">
          <ui-button variant="ghost" size="sm" (click)="cancelDelete()">Cancelar</ui-button>
          <ui-button
            variant="destructive"
            size="sm"
            [loading]="deleting()"
            (click)="confirmDelete()"
          >Excluir</ui-button>
        </div>
      </div>
    </ui-dialog>
  `,
})
export class FolderListPage implements OnInit {
  private readonly foldersApi = inject(FoldersApi);
  private readonly router = inject(Router);

  readonly folders = signal<FolderSummary[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly searchInput = signal('');
  readonly filteredFolders = computed(() => {
    const q = this.searchInput().toLowerCase();
    if (!q) return this.folders();
    return this.folders().filter(f => f.name.toLowerCase().includes(q));
  });

  readonly renamingFolder = signal<FolderSummary | null>(null);
  readonly renaming = signal(false);
  renameValue = '';

  readonly deletingFolder = signal<FolderSummary | null>(null);
  readonly deleting = signal(false);

  private readonly searchSubject = new Subject<string>();

  constructor() {
    this.searchSubject.pipe(debounceTime(200), distinctUntilChanged()).subscribe(q => {
      this.searchInput.set(q);
    });
  }

  ngOnInit(): void {
    this.loadFolders();
  }

  loadFolders(): void {
    this.loading.set(true);
    this.error.set(null);
    this.foldersApi.list().subscribe({
      next: fs => {
        this.folders.set(fs);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Não foi possível carregar as pastas.');
        this.loading.set(false);
      },
    });
  }

  onSearchChange(value: string): void {
    this.searchSubject.next(value);
  }

  clearSearch(): void {
    this.searchSubject.next('');
  }

  open(folder: FolderSummary): void {
    this.router.navigate(['/pastas', folder.id]);
  }

  pagesLabel(folder: FolderSummary): string {
    if (folder.status === 'INCOMPLETE') {
      return `${folder.processed_pages}/${folder.total_pages}`;
    }
    return String(folder.total_pages);
  }

  formatDate(iso: string): string {
    const d = new Date(iso);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${day}/${month} ${hh}:${mm}`;
  }

  // ── Rename ─────────────────────────────────────────────────────────────────

  startRename(folder: FolderSummary): void {
    this.renamingFolder.set(folder);
    this.renameValue = folder.name;
  }

  cancelRename(): void {
    this.renamingFolder.set(null);
    this.renameValue = '';
  }

  confirmRename(): void {
    const folder = this.renamingFolder();
    if (!folder || !this.renameValue.trim() || this.renaming()) return;
    this.renaming.set(true);
    this.foldersApi.rename(folder.id, this.renameValue.trim()).subscribe({
      next: updated => {
        this.folders.update(fs => fs.map(f => (f.id === updated.id ? updated : f)));
        this.renaming.set(false);
        this.cancelRename();
      },
      error: () => {
        this.renaming.set(false);
      },
    });
  }

  // ── Delete ─────────────────────────────────────────────────────────────────

  startDelete(folder: FolderSummary): void {
    this.deletingFolder.set(folder);
  }

  cancelDelete(): void {
    this.deletingFolder.set(null);
  }

  confirmDelete(): void {
    const folder = this.deletingFolder();
    if (!folder || this.deleting()) return;
    this.deleting.set(true);
    this.foldersApi.remove(folder.id).subscribe({
      next: () => {
        this.folders.update(fs => fs.filter(f => f.id !== folder.id));
        this.deleting.set(false);
        this.cancelDelete();
      },
      error: () => {
        this.deleting.set(false);
      },
    });
  }
}
