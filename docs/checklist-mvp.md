# Checklist MVP — Critérios de Aceite (§26)

> Verificado em: 2026-11-04 · Branch: `feat/f6-qa-02-checklist-mvp`

## Status geral

✅ Todos os 16 critérios verificados manualmente.

---

## §26 — Critérios de aceite

| # | Critério | Status | Evidência |
|---|---|---|---|
| 1 | Consigo criar uma pasta e cadastrar páginas. | ✅ | `POST /api/folders` + `POST /api/folders/{id}/pages/process` funcionam. |
| 2 | Consigo ver o nome do arquivo de cada página. | ✅ | `file_name` exibido no modal e na grade de miniaturas. |
| 3 | Consigo executar a análise de uma página. | ✅ | Botão Analisar → `POST /api/pages/{id}/analyze` → status `PROCESSING → REVIEW`. |
| 4 | O agente detecta os textos e cria blocos persistidos no banco. | ✅ | Blocos persistidos via `TextBlock` no PostgreSQL; `GET /api/pages/{id}/blocks` confirma. |
| 5 | Cada bloco tem original, tipo, localização e ordem. | ✅ | Campos `original`, `type`, `location`, `order_number` em `TextBlock`. |
| 6 | A ordem segue direita → esquerda e cima → baixo. | ✅ | `tiered_column_rtl` implementado em F4-AG-01; métricas 100% corretas (ver `docs/metricas.md`). |
| 7 | Cada bloco tem pelo menos uma sugestão de tradução. | ✅ | Guardrail F5-AG-07 garante ≥ 1 sugestão por bloco. |
| 8 | Cada sugestão tem `traducao`, `observacao` e `relevancia`. | ✅ | Schema Pydantic `SuggestionIn` valida os três campos. |
| 9 | Consigo editar OCR, tipo, localização, ordem e traduções. | ✅ | Modal de revisão com aba Editar + drag-and-drop na aba Ordenação. |
| 10 | O frontend mostra as regiões numeradas sobre a imagem. | ✅ | `PageImageViewerComponent` desenha bboxes numerados sobre a imagem. |
| 11 | O backend gera um JSON válido, exatamente no contrato definido. | ✅ | `GET /api/pages/{id}/json` retorna `TextBlockExport[]` conforme `page-export.schema.json`. |
| 12 | Depois de recarregar, os resultados continuam disponíveis. | ✅ | Persistência via SQLAlchemy + PostgreSQL; testado com reload manual. |
| 13 | Consigo exportar o JSON da página. | ✅ | Aba "Exportar JSON" no modal (F6-FE-04): baixar e copiar. |
| 14 | **(Revisão)** Consigo criar e excluir blocos manualmente. | ✅ | Modo "Adicionar região" no viewer; `DELETE /api/blocks/{id}` no backend. |
| 15 | **(Revisão)** Consigo aprovar a página e a política de baixa confiança é respeitada. | ✅ | `POST /api/pages/{id}/approve` com `EXPORT_BLOCK_ON_LOW_CONFIDENCE` (F6-BE-01). |
| 16 | **(Revisão)** Reanalisar página revisada exige confirmação e não duplica blocos. | ✅ | Diálogo de confirmação no modal; `force=true` limpa blocos antes de reanalisar. |

---

## Acessibilidade por teclado (§25 + §20)

Fluxo completo sem mouse verificado na tela de revisão:

| Ação | Tecla(s) | Verificado |
|---|---|---|
| Navegar para próximo bloco | `J` | ✅ |
| Navegar para bloco anterior | `K` | ✅ |
| Alternar tipo `#`/`$` do bloco selecionado | `T` | ✅ |
| Marcar bloco como revisado | `R` | ✅ |
| Ligar/desligar filtro "somente pendentes" | `F` | ✅ |
| Ir para página anterior | `←` | ✅ |
| Ir para página seguinte | `→` | ✅ |
| Mover bloco na ordenação (aba Ordenação) | `Alt+↑` / `Alt+↓` | ✅ |
| Fechar modal | `Escape` | ✅ |
| Salvar | `Ctrl+S` | ✅ |
| Focus trap dentro do modal | `Tab` / `Shift+Tab` | ✅ |

> Legenda de atalhos visível no footer do modal via `ui-kbd-legend` (F6-FE-03).

---

## Contraste e paleta

- Tailwind `red` como cor primária, tokens em `--color-primary-*` (§27).
- Contraste AA verificado: botão primário `bg-primary-600 text-white` → ratio ≥ 4.5:1.
- Suporte a dark mode: tokens redefinidos via `.dark` variant.
