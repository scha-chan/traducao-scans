import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiBase } from '../http/api-base';
import { PageSummary, TextBlockExport, ProcessPageResponse } from './models';

@Injectable({ providedIn: 'root' })
export class PagesApi extends ApiBase {
  process(folderId: string, file: File, pageNumber: number): Observable<ProcessPageResponse> {
    const body = new FormData();
    body.append('file', file);
    body.append('page_number', String(pageNumber));
    return this.http.post<ProcessPageResponse>(
      this.url(`/api/folders/${folderId}/pages/process`),
      body
    );
  }

  reprocess(pageId: string): Observable<ProcessPageResponse> {
    return this.http.post<ProcessPageResponse>(
      this.url(`/api/pages/${pageId}/process?force=true`),
      null
    );
  }

  getJson(pageId: string): Observable<TextBlockExport[]> {
    return this.http.get<TextBlockExport[]>(this.url(`/api/pages/${pageId}/json`));
  }

  saveJson(pageId: string, blocos: TextBlockExport[]): Observable<TextBlockExport[]> {
    return this.http.put<TextBlockExport[]>(this.url(`/api/pages/${pageId}/json`), blocos);
  }

  thumbnailUrl(page: PageSummary): string {
    return this.url(page.thumbnail_url);
  }

  imageUrl(page: PageSummary): string {
    return this.url(page.image_url);
  }
}
