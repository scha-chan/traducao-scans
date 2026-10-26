/* Gerado automaticamente a partir de contracts/page-export.schema.json.
 * Não edite este arquivo — execute `npm run generate:contracts`. */

/**
 * Posição na ordem de leitura, a partir de 1.
 */
export type Ordem = number;
export type Tipo = '#' | '$';
export type Original = string;
export type Localizacao = string;
export type Traducao = string;
export type Observacao = string;
export type Relevancia = number;
export type Traducoes = TranslationSuggestionExport[];
export type RootModelListTextBlockExport = TextBlockExport[];

/**
 * Um bloco de texto detectado na página.
 */
export interface TextBlockExport {
  ordem: Ordem;
  tipo: Tipo;
  original: Original;
  localizacao: Localizacao;
  traducoes: Traducoes;
}
/**
 * Uma sugestão de tradução para um bloco de texto.
 */
export interface TranslationSuggestionExport {
  traducao: Traducao;
  observacao: Observacao;
  relevancia: Relevancia;
}
