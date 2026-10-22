import { Component, input } from '@angular/core';

@Component({
  selector: 'ui-skeleton',
  standalone: true,
  templateUrl: './ui-skeleton.component.html',
  styleUrl: './ui-skeleton.component.scss',
})
export class UiSkeletonComponent {
  readonly height = input('h-4');
  readonly width = input('w-full');

  readonly heightClass = this.height;
  readonly widthClass = this.width;
}
