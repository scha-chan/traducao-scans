// Tipos do contrato importados do arquivo gerado a partir de contracts/page-export.schema.json.
// Não altere TranslationSuggestionExport aqui — edite o modelo Pydantic em contracts/models.py.
export type {
  TranslationSuggestionExport,
  RootModelListTextBlockExport as PageBlocks,
} from './contracts';
import type {
  TextBlockExport as ContractTextBlock,
  TranslationSuggestionExport,
} from './contracts';

// Alias de compatibilidade: o código Angular usa o nome "Translation".
export type Translation = TranslationSuggestionExport;

// Extensão frontend-only: bbox em pixels para o overlay SVG (não faz parte do schema da API).
export interface BboxPx {
  x: number;
  y: number;
  w: number;
  h: number;
}

// TextBlockExport estende o contrato gerado com o campo opcional de bounding-box.
export interface TextBlockExport extends ContractTextBlock {
  bbox?: BboxPx;
}

export type PageStatus = 'PENDING' | 'PROCESSING' | 'REVIEW' | 'APPROVED' | 'ERROR';
export type FolderStatus = 'PROCESSING' | 'DONE' | 'DONE_WITH_ERRORS' | 'INCOMPLETE';

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
