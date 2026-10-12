// Modelos gerados a partir do contrato da seção 10.1 da especificação

export type PageStatus = 'PENDING' | 'PROCESSING' | 'REVIEW' | 'APPROVED' | 'ERROR';
export type FolderStatus = 'PROCESSING' | 'DONE' | 'DONE_WITH_ERRORS' | 'INCOMPLETE';

export interface Translation {
  traducao: string;
  observacao: string;
  relevancia: 1 | 2 | 3 | 4 | 5;
}

export interface TextBlockExport {
  ordem: number;
  tipo: '#' | '$';
  original: string;
  localizacao: string;
  traducoes: Translation[];
}

export interface FolderSummary {
  id: string;
  name: string;
  status: FolderStatus;
  total_pages: number;
  processed_pages: number;
  error_pages: number;
  updated_at: string;
}

export interface PageSummary {
  id: string;
  page_number: number;
  file_name: string;
  status: PageStatus;
  block_count: number;
  edited: boolean;
  thumbnail_url: string;
  image_url: string;
  error_message?: string;
}

export interface FolderDetail extends FolderSummary {
  pages: PageSummary[];
}

export interface ProcessPageResponse {
  page: PageSummary;
  blocos: TextBlockExport[];
}

export interface PageExport {
  pagina: number;
  arquivo: string;
  status: PageStatus;
  blocos: TextBlockExport[] | null;
}

export interface FolderExport {
  pasta: string;
  paginas: PageExport[];
}
