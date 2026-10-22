import { Component, input } from '@angular/core';

@Component({
  selector: 'ui-empty-state',
  standalone: true,
  templateUrl: './ui-empty-state.component.html',
  styleUrl: './ui-empty-state.component.scss',
})
export class UiEmptyStateComponent {
  readonly icon = input<'folder' | 'search' | 'info'>('folder');
  readonly title = input('Nenhum item encontrado');
  readonly description = input('');
}
