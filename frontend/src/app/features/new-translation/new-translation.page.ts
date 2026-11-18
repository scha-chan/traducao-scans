import { Component, OnDestroy, signal, computed, inject } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { FoldersApi } from '../../core/api/folders.api';
import { PagesApi } from '../../core/api/pages.api';
import { NotificationService } from '../../core/notifications/notification.service';
import { extractErrorMessage } from '../../core/http/extract-error';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import { UiDropzoneComponent } from '../../shared/ui/ui-dropzone.component';
import { UiProgressComponent } from '../../shared/ui/ui-progress.component';

type AppState = 'selecao' | 'processando' | 'concluido';

type ImageRowStatus = 'pending' | 'processing' | 'done' | 'error';

interface AcceptedFile {
  file: File;
  pageNumber: number;
}

interface IgnoredFile {
  name: string;
  reason: string;
}

interface ImageRow {
  file: File;
  pageNumber: number;
  status: ImageRowStatus;
  blockCount?: number;
  tokensUsed?: number;
  processingMs?: number;
  errorMsg?: string;
}

const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp']);
const MAX_FILE_SIZE = 20 * 1024 * 1024;
const HIDDEN_FILES = new Set(['.ds_store', 'thumbs.db', 'desktop.ini']);

function ext(name: string): string {
  return name.slice(name.lastIndexOf('.')).toLowerCase();
}

function ignoreReason(file: File): string | null {
  const name = file.name.toLowerCase();
  if (name.startsWith('.') || HIDDEN_FILES.has(name)) return 'arquivo oculto';
  if (file.size === 0) return 'arquivo vazio';
  if (file.size > MAX_FILE_SIZE) return 'acima de 20 MB';
  if (!IMAGE_EXTENSIONS.has(ext(file.name)) || !file.type.startsWith('image/')) return 'não é imagem';
  return null;
}

const collator = new Intl.Collator('pt-BR', { numeric: true, sensitivity: 'base' });

@Component({
  selector: 'app-new-translation-page',
  standalone: true,
  imports: [DecimalPipe, FormsModule, UiButtonComponent, UiDropzoneComponent, UiProgressComponent],
  template: `
    <div class="mx-auto max-w-3xl px-4 py-12">

      <!-- SELEÇÃO -->
      @if (appState() === 'selecao') {
        <h1 class="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mb-8">Nova tradução</h1>

        <ui-dropzone (filesSelected)="onFilesSelected($event)" class="mb-6" />

        @if (accepted().length > 0) {
          <div class="flex flex-col gap-4">
            <!-- Folder name -->
            <div class="flex flex-col gap-1.5">
              <label for="folder-name" class="text-sm font-medium text-zinc-700 dark:text-zinc-300">Nome da pasta</label>
              <input id="folder-name" type="text" [(ngModel)]="folderName" maxlength="120" class="rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 ring-primary-500" />
              @if (conflictSuggestion()) {
                <p class="text-sm text-amber-600 dark:text-amber-400">
                  Nome já existe.
                  <button type="button" (click)="useSuggestion()" class="underline hover:no-underline">Usar "{{ conflictSuggestion() }}"</button>
                </p>
              }
            </div>

            <!-- File summary -->
            <div class="rounded-lg border border-zinc-200 dark:border-zinc-700 p-4 flex flex-col gap-2">
              <div class="flex items-center gap-4 text-sm">
                <span class="text-emerald-600 dark:text-emerald-400">✔ {{ accepted().length }} {{ accepted().length === 1 ? 'imagem encontrada' : 'imagens encontradas' }}</span>
                @if (ignored().length > 0) {
                  <button type="button" (click)="toggleIgnored()" class="text-amber-600 dark:text-amber-400 hover:underline">⚠ {{ ignored().length }} {{ ignored().length === 1 ? 'arquivo ignorado' : 'arquivos ignorados' }} [ver]</button>
                }
              </div>

              @if (showIgnored()) {
                <ul class="mt-1 max-h-32 overflow-y-auto text-xs text-zinc-500 dark:text-zinc-400 space-y-0.5 pl-2 border-l-2 border-zinc-200 dark:border-zinc-700">
                  @for (f of ignored(); track f.name) {
                    <li><span class="font-mono">{{ f.name }}</span> — {{ f.reason }}</li>
                  }
                </ul>
              }

              @if (accepted().length > 200) {
                <p class="text-sm text-amber-600 dark:text-amber-400">⚠ Pastas grandes podem levar vários minutos.</p>
              }

              <!-- File list preview -->
              <ul class="mt-1 max-h-24 overflow-y-auto text-xs text-zinc-500 dark:text-zinc-400 flex flex-wrap gap-1">
                @for (f of accepted().slice(0, 20); track f.pageNumber) {
                  <li class="font-mono">{{ f.file.name }}</li>
                }
                @if (accepted().length > 20) {
                  <li>… mais {{ accepted().length - 20 }}</li>
                }
              </ul>
            </div>

            <!-- Actions -->
            <div class="flex justify-end gap-3 pt-2">
              <ui-button variant="secondary" (click)="cancelSelection()">Cancelar</ui-button>
              <ui-button variant="primary" [disabled]="!canStart()" (click)="startProcessing()">Iniciar tradução</ui-button>
            </div>
          </div>
        }
      }

      <!-- PROCESSANDO -->
      @else if (appState() === 'processando') {
        <h1 class="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mb-6">
          Traduzindo "{{ folderName }}"
        </h1>

        <div class="flex flex-col gap-5">
          <ui-progress [value]="processed()" [max]="total()" [label]="processedLabel()" [sublabel]="timeRemaining()" />

          <div class="flex gap-4 text-sm">
            <span class="text-emerald-600 dark:text-emerald-400">✔ {{ successCount() }} concluídas</span>
            @if (errorCountProcessing() > 0) {
              <span class="text-amber-600 dark:text-amber-400">⚠ {{ errorCountProcessing() }} com erro</span>
            }
          </div>

          <!-- Tabela de status por imagem -->
          <div class="rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden">
            <div class="max-h-80 overflow-y-auto">
              <table class="w-full text-sm">
                <thead class="sticky top-0 bg-zinc-50 dark:bg-zinc-800/80 backdrop-blur-sm">
                  <tr class="text-left text-xs text-zinc-500 dark:text-zinc-400">
                    <th class="px-3 py-2 font-medium w-10">#</th>
                    <th class="px-3 py-2 font-medium">Arquivo</th>
                    <th class="px-3 py-2 font-medium w-32">Status</th>
                    <th class="px-3 py-2 font-medium text-right w-16">Blocos</th>
                    <th class="px-3 py-2 font-medium text-right w-20">Tokens</th>
                    <th class="px-3 py-2 font-medium text-right w-20">Tempo</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-zinc-100 dark:divide-zinc-800">
                  @for (row of imageRows(); track row.pageNumber) {
                    <tr [class]="row.status === 'processing' ? 'bg-primary-50/60 dark:bg-primary-900/10' : ''">
                      <td class="px-3 py-2 text-zinc-400 tabular-nums">{{ row.pageNumber }}</td>
                      <td class="px-3 py-2 text-zinc-700 dark:text-zinc-300 font-mono text-xs max-w-[200px] truncate" [title]="row.file.name">{{ row.file.name }}</td>
                      <td class="px-3 py-2">
                        @if (row.status === 'pending') {
                          <span class="text-xs text-zinc-400">Aguardando</span>
                        } @else if (row.status === 'processing') {
                          <span class="inline-flex items-center gap-1 text-xs text-primary-700 dark:text-primary-300">
                            <svg class="size-3 animate-spin shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                            </svg>
                            Processando
                          </span>
                        } @else if (row.status === 'done') {
                          <span class="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                            <svg class="size-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>
                            Concluído
                          </span>
                        } @else {
                          <span class="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400" [title]="row.errorMsg">
                            <svg class="size-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                            Erro
                          </span>
                        }
                      </td>
                      <td class="px-3 py-2 text-right text-zinc-500 tabular-nums">
                        @if (row.status === 'done') { {{ row.blockCount }} }
                      </td>
                      <td class="px-3 py-2 text-right text-zinc-500 tabular-nums text-xs">
                        @if (row.tokensUsed !== null && row.tokensUsed !== undefined) { {{ row.tokensUsed | number }} }
                      </td>
                      <td class="px-3 py-2 text-right text-zinc-500 tabular-nums text-xs">
                        @if (row.processingMs !== null && row.processingMs !== undefined) { {{ row.processingMs / 1000 | number:'1.1-1' }}s }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

          <div class="flex justify-end">
            <ui-button variant="secondary" (click)="cancelProcessing()">Cancelar processamento</ui-button>
          </div>
        </div>
      }

    </div>
  `,
})
export class NewTranslationPage implements OnDestroy {
  private readonly router = inject(Router);
  private readonly foldersApi = inject(FoldersApi);
  private readonly pagesApi = inject(PagesApi);
  private readonly notifications = inject(NotificationService);

  readonly appState = signal<AppState>('selecao');
  readonly accepted = signal<AcceptedFile[]>([]);
  readonly ignored = signal<IgnoredFile[]>([]);
  folderName = '';
  readonly conflictSuggestion = signal<string | null>(null);
  readonly showIgnored = signal(false);

  readonly processed = signal(0);
  readonly total = signal(0);
  readonly successCount = signal(0);
  readonly errorCountProcessing = signal(0);
  readonly currentFile = signal('');
  readonly timeRemaining = signal('');
  readonly imageRows = signal<ImageRow[]>([]);

  private folderId = '';
  private abortController: AbortController | null = null;
  private durations: number[] = [];
  private processingStart = 0;

  readonly processedLabel = computed(() => `${this.processed()} de ${this.total()}`);

  readonly canStart = computed(() => this.accepted().length > 0 && this.folderName.trim().length > 0);

  onFilesSelected(files: File[]) {
    const accepted: AcceptedFile[] = [];
    const ignored: IgnoredFile[] = [];

    for (const file of files) {
      const pathParts = (file as File & { webkitRelativePath?: string }).webkitRelativePath?.split('/') ?? [];
      const depth = pathParts.length;
      if (depth > 2) {
        ignored.push({ name: file.name, reason: 'está em subpasta' });
        continue;
      }
      const reason = ignoreReason(file);
      if (reason) {
        ignored.push({ name: file.name, reason });
      } else {
        accepted.push({ file, pageNumber: 0 });
      }
    }

    accepted.sort((a, b) => collator.compare(a.file.name, b.file.name));
    accepted.forEach((f, i) => (f.pageNumber = i + 1));

    const firstPath = (files[0] as File & { webkitRelativePath?: string })?.webkitRelativePath ?? '';
    this.folderName = firstPath.split('/')[0] ?? '';
    this.conflictSuggestion.set(null);
    this.accepted.set(accepted);
    this.ignored.set(ignored);
    this.showIgnored.set(false);
  }

  toggleIgnored() {
    this.showIgnored.update((v) => !v);
  }

  cancelSelection() {
    this.accepted.set([]);
    this.ignored.set([]);
    this.folderName = '';
    this.conflictSuggestion.set(null);
  }

  useSuggestion() {
    const s = this.conflictSuggestion();
    if (s) {
      this.folderName = s;
      this.conflictSuggestion.set(null);
    }
  }

  async startProcessing() {
    if (!this.canStart()) return;
    this.conflictSuggestion.set(null);

    this.foldersApi.create(this.folderName.trim()).subscribe({
      next: (folder) => {
        this.folderId = folder.id;
        this.runUploadLoop(this.accepted());
      },
      error: (err) => {
        if (err?.status === 409) {
          this.conflictSuggestion.set(`${this.folderName.trim()} (2)`);
        }
      },
    });
  }

  private runUploadLoop(files: AcceptedFile[]) {
    this.appState.set('processando');
    this.total.set(files.length);
    this.processed.set(0);
    this.successCount.set(0);
    this.errorCountProcessing.set(0);
    this.currentFile.set('');
    this.timeRemaining.set('');
    this.durations = [];
    this.processingStart = Date.now();
    this.abortController = new AbortController();
    this.imageRows.set(files.map(f => ({ file: f.file, pageNumber: f.pageNumber, status: 'pending' })));

    this.processNext(files, 0);
  }

  private async processNext(files: AcceptedFile[], index: number): Promise<void> {
    if (this.abortController?.signal.aborted || index >= files.length) {
      if (!this.abortController?.signal.aborted) {
        this.router.navigate(['/pastas', this.folderId]);
      }
      return;
    }

    const item = files[index];
    const start = Date.now();
    this.currentFile.set(item.file.name);
    this.imageRows.update(rows =>
      rows.map(r => r.pageNumber === item.pageNumber ? { ...r, status: 'processing' as const } : r)
    );

    try {
      const { page_id } = await new Promise<{ page_id: string }>((resolve, reject) => {
        this.pagesApi.process(this.folderId, item.file, item.pageNumber).subscribe({
          next: (res) => resolve({ page_id: res.page_id ?? '' }),
          error: reject,
        });
      });

      let blocks = 0;
      let tokensUsed: number | undefined;
      let processingMs: number | undefined;
      if (page_id) {
        const ev = await this.pagesApi.waitForEvent(page_id);
        blocks = ev.block_count ?? 0;
        tokensUsed = ev.tokens_used;
        processingMs = ev.processing_ms;
        this.notifications.add(
          `Página ${item.pageNumber} concluída`,
          `${item.file.name} — ${blocks} bloco${blocks !== 1 ? 's' : ''} detectado${blocks !== 1 ? 's' : ''}`,
          'success',
        );
      }

      this.imageRows.update(rows =>
        rows.map(r => r.pageNumber === item.pageNumber
          ? { ...r, status: 'done' as const, blockCount: blocks, tokensUsed, processingMs }
          : r)
      );
      this.trackDuration(Date.now() - start);
      this.successCount.update((n) => n + 1);
    } catch (err) {
      const msg = extractErrorMessage(err);
      this.imageRows.update(rows =>
        rows.map(r => r.pageNumber === item.pageNumber ? { ...r, status: 'error' as const, errorMsg: msg } : r)
      );
      this.notifications.add(
        `Erro na página ${item.pageNumber}`,
        `${item.file.name} — ${msg}`,
        'error',
      );
      this.errorCountProcessing.update((n) => n + 1);
    }

    this.processed.update((n) => n + 1);
    this.updateTimeRemaining(files.length - index - 1);
    await this.processNext(files, index + 1);
  }

  private trackDuration(ms: number) {
    this.durations.push(ms);
    if (this.durations.length > 5) this.durations.shift();
  }

  private updateTimeRemaining(remaining: number) {
    if (this.durations.length < 2 || remaining === 0) {
      this.timeRemaining.set('');
      return;
    }
    const avg = this.durations.reduce((a, b) => a + b, 0) / this.durations.length;
    const seconds = Math.round((avg * remaining) / 1000);
    if (seconds < 60) {
      this.timeRemaining.set(`~ ${seconds} s restantes`);
    } else {
      this.timeRemaining.set(`~ ${Math.round(seconds / 60)} min restantes`);
    }
  }

  cancelProcessing() {
    this.abortController?.abort();
    this.appState.set('selecao');
    this.currentFile.set('');
  }

  ngOnDestroy() {
    this.abortController?.abort();
  }
}
