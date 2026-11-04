import { TestBed } from '@angular/core/testing';
import { ComponentRef } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PageReviewModalComponent } from './page-review-modal.component';
import { FolderDetail, PageSummary, TextBlockExport, ProcessPageResponse, RegenerateResponse } from '../../core/api/models';

const mockPage: PageSummary = {
  id: 'page-1', page_number: 1, file_name: 'p001.jpg', status: 'REVIEW',
  block_count: 2, edited: false, thumbnail_url: '/thumb/1', image_url: '/image/1',
};
const mockFolder: FolderDetail = {
  id: 'folder-1', name: 'Test Manga', status: 'DONE',
  total_pages: 1, processed_pages: 1, error_pages: 0,
  updated_at: '2026-01-01T00:00:00Z', pages: [mockPage],
};
const mockBlock: TextBlockExport = {
  tipo: '#', ordem: 1, original: '元の文',
  traducoes: [{ traducao: 'Original text', observacao: '', relevancia: 3 }],
  localizacao: '',
};
function createFixture() {
  const fixture = TestBed.createComponent(PageReviewModalComponent);
  const ref: ComponentRef<PageReviewModalComponent> = fixture.componentRef;
  ref.setInput('folder', mockFolder);
  ref.setInput('page', mockPage);
  fixture.detectChanges();
  return fixture;
}
describe('PageReviewModalComponent', () => {
  let httpMock: HttpTestingController;
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PageReviewModalComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    const pending = httpMock.match(() => true);
    pending.forEach((req) => req.flush([]));
    httpMock.verify();
  });
  it('shows reprocess confirmation dialog on click', async () => {
    const fixture = createFixture();
    httpMock.expectOne((req) => req.url.includes('/json')).flush([mockBlock]);
    await fixture.whenStable();
    fixture.detectChanges();
    const comp = fixture.componentInstance;
    expect(comp.reprocessDialogOpen()).toBe(false);
    comp.onReprocessClick();
    fixture.detectChanges();
    expect(comp.reprocessDialogOpen()).toBe(true);
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('[aria-labelledby="reprocess-dialog-title"]')).toBeTruthy();
  });
  it('cancels reprocess without API call', async () => {
    const fixture = createFixture();
    httpMock.expectOne((req) => req.url.includes('/json')).flush([]);
    await fixture.whenStable();
    fixture.detectChanges();
    const comp = fixture.componentInstance;
    comp.onReprocessClick();
    fixture.detectChanges();
    expect(comp.reprocessDialogOpen()).toBe(true);
    comp.cancelReprocess();
    fixture.detectChanges();
    expect(comp.reprocessDialogOpen()).toBe(false);
    httpMock.expectNone((req) => req.url.includes('process'));
  });
  it('shows loading overlay during reprocess', async () => {
    const fixture = createFixture();
    httpMock.expectOne((req) => req.url.includes('/json')).flush([]);
    await fixture.whenStable();
    fixture.detectChanges();
    const comp = fixture.componentInstance;
    comp.onReprocessClick();
    comp.confirmReprocess();
    fixture.detectChanges();
    expect(comp.reprocessing()).toBe(true);
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('[aria-live="polite"]')).toBeTruthy();
    const reprocessReq = httpMock.expectOne((req) => req.url.includes('process'));
    const response: ProcessPageResponse = { page: mockPage, blocos: [mockBlock] };
    reprocessReq.flush(response);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(comp.reprocessing()).toBe(false);
  });
  it('updates form on successful reprocess', async () => {
    const fixture = createFixture();
    httpMock.expectOne((req) => req.url.includes('/json')).flush([]);
    await fixture.whenStable();
    fixture.detectChanges();
    const comp = fixture.componentInstance;
    const reprocessedEvents: PageSummary[] = [];
    comp.pageReprocessed.subscribe((p) => reprocessedEvents.push(p));
    comp.onReprocessClick();
    comp.confirmReprocess();
    const reprocessReq = httpMock.expectOne((req) => req.url.includes('process'));
    const newPage: PageSummary = { ...mockPage, block_count: 3, edited: false };
    const response: ProcessPageResponse = { page: newPage, blocos: [mockBlock] };
    reprocessReq.flush(response);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(comp.blocks()).toHaveLength(1);
    expect(comp.reprocessing()).toBe(false);
    expect(reprocessedEvents).toHaveLength(1);
    expect(reprocessedEvents[0].block_count).toBe(3);
  });
  it('calls regenerate API on regenerate click', async () => {
    const fixture = createFixture();
    httpMock.expectOne((req) => req.url.includes('/json')).flush([]);
    await fixture.whenStable();
    fixture.detectChanges();
    const comp = fixture.componentInstance;
    const reprocessedEvents: PageSummary[] = [];
    comp.pageReprocessed.subscribe((p) => reprocessedEvents.push(p));
    comp.onRegenerateClick();
    fixture.detectChanges();
    expect(comp.regenerating()).toBe(true);
    const regenerateReq = httpMock.expectOne((req) => req.url.includes('regenerate'));
    const response: RegenerateResponse = { page: mockPage, blocos: [mockBlock], cost_usd: 0.0012 };
    regenerateReq.flush(response);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(comp.regenerating()).toBe(false);
    expect(comp.blocks()).toHaveLength(1);
    expect(reprocessedEvents).toHaveLength(1);
  });
});
