import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiBase } from '../http/api-base';
import { WorkSummary } from './models';

@Injectable({ providedIn: 'root' })
export class WorksApi extends ApiBase {
  get(id: string): Observable<WorkSummary> {
    return this.http.get<WorkSummary>(this.url(`/api/works/${id}`));
  }
}
