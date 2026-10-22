import { Component, input, computed } from '@angular/core';

@Component({
  selector: 'ui-progress',
  standalone: true,
  templateUrl: './ui-progress.component.html',
  styleUrl: './ui-progress.component.scss',
})
export class UiProgressComponent {
  readonly value = input(0);
  readonly max = input(100);
  readonly label = input('');
  readonly sublabel = input('');
  readonly ariaLabel = input('Progresso');

  readonly percent = computed(() =>
    this.max() > 0 ? Math.min(100, (this.value() / this.max()) * 100) : 0
  );
}
