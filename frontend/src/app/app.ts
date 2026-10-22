import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AppHeaderComponent } from './core/layout/app-header.component';
import { UiToastOutletComponent } from './shared/ui';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, AppHeaderComponent, UiToastOutletComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {}
