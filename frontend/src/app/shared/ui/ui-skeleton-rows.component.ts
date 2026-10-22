import { Component, input } from '@angular/core';
import { UiSkeletonComponent } from './ui-skeleton.component';

@Component({
  selector: 'ui-skeleton-rows',
  standalone: true,
  imports: [UiSkeletonComponent],
  templateUrl: './ui-skeleton-rows.component.html',
  styleUrl: './ui-skeleton-rows.component.scss',
})
export class UiSkeletonRowsComponent {
  readonly count = input(5);
  readonly rows = () => Array.from({ length: this.count() });
}
