import { inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

export abstract class ApiBase {
  protected readonly http = inject(HttpClient);

  protected url(path: string): string {
    return `${environment.apiBaseUrl}${path}`;
  }
}
