import {
  Component,
  input,
  output,
  signal,
  ViewChild,
  ElementRef,
} from '@angular/core';

@Component({
  selector: 'ui-dropzone',
  standalone: true,
  template: `
    <div
      class="relative flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed p-10 text-center transition-colors"
      [class.border-primary-400]="dragging()"
      [class.bg-primary-50]="dragging()"
      [class.dark:bg-primary-950]="dragging()"
      [class.border-zinc-300]="!dragging()"
      [class.dark:border-zinc-700]="!dragging()"
      (dragover)="onDragOver($event)"
      (dragleave)="onDragLeave()"
      (drop)="onDrop($event)"
    >
      <svg class="size-12 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
      </svg>

      <div class="flex flex-col gap-2">
        <p class="text-base font-medium text-zinc-700 dark:text-zinc-300">
          {{ label() }}
        </p>
        <p class="text-sm text-zinc-500 dark:text-zinc-400">
          ou arraste a pasta aqui
        </p>
      </div>

      <button
        type="button"
        (click)="fileInput.click()"
        class="inline-flex items-center gap-2 rounded-lg px-4 py-2 bg-primary-600 hover:bg-primary-700 active:bg-primary-800 text-white font-medium text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 ring-primary-500 ring-offset-2"
      >
        Escolher pasta
      </button>

      <input
        #fileInput
        type="file"
        webkitdirectory
        multiple
        class="hidden"
        [attr.accept]="accept()"
        (change)="onFileChange($event)"
      />
    </div>
  `,
})
export class UiDropzoneComponent {
  readonly label = input('Selecione uma pasta com as imagens');
  readonly accept = input<string | null>(null);
  readonly filesSelected = output<File[]>();

  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  readonly dragging = signal(false);

  onDragOver(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    this.dragging.set(true);
  }

  onDragLeave() {
    this.dragging.set(false);
  }

  onDrop(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    this.dragging.set(false);

    const items = e.dataTransfer?.items;
    if (!items) return;

    const files: File[] = [];
    const promises: Promise<void>[] = [];

    for (const item of Array.from(items)) {
      const entry = item.webkitGetAsEntry?.();
      if (entry?.isDirectory) {
        promises.push(this.readDirEntry(entry as FileSystemDirectoryEntry, files));
      } else if (entry?.isFile) {
        promises.push(
          new Promise<void>((resolve) => {
            (entry as FileSystemFileEntry).file((f) => {
              files.push(f);
              resolve();
            });
          })
        );
      }
    }

    Promise.all(promises).then(() => {
      if (files.length) this.filesSelected.emit(files);
    });
  }

  onFileChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files?.length) {
      this.filesSelected.emit(Array.from(input.files));
    }
  }

  private readDirEntry(dir: FileSystemDirectoryEntry, acc: File[]): Promise<void> {
    return new Promise((resolve) => {
      const reader = dir.createReader();
      reader.readEntries((entries) => {
        const promises = entries
          .filter((e) => e.isFile)
          .map(
            (e) =>
              new Promise<void>((res) => {
                (e as FileSystemFileEntry).file((f) => {
                  acc.push(f);
                  res();
                });
              })
          );
        Promise.all(promises).then(() => resolve());
      });
    });
  }
}
