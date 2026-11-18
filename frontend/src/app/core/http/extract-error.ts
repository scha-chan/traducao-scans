/** Extrai uma mensagem legível de qualquer tipo de erro.
 *
 * HttpErrorResponse do Angular implementa a interface Error mas não estende
 * a classe Error, portanto `instanceof Error` retorna false. Esta função
 * trata todos os casos: Error nativo, HttpErrorResponse, string, etc.
 */
export function extractErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (err && typeof err === 'object') {
    const e = err as Record<string, unknown>;
    // FastAPI retorna { detail: string | object }
    if (e['error'] && typeof e['error'] === 'object') {
      const detail = (e['error'] as Record<string, unknown>)['detail'];
      if (detail !== undefined) return String(detail);
    }
    if (typeof e['error'] === 'string' && e['error']) return e['error'];
    if (typeof e['message'] === 'string' && e['message']) return e['message'];
    if (typeof e['status'] === 'number') return `Erro HTTP ${e['status']}`;
  }
  if (typeof err === 'string' && err) return err;
  return 'Erro desconhecido';
}
