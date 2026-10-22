import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { FoldersApi } from '../../core/api/folders.api';
import { FolderSummary } from '../../core/api/models';
import { buildFolderTxt, downloadTxt, txtFileName } from '../../export/txt-export';
import { UiBadgeComponent } from '../../shared/ui/ui-badge.component';
import { UiButtonComponent } from '../../shared/ui/ui-button.component';
import { UiDialogComponent } from '../../shared/ui/ui-dialog.component';
import { UiEmptyStateComponent } from '../../shared/ui/ui-empty-state.component';
import { UiSkeletonRowsComponent } from '../../shared/ui/ui-skeleton-rows.component';

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
  templateUrl: './folder-list.page.html',
  styleUrl: './folder-list.page.scss',
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

  private readonly downloadingIds = signal<string[]>([]);

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

  isDownloading(folderId: string): boolean {
    return this.downloadingIds().includes(folderId);
  }

  downloadFolderTxt(folder: FolderSummary): void {
    if (this.isDownloading(folder.id)) return;
    this.downloadingIds.update((ids) => [...ids, folder.id]);
    this.foldersApi.export(folder.id).subscribe({
      next: (data) => {
        downloadTxt(buildFolderTxt(data), txtFileName(folder.name));
        this.downloadingIds.update((ids) => ids.filter((id) => id !== folder.id));
      },
      error: () => {
        this.downloadingIds.update((ids) => ids.filter((id) => id !== folder.id));
      },
    });
  }

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
