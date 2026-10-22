import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiBase } from '../http/api-base';
import { FolderSummary, FolderDetail, FolderExport } from './models';

@Injectable({ providedIn: 'root' })
export class FoldersApi extends ApiBase {
  list(): Observable<FolderSummary[]> {
    return this.http.get<FolderSummary[]>(this.url('/api/folders'));
  }

  create(name: string): Observable<FolderSummary> {
    return this.http.post<FolderSummary>(this.url('/api/folders'), { name });
  }

  get(id: string): Observable<FolderDetail> {
    return this.http.get<FolderDetail>(this.url(`/api/folders/${id}`));
  }

  rename(id: string, name: string): Observable<FolderSummary> {
    return this.http.patch<FolderSummary>(this.url(`/api/folders/${id}`), { name });
  }

  remove(id: string): Observable<void> {
    return this.http.delete<void>(this.url(`/api/folders/${id}`));
  }

  export(id: string): Observable<FolderExport> {
    return this.http.get<FolderExport>(this.url(`/api/folders/${id}/export`));
  }
}
