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
  templateUrl: './ui-dropzone.component.html',
  styleUrl: './ui-dropzone.component.scss',
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
