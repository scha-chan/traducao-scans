import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiBase } from '../http/api-base';
import { ApproveResponse, AnalyzeResponse, BlockOut, FolderDetail, PageEvent, PageSummary, TextBlockExport, RunOut, ReorderAutoOut, RegenerateResponse } from './models';

@Injectable({ providedIn: 'root' })
export class PagesApi extends ApiBase {
  process(folderId: string, file: File, pageNumber: number): Observable<AnalyzeResponse> {
    const body = new FormData();
    body.append('file', file);
    body.append('page_number', String(pageNumber));
    return this.http.post<AnalyzeResponse>(
      this.url(`/api/folders/${folderId}/pages/process`),
      body
    );
  }

  reprocess(pageId: string): Observable<AnalyzeResponse> {
    return this.http.post<AnalyzeResponse>(
      this.url(`/api/pages/${pageId}/process?force=true`),
      null
    );
  }

  events(pageId: string): EventSource {
    return new EventSource(this.url(`/api/pages/${pageId}/events`));
  }

  waitForEvent(pageId: string): Promise<PageEvent> {
    return new Promise((resolve, reject) => {
      const es = this.events(pageId);
      es.onmessage = ({ data }) => {
        const ev: PageEvent = JSON.parse(data);
        if (ev.event === 'done' || ev.event === 'error') {
          es.close();
          if (ev.event === 'done') { resolve(ev); } else { reject(new Error(ev.message ?? 'Erro no processamento')); }
        }
      };
      es.onerror = () => { es.close(); reject(new Error('Conexão SSE perdida')); };
    });
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

  analyze(pageId: string): Observable<AnalyzeResponse> {
    return this.http.post<AnalyzeResponse>(this.url(`/api/pages/${pageId}/analyze`), null);
  }

  analyzeForce(pageId: string): Observable<AnalyzeResponse> {
    return this.http.post<AnalyzeResponse>(this.url(`/api/pages/${pageId}/analyze?force=true`), null);
  }

  getRuns(pageId: string): Observable<RunOut[]> {
    return this.http.get<RunOut[]>(this.url(`/api/pages/${pageId}/runs`));
  }

  reorderAuto(pageId: string): Observable<ReorderAutoOut> {
    return this.http.post<ReorderAutoOut>(this.url(`/api/pages/${pageId}/reorder/auto`), null);
  }

  regenerate(pageId: string): Observable<RegenerateResponse> {
    return this.http.post<RegenerateResponse>(this.url(`/api/pages/${pageId}/regenerate`), null);
  }

  getBlocks(pageId: string): Observable<BlockOut[]> {
    return this.http.get<BlockOut[]>(this.url(`/api/pages/${pageId}/blocks`));
  }

  toggleBlockReviewed(blockId: string): Observable<BlockOut> {
    return this.http.post<BlockOut>(this.url(`/api/blocks/${blockId}/toggle-reviewed`), null);
  }

  approve(pageId: string): Observable<ApproveResponse> {
    return this.http.post<ApproveResponse>(this.url(`/api/pages/${pageId}/approve`), null);
  }

  getFolder(folderId: string): Observable<FolderDetail> {
    return this.http.get<FolderDetail>(this.url(`/api/folders/${folderId}`));
  }
}
