# Especificação do Frontend — Manga Translator Agent

> **Stack:** Angular (standalone components + signals) • TypeScript strict • Tailwind CSS v4 (paleta `red`, tokens `primary-*`)
> **Documento pai:** [PRD_Agente_Traducao_Manga_Japones.md](PRD_Agente_Traducao_Manga_Japones.md). O design system está na seção 27 do PRD e o contrato JSON na seção 13.
> **Versão:** 1.0 — 2026-09-24

Este documento detalha o fluxo do frontend orientado a **pastas locais**. Ele substitui as seções 19 e 20 do PRD no que for conflitante (ver a seção 11, "Impactos no PRD e no backend").

---

## Sumário

1. [Visão geral do fluxo](#1-visão-geral-do-fluxo)
2. [Rotas](#2-rotas)
3. [Layout global](#3-layout-global)
4. [Tela 1 — Lista de pastas (página inicial)](#4-tela-1--lista-de-pastas-página-inicial)
5. [Tela 2 — Nova tradução (seleção + processamento)](#5-tela-2--nova-tradução-seleção--processamento)
6. [Tela 3 — Detalhe da pasta (miniaturas)](#6-tela-3--detalhe-da-pasta-miniaturas)
7. [Modal de conferência e edição](#7-modal-de-conferência-e-edição)
8. [Arquivo TXT final](#8-arquivo-txt-final)
9. [Arquitetura Angular](#9-arquitetura-angular)
10. [Contratos consumidos da API](#10-contratos-consumidos-da-api)
11. [Impactos no PRD e no backend](#11-impactos-no-prd-e-no-backend)
12. [Estados, erros e casos-limite](#12-estados-erros-e-casos-limite)
13. [Acessibilidade e responsividade](#13-acessibilidade-e-responsividade)
14. [Cards de entrega do frontend](#14-cards-de-entrega-do-frontend)
15. [Questões em aberto](#15-questões-em-aberto)

---

## 1. Visão geral do fluxo

```
┌───────────────────────┐   "Nova tradução"   ┌──────────────────────────────┐
│ 1. Lista de pastas     │ ──────────────────> │ 2. Nova tradução              │
│ (página inicial)       │                     │  a) selecionar pasta local    │
│  • Baixar TXT          │                     │  b) filtrar imagens           │
│  • Abrir pasta         │                     │  c) processar: "5 de 30"      │
└──────────┬────────────┘                     └──────────────┬───────────────┘
           │ abrir                                           │ término
           ▼                                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 3. Detalhe da pasta — grade de miniaturas  [Baixar TXT final]              │
│      clique na miniatura ─────> ┌───────────────────────────────────────┐ │
│                                 │ Modal: imagem 40% | tabela editável    │ │
│                                 │ footer: [Cancelar] [Salvar]            │ │
│                                 └───────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

1. O usuário abre a aplicação e vê a **lista de pastas já processadas**, cada uma com o botão **Baixar TXT**.
2. Ao clicar em **Nova tradução** (no topo), vai para a tela de seleção de uma **pasta local**.
3. O frontend lê os arquivos da pasta e **ignora o que não for imagem**.
4. As imagens são enviadas **uma a uma** ao backend, que devolve o **JSON da página**. Um loading mostra o progresso: **"5 de 30"**.
5. Ao terminar, o usuário vai para a **grade de miniaturas** da pasta.
6. Clicar numa miniatura abre um **modal**: a imagem à esquerda (40%) e a **tabela editável** à direita. As alterações são salvas pelo botão **Salvar** no footer.
7. Na grade há o botão **Baixar TXT final**, que junta todas as páginas em um único arquivo.

## 2. Rotas

| Rota | Componente | Descrição |
|---|---|---|
| `/` | `FolderListPage` | Página inicial: lista de pastas processadas. |
| `/nova-traducao` | `NewTranslationPage` | Seleção da pasta local e processamento. |
| `/pastas/:folderId` | `FolderDetailPage` | Grade de miniaturas + download do TXT. |
| `/pastas/:folderId?pagina=:n` | `FolderDetailPage` + modal aberto | Deep link: recarregar a página mantém o modal aberto na página `n`. |
| `**` | redireciona para `/` | — |

Guard: `NewTranslationPage` implementa `CanDeactivate` e pede confirmação para sair durante o processamento (ver a seção 5.4).

## 3. Layout global

```
┌──────────────────────────────────────────────────────────────────────┐
│ [logo] Manga Translator                          [ + Nova tradução ] │  ← header fixo
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                          <router-outlet>                             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

| Elemento | Classes Tailwind |
|---|---|
| Header | `sticky top-0 z-30 h-14 flex items-center justify-between px-4 md:px-6 bg-white/90 backdrop-blur border-b border-zinc-200 dark:bg-zinc-900/90 dark:border-zinc-800` |
| Botão "Nova tradução" | `inline-flex items-center gap-2 rounded-lg px-4 py-2 bg-primary-600 hover:bg-primary-700 active:bg-primary-800 text-white font-medium focus-visible:ring-2 ring-primary-500 ring-offset-2` |
| Conteúdo | `mx-auto max-w-7xl px-4 md:px-6 py-6` |
| Fundo | `bg-zinc-50 dark:bg-zinc-950 min-h-dvh` |

O botão **Nova tradução** fica **desabilitado** (com tooltip "Processamento em andamento") enquanto houver um processamento ativo na sessão.

## 4. Tela 1 — Lista de pastas (página inicial)

### 4.1 Wireframe

```
Pastas traduzidas                                   [🔍 Buscar pasta...]

┌──────────────────────────────────────────────────────────────────────┐
│ Nome           Páginas   Status            Atualizado     Ações      │
├──────────────────────────────────────────────────────────────────────┤
│ capitulo 1     30        ✔ Concluída       24/09 14:10   [Abrir] [⬇ TXT] │
│ capitulo 2     28        ⚠ 2 com erro      24/09 15:02   [Abrir] [⬇ TXT] │
│ capitulo 3     12/30     ⟳ Incompleta      24/09 15:40   [Abrir] [⬇ TXT] │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Comportamento

| Item | Regra |
|---|---|
| Fonte de dados | `GET /api/folders`, ordenado por `updated_at` decrescente. |
| Colunas | Nome, páginas (`processadas/total` quando incompleta), status, data da última atualização, ações. |
| Status da pasta | Calculado pelo backend (seção 10): **Concluída** (todas as páginas ok), **Com erros** (n páginas com erro), **Incompleta** (processamento interrompido). |
| Busca | Filtro local, sem diferenciar maiúsculas de minúsculas, pelo nome (debounce de 200 ms). |
| Clique na linha / "Abrir" | Navega para `/pastas/:folderId`. |
| **Baixar TXT** | Chama `GET /api/folders/{id}/export`, gera o TXT **no frontend** (seção 8) e dispara o download de `<nome da pasta>.txt`. Enquanto gera, o botão mostra um spinner e fica desabilitado. |
| TXT de pasta com erros ou incompleta | Permitido. As páginas sem resultado aparecem no TXT com um aviso (seção 8.3). Antes de baixar, um toast informa: "2 páginas sem tradução serão sinalizadas no arquivo". |
| Estado vazio | Ilustração + "Nenhuma pasta traduzida ainda" + botão primário **Nova tradução**. |
| Carregando | 5 linhas `ui-skeleton`. |
| Mobile (< md) | A tabela vira uma lista de cards (nome, badge de status e os botões Abrir e TXT). |

### 4.3 Badges de status (tokens da seção 27.4 do PRD)

| Status | Classes | Ícone |
|---|---|---|
| Concluída | `bg-emerald-100 text-emerald-800` | check |
| Com erros | `bg-amber-100 text-amber-800` | alerta |
| Incompleta | `bg-zinc-100 text-zinc-700` | relógio |
| Processando | `bg-primary-50 text-primary-700` | spinner |

## 5. Tela 2 — Nova tradução (seleção + processamento)

A tela tem **três estados**: `selecao` → `processando` → `concluido` (este último redireciona).

### 5.1 Estado `selecao`

```
Nova tradução

┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
         📁  Selecione uma pasta com as imagens
             [ Escolher pasta ]   ou arraste aqui
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘

Nome da pasta: [ capitulo 1                         ]   ← pré-preenchido, editável

✔ 30 imagens encontradas      ⚠ 4 arquivos ignorados [ver]
  001.jpg · 002.jpg · 003.jpg · … (lista rolável, em ordem de página)

                                   [Cancelar]  [ Iniciar tradução ]
```

**Seleção da pasta:**

| Item | Regra |
|---|---|
| Mecanismo | `<input type="file" webkitdirectory multiple hidden>` acionado pelo botão "Escolher pasta". Funciona em Chrome, Edge e Firefox. Também aceita arrastar e soltar uma pasta na dropzone (`DataTransferItem.webkitGetAsEntry()`). |
| Nome da pasta | O primeiro segmento de `file.webkitRelativePath` (por exemplo `capitulo 1/001.jpg` → `capitulo 1`). O campo é editável antes de iniciar, é obrigatório e aceita no máximo 120 caracteres. |
| Subpastas | **Ignoradas**: só os arquivos diretamente dentro da pasta selecionada são considerados. Os arquivos de subpastas contam como "ignorados", com o motivo "está em subpasta". |
| Filtro de imagem | Aceitos: extensão `.jpg`, `.jpeg`, `.png` ou `.webp` **e** `file.type` começando com `image/`. O backend revalida pelos *magic bytes*. |
| Ignorados automaticamente | Qualquer outra extensão (`.txt`, `.psd`, `.zip`, `.heic`…), arquivos ocultos ou de sistema (`.DS_Store`, `Thumbs.db`, `desktop.ini`, nomes começando com `.`), arquivos com 0 bytes e arquivos acima de 20 MB. |
| Lista de ignorados | Link "ver" abre um popover com o **nome do arquivo e o motivo** ("não é imagem", "arquivo oculto", "acima de 20 MB", "está em subpasta"). |
| Ordem das páginas | Ordenação **natural** pelo nome do arquivo (`Intl.Collator('pt-BR', { numeric: true, sensitivity: 'base' })`): `1.jpg, 2.jpg, 10.jpg`. A posição na lista é o **número da página** (1..N). |
| Sem imagens | Mensagem "Nenhuma imagem encontrada nesta pasta"; o botão Iniciar fica desabilitado. |
| Pasta grande | Acima de 200 imagens aparece um aviso não bloqueante: "Pastas grandes podem levar vários minutos". |
| Nome já existente | Ao iniciar, se `POST /api/folders` responder `409`, um inline error sugere `capitulo 1 (2)` com o botão "Usar este nome". |

### 5.2 Estado `processando`

```
Traduzindo "capitulo 1"

  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   5 de 30
  Processando: 006.jpg                          ~ 4 min restantes

  ✔ 5 concluídas   ⚠ 0 com erro

                                            [ Cancelar processamento ]
```

| Item | Regra |
|---|---|
| Início | 1) `POST /api/folders { name }` → `folderId`; 2) enfileirar as N imagens na ordem das páginas. |
| Envio | Para cada imagem: `POST /api/folders/{folderId}/pages/process` (multipart: `file`, `page_number`). A resposta traz o **JSON da página** (seção 10.3). |
| Concorrência | Padrão **1** (sequencial), configurável até 3 (`environment.processingConcurrency`). O contador funciona igual com qualquer concorrência. |
| Contador | **`<processadas> de <total>`**, em que *processadas* = sucesso + erro. Usa `tabular-nums` para os dígitos não "pularem". |
| Barra | `role="progressbar"` com `aria-valuenow`, `aria-valuemin=0` e `aria-valuemax=total`. Trilho `h-3 rounded-full bg-zinc-200 dark:bg-zinc-800`; preenchimento `bg-primary-600 transition-[width] duration-300`. |
| Arquivo atual | Mostra o nome da imagem em processamento. |
| Tempo restante | Média móvel das últimas 5 durações × restantes. Só aparece depois de 2 imagens concluídas. |
| Resultado por imagem | O JSON devolvido fica guardado no `ProcessingStore` (signal) e é **usado na grade** sem novo GET (seção 6). |
| Erro em uma imagem | **Não interrompe** a fila. A imagem é marcada como erro, o contador avança e "⚠ n com erro" é incrementado. Timeout de 180 s por imagem. |
| Retentativa automática | 1 retentativa para erros de rede e 5xx, com backoff de 3 s. Para 4xx não há retentativa. |
| Cancelar | Confirmação → aborta as requisições pendentes (`AbortController`/`takeUntil`) e navega para `/pastas/:folderId`. A pasta fica **Incompleta**. |

### 5.3 Estado `concluido`

- Um toast de sucesso: "30 páginas traduzidas", ou "28 traduzidas, 2 com erro".
- Redireciona automaticamente para `/pastas/:folderId`, e a grade usa os JSONs já recebidos.

### 5.4 Saída durante o processamento

- Dentro do app: o guard `CanDeactivate` mostra o diálogo "O processamento será interrompido. Sair mesmo assim?".
- Ao fechar ou recarregar a aba: `beforeunload` mostra o aviso nativo do navegador.
- As páginas já processadas ficam salvas no backend; a pasta aparece como **Incompleta** na lista.

> **Limitação conhecida:** o navegador não guarda a referência da pasta local depois de recarregar. Para completar uma pasta incompleta, o usuário precisa selecionar a mesma pasta de novo (ver Q2).

## 6. Tela 3 — Detalhe da pasta (miniaturas)

### 6.1 Wireframe

```
← Pastas / capitulo 1                         30 páginas · ⚠ 2 com erro
                                                   [ ⬇ Baixar TXT final ]

┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  img   │ │  img   │ │  img   │ │  img   │ │  ⚠     │ │  img   │
│        │ │        │ │        │ │        │ │ erro   │ │        │
├────────┤ ├────────┤ ├────────┤ ├────────┤ ├────────┤ ├────────┤
│ Pág. 1 │ │ Pág. 2 │ │ Pág. 3 │ │ Pág. 4 │ │ Pág. 5 │ │ Pág. 6 │
│ 12 txt │ │ 4 txt  │ │ 0 txt  │ │ 7 txt ✎│ │[Tentar]│ │ 9 txt  │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

### 6.2 Comportamento

| Item | Regra |
|---|---|
| Fonte de dados | Logo depois do processamento: o `ProcessingStore`, com as miniaturas vindas de `URL.createObjectURL(file)`. Em acesso direto ou recarga: `GET /api/folders/{id}`, com miniaturas de `GET /api/pages/{id}/thumbnail`. |
| Grade | `grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4`, em ordem de página. |
| Card da miniatura | Imagem `aspect-[2/3] object-cover` com `loading="lazy"`, rótulo "Pág. N", contagem de blocos ("12 textos") e o ícone ✎ quando editada manualmente. |
| Card com erro | Placeholder com ícone de alerta, mensagem curta e o botão **Tentar novamente** (`POST /api/pages/{id}/process`). Se o arquivo local ainda estiver na sessão, ele é reenviado; senão, o backend reprocessa a imagem que já tem armazenada. |
| Página sem texto | Card normal com "0 textos". Abre o modal com a tabela vazia e a opção de adicionar bloco. |
| Clique no card | Abre o **modal de conferência** (seção 7) e atualiza a URL com `?pagina=N`. |
| **Baixar TXT final** | Mesmo comportamento da seção 4.2. Nome do arquivo: `<nome da pasta>.txt`. Se o modal tiver alterações não salvas, o botão pede para salvar antes. |
| Liberação de memória | Os object URLs são revogados (`URL.revokeObjectURL`) no `ngOnDestroy`. |

## 7. Modal de conferência e edição

### 7.1 Wireframe (desktop ≥ lg)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ capitulo 1 — Página 4 de 30   (004.jpg)             [‹ Anterior] [Próxima ›] [✕]│
├──────────────────────────────┬────────────────────────────────────────────────┤
│                              │  [Tabela]  [Pré-visualizar texto]               │
│                              │ ┌───┬────┬──────────────┬──────────────────────┐│
│                              │ │ # │Tipo│ Original      │ Traduções            ││
│         IMAGEM               │ ├───┼────┼──────────────┼──────────────────────┤│
│          40%                 │ │ 1 │[$▾]│[待ど        ] │ 1 [...        ][obs ]││
│   (scroll/zoom, contain)     │ │   │    │              │ 2 [Ah...      ][obs ]││
│                              │ │   │    │              │ [+ tradução]          ││
│                              │ ├───┼────┼──────────────┼──────────────────────┤│
│                              │ │ 2 │[#▾]│[ビグタン     ] │ 1 [Bem...     ][    ]││
│                              │ └───┴────┴──────────────┴──────────────────────┘│
│                              │ [+ Adicionar bloco]                             │
├──────────────────────────────┴────────────────────────────────────────────────┤
│ ● Alterações não salvas                [Cancelar]  [↻ Reprocessar]  [ Salvar ]  │  ← footer
└───────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Estrutura e classes

| Parte | Regra | Classes Tailwind |
|---|---|---|
| Overlay | Cobre a tela; clicar fora **não** fecha o modal (evita perder edições). | `fixed inset-0 z-50 bg-zinc-950/60 backdrop-blur-sm` |
| Painel | 95% da largura e 90% da altura da viewport. | `w-[95vw] h-[90dvh] flex flex-col rounded-xl bg-white dark:bg-zinc-900 shadow-2xl` |
| Header | Pasta, página N de T, nome do arquivo, navegação e fechar. | `h-14 flex items-center justify-between px-4 border-b` |
| Corpo | Duas colunas. | `flex-1 min-h-0 flex flex-col lg:flex-row` |
| Coluna da imagem | **40%** da largura; imagem inteira visível, com zoom. | `lg:basis-2/5 lg:max-w-[40%] min-h-0 overflow-auto bg-zinc-100 dark:bg-zinc-950` |
| Coluna do texto | **60%**; tabela com rolagem própria. | `lg:basis-3/5 min-h-0 overflow-y-auto p-4` |
| Footer | Indicador de alterações + ações. | `h-16 flex items-center justify-between px-4 border-t` |

**Imagem (coluna esquerda):**
- `object-contain`, ajustada à largura da coluna.
- Zoom com os botões `−`, `+` e "Ajustar", ou com `Ctrl+roda`; pan arrastando quando ampliada.
- Opcional (fase posterior): desenhar os bboxes numerados quando a API os fornecer (seção 11, item I7).

### 7.3 Tabela editável (coluna direita)

Cada **linha é um bloco** de texto, na ordem de leitura.

| Coluna | Controle | Validação |
|---|---|---|
| Ordem | Número (somente leitura) + botões `↑` `↓` para mover o bloco. Mover **renumera** todos de 1 a N automaticamente. | — |
| Tipo | `select` com `#` (Balão) e `$` (Fora do balão). | Obrigatório. |
| Original | `textarea` auto-expansível, fonte `font-jp` (Noto Sans JP), `lang="ja"`. | Não pode ser vazio. |
| Localização | Input de texto; fica numa linha expansível "Detalhes" para não poluir a tabela. | Não pode ser vazia. |
| Traduções | Sublista **ordenada por relevância**. Cada item tem: relevância (select 1–5), tradução (`textarea`) e observação (input). Botões "+ tradução" e remover (🗑). | Mínimo 1 e máximo 5 por bloco; tradução não vazia; relevância de 1 a 5. |
| Ações do bloco | Menu `⋯`: "Excluir bloco" (com confirmação), que renumera os demais. | — |

- **+ Adicionar bloco:** cria uma linha no fim, com tipo `#`, original vazio, localização vazia e uma tradução vazia de relevância 1. O foco vai para o campo Original.
- **Reordenação das traduções:** ao mudar a relevância, a sublista se reordena **ao sair do campo** (blur), e não durante a digitação, para o item não "fugir" do cursor.
- **Erros de validação:** borda `border-primary-600`, mensagem abaixo do campo (`text-sm text-primary-700`) e um resumo no footer ("2 campos precisam de atenção"). O botão Salvar só fica desabilitado se houver erros.

**Aba "Pré-visualizar texto":** mostra, em `<pre class="font-jp whitespace-pre-wrap">`, o trecho do TXT **desta página** gerado pelo mesmo `TxtExportService` (seção 8), refletindo as edições ainda não salvas. É somente leitura.

### 7.4 Footer, salvamento e navegação

| Ação | Regra |
|---|---|
| Indicador | "● Alterações não salvas" (`text-amber-700`) quando o formulário está sujo; "✔ Salvo" por 3 s depois de salvar. |
| **Salvar** | Botão primário. Envia `PUT /api/pages/{id}/json` com o array completo no formato do contrato. Em `200`, atualiza a grade (contagem de blocos, ícone ✎) e mostra um toast "Página salva". Em `422`, mapeia os erros do backend para os campos. |
| Atalho | `Ctrl+S` / `Cmd+S` salva (com `preventDefault`). |
| Cancelar | Descarta as alterações (com confirmação se houver edição) e fecha o modal. |
| Fechar (✕ / `Esc`) | Igual a Cancelar. |
| Anterior/Próxima (`←`/`→` fora de campos de texto) | Se houver alterações não salvas, o diálogo oferece **Salvar e continuar**, **Descartar** ou **Voltar**. |
| Salvando | Os botões ficam desabilitados, o Salvar mostra um spinner e o formulário fica somente leitura. |
| **Reprocessar** | Botão secundário ao lado do Salvar. Consulta a IA de novo para esta imagem e **substitui todo o conteúdo da página** pelo novo resultado. Detalhes na seção 7.5. |

### 7.5 Reprocessar a imagem

**Objetivo:** descartar o resultado atual da página e gerar tudo de novo com a IA (detecção, OCR, classificação, ordem, localização e traduções), usando a imagem que o backend já tem armazenada.

| Item | Regra |
|---|---|
| Posição e estilo | No footer, entre Cancelar e Salvar: `[Cancelar] [↻ Reprocessar] [Salvar]`. Botão secundário, para não competir com o Salvar: `inline-flex items-center gap-2 rounded-lg px-4 py-2 border border-primary-600 text-primary-700 hover:bg-primary-50 dark:border-primary-400 dark:text-primary-300 dark:hover:bg-primary-950`, com o ícone ↻ e `aria-label="Reprocessar esta imagem com a IA"`. |
| Confirmação obrigatória | Diálogo destrutivo: **"Reprocessar a página 4?"** / "A IA vai gerar os textos e as traduções de novo. **Todas as alterações desta imagem, salvas e não salvas, serão substituídas.** Esta ação não pode ser desfeita." Botões: `[Cancelar]` (com o foco inicial) e `[Reprocessar]` (`bg-primary-700 hover:bg-primary-800 text-white`). |
| Chamada | `POST /api/pages/{id}/process?force=true` (seção 10.2). O `force=true` autoriza o backend a sobrescrever blocos editados manualmente (PRD 17.2). |
| Durante o processamento | O corpo da tabela recebe um overlay `absolute inset-0 bg-white/70 dark:bg-zinc-900/70` com spinner e o texto "Reprocessando com IA…" (`aria-live="polite"`). Ficam desabilitados: edição, Salvar, Reprocessar, Anterior/Próxima, ✕ e `Esc`. A imagem continua visível. Timeout de 180 s. |
| Sucesso | O formulário é **reconstruído** com os `blocos` devolvidos e marcado como *pristine*, porque o resultado já está salvo no backend. O card da grade é atualizado (contagem de blocos; o ícone ✎ some porque `edited=false`), o TXT passa a refletir o novo resultado e aparece o toast "Página reprocessada". |
| Erro | O conteúdo atual **permanece intacto**, inclusive as edições não salvas: o backend faz a substituição numa única transação, e o frontend só troca o formulário depois de um `200`. Um banner no topo da tabela mostra "Não foi possível reprocessar: <mensagem>" com o botão `[Tentar novamente]`. |
| `409` (página já em processamento) | Toast "Esta página já está sendo processada. Tente em instantes." |
| Alterações não salvas | Não há diálogo extra: a confirmação acima já avisa que elas serão descartadas. |
| Relação com "Tentar novamente" | O card de erro da grade (seção 6.2) usa o mesmo endpoint e o mesmo serviço (`PagesApi.reprocess`), mas sem confirmação, porque não há conteúdo a perder. |

### 7.6 Mobile e tablet (< lg)

- As colunas ficam empilhadas: a imagem no topo (`h-[35dvh]`) e a tabela embaixo.
- A tabela vira uma **lista de cards por bloco** (os mesmos campos, em layout vertical).
- O footer fica fixo na base do modal. Abaixo de `sm`, Reprocessar vira um botão só de ícone (↻, com `aria-label`) para caber ao lado de Cancelar e Salvar.

## 8. Arquivo TXT final

### 8.1 Formato

Estrutura:

```
<nome da pasta>
<linha em branco>
Página: <n>
<tipo><ordem> <original>
<linha em branco>
* <traducao> (<observacao>)        ← uma linha por tradução, em ordem de relevância
<linha em branco>
<próximo bloco...>
<linha em branco>
Página: <n+1>
...
```

**Exemplo** (pasta `Capítulo 1`):

```text
Capítulo 1

Página: 1
$1 待ど

* ... (Silêncio envergonhado.)
* Ah... (Reação tímida.)

#2 ビグタン

* Bem...


Página: 2
#1 きめたよ!

* Decidi! (よ dá tom de anúncio/afirmação enfática.)
* Já decidi! (Reforça que a decisão está tomada.)

```

### 8.2 Regras de formatação

| # | Regra |
|---|---|
| T1 | A **1ª linha** é o nome da pasta, seguida de uma linha em branco. |
| T2 | As páginas aparecem em **ordem crescente** de número de página (a ordem natural dos arquivos, seção 5.1). Cabeçalho: `Página: <n>`. |
| T3 | Os blocos aparecem em ordem crescente de `ordem`. A linha do bloco é `<tipo><ordem> <original>`, sem espaço entre o tipo e o número: `#2 ビグタン`. |
| T4 | Depois da linha do bloco vem uma linha em branco e depois as traduções. |
| T5 | Cada tradução ocupa uma linha, no formato `* <traducao>`. Se `observacao` não estiver vazia, acrescenta-se ` (<observacao>)`. |
| T6 | As traduções vêm **ordenadas por `relevancia` crescente** (1 primeiro). Em caso de empate, mantém-se a ordem original, porque a ordenação é estável. |
| T7 | Há uma linha em branco depois do último item de cada bloco; entre páginas, uma linha em branco extra (ou seja, **2 linhas em branco** antes de `Página:`). |
| T8 | Quebras de linha dentro de `original`, `traducao` ou `observacao` viram **um espaço**, para manter uma linha por item. Espaços nas pontas são removidos. |
| T9 | Codificação **UTF-8 com BOM** (`﻿`), para o japonês abrir corretamente em qualquer editor do Windows. Quebra de linha `\n`. |
| T10 | Nome do arquivo: `<nome da pasta>.txt`. Os caracteres inválidos no Windows (`\ / : * ? " < > \|`) são trocados por `_`, e espaços e pontos no fim são removidos. Exemplo: `capitulo 1.txt`. |

> **Normalização do exemplo enviado:** o exemplo original tinha aspas soltas (`"Ah...`, `"ビグタン`, `("Silêncio envergonhado.)`) e `Página 2` sem dois-pontos. Tratei isso como erro de digitação e padronizei como `Página: N`, sem aspas. Confirmar em Q1.

### 8.3 Casos especiais

| Situação | Saída no TXT |
|---|---|
| Página processada sem textos | `Página: N`, seguida de `(nenhum texto detectado)` |
| Página com erro ou não processada | `Página: N`, seguida de `(página não traduzida — erro no processamento)` |
| Pasta sem nenhuma página | Só o nome da pasta, e o botão fica desabilitado com o tooltip "Pasta vazia" |

### 8.4 Implementação de referência (`TxtExportService`)

Função pura, sem dependência de Angular, com testes unitários cobrindo T1–T10 e a seção 8.3:

```ts
import { FolderExport, PageExport } from '../api/models';

const BOM = '﻿';
const oneLine = (s: string) => s.replace(/\s*\r?\n\s*/g, ' ').trim();

export function buildFolderTxt(folder: FolderExport): string {
  const out: string[] = [oneLine(folder.pasta), ''];
  const pages = [...folder.paginas].sort((a, b) => a.pagina - b.pagina);

  pages.forEach((page, i) => {
    if (i > 0) out.push('');               // T7: 2ª linha em branco entre páginas
    out.push(...buildPageLines(page));
  });

  return BOM + out.join('\n') + '\n';
}

export function buildPageLines(page: PageExport): string[] {
  const out = [`Página: ${page.pagina}`];

  if (page.status === 'ERROR' || page.blocos === null) {
    return [...out, '(página não traduzida — erro no processamento)', ''];
  }
  if (page.blocos.length === 0) {
    return [...out, '(nenhum texto detectado)', ''];
  }

  for (const b of [...page.blocos].sort((x, y) => x.ordem - y.ordem)) {
    out.push(`${b.tipo}${b.ordem} ${oneLine(b.original)}`, '');
    for (const t of [...b.traducoes].sort((x, y) => x.relevancia - y.relevancia)) {
      const obs = oneLine(t.observacao);
      out.push(`* ${oneLine(t.traducao)}${obs ? ` (${obs})` : ''}`);
    }
    out.push('');
  }
  return out;
}

export function txtFileName(folderName: string): string {
  const safe = folderName.replace(/[\\/:*?"<>|]/g, '_').replace(/[. ]+$/, '').trim();
  return `${safe || 'traducao'}.txt`;
}

export function downloadTxt(content: string, fileName: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
  const a = Object.assign(document.createElement('a'), { href: url, download: fileName });
  a.click();
  URL.revokeObjectURL(url);
}
```

## 9. Arquitetura Angular

### 9.1 Estrutura de pastas

```
frontend/src/app/
├── core/
│   ├── api/                 # FoldersApi, PagesApi, models.ts (gerados do JSON Schema)
│   ├── http/                # interceptor de erro → toast; baseUrl
│   └── layout/              # AppHeaderComponent, AppShellComponent
├── shared/ui/               # ui-button, ui-badge, ui-dialog, ui-toast, ui-skeleton,
│                            # ui-dropzone, ui-progress, ui-empty-state
├── features/
│   ├── folders/             # FolderListPage, FolderTableComponent
│   ├── new-translation/     # NewTranslationPage, FolderPickerComponent,
│   │                        # FileSummaryComponent, ProcessingProgressComponent,
│   │                        # processing.store.ts, folder-reader.ts
│   └── folder-detail/       # FolderDetailPage, ThumbnailGridComponent,
│                            # ThumbnailCardComponent, PageReviewModalComponent,
│                            # BlockTableComponent, TranslationListComponent
└── export/                  # txt-export.ts (seção 8.4) + spec
```

### 9.2 Estado (signals)

**`ProcessingStore`** (`providedIn: 'root'`, sobrevive à navegação):

```ts
type ItemStatus = 'queued' | 'processing' | 'done' | 'error';

interface ProcessingItem {
  pageNumber: number;
  file: File;
  previewUrl: string;          // object URL
  status: ItemStatus;
  pageId?: string;
  blocos?: TextBlockExport[];  // JSON devolvido pelo backend
  error?: string;
  durationMs?: number;
}

// signals
folderId      = signal<string | null>(null);
folderName    = signal('');
items         = signal<ProcessingItem[]>([]);
total         = computed(() => this.items().length);
processed     = computed(() => this.items().filter(i => i.status === 'done' || i.status === 'error').length);
failed        = computed(() => this.items().filter(i => i.status === 'error').length);
current       = computed(() => this.items().find(i => i.status === 'processing'));
isRunning     = computed(() => this.items().some(i => i.status === 'queued' || i.status === 'processing'));
progressLabel = computed(() => `${this.processed()} de ${this.total()}`);
```

A fila é processada com RxJS: `from(items).pipe(mergeMap(item => processOne(item), concurrency), takeUntil(cancel$))`.

**Formulário do modal:** `FormArray` tipado com `FormGroup<Block>`, cada um com um `FormArray<Translation>`. Ele é reconstruído a cada abertura a partir do JSON da página; `dirty` controla o indicador e os guards.

### 9.3 Leitura da pasta (`folder-reader.ts`)

```ts
const IMAGE_EXT = /\.(jpe?g|png|webp)$/i;
const HIDDEN = /^(\.|thumbs\.db$|desktop\.ini$)/i;
const MAX_BYTES = 20 * 1024 * 1024;
const collator = new Intl.Collator('pt-BR', { numeric: true, sensitivity: 'base' });

export interface IgnoredFile { name: string; reason: string; }

export function readFolder(files: File[]) {
  const folderName = files[0]?.webkitRelativePath.split('/')[0] ?? '';
  const images: File[] = [];
  const ignored: IgnoredFile[] = [];

  for (const f of files) {
    const depth = f.webkitRelativePath.split('/').length;
    const reason =
      depth > 2                                            ? 'está em subpasta'
      : HIDDEN.test(f.name)                                ? 'arquivo oculto/sistema'
      : !IMAGE_EXT.test(f.name) || !f.type.startsWith('image/') ? 'não é imagem'
      : f.size === 0                                       ? 'arquivo vazio'
      : f.size > MAX_BYTES                                 ? 'acima de 20 MB'
      : null;
    reason ? ignored.push({ name: f.webkitRelativePath || f.name, reason }) : images.push(f);
  }

  images.sort((a, b) => collator.compare(a.name, b.name));
  return { folderName, images, ignored };
}
```

## 10. Contratos consumidos da API

### 10.1 Tipos (gerados de `contracts/page-export.schema.json` + extensões)

```ts
export interface Translation { traducao: string; observacao: string; relevancia: 1 | 2 | 3 | 4 | 5; }
export interface TextBlockExport { ordem: number; tipo: '#' | '$'; original: string; localizacao: string; traducoes: Translation[]; }

export type PageStatus = 'PENDING' | 'PROCESSING' | 'REVIEW' | 'APPROVED' | 'ERROR';
export type FolderStatus = 'PROCESSING' | 'DONE' | 'DONE_WITH_ERRORS' | 'INCOMPLETE';

export interface FolderSummary {
  id: string; name: string; status: FolderStatus;
  total_pages: number; processed_pages: number; error_pages: number; updated_at: string;
}
export interface PageSummary {
  id: string; page_number: number; file_name: string; status: PageStatus;
  block_count: number; edited: boolean; thumbnail_url: string; image_url: string; error_message?: string;
}
export interface PageExport { pagina: number; arquivo: string; status: PageStatus; blocos: TextBlockExport[] | null; }
export interface FolderExport { pasta: string; paginas: PageExport[]; }
```

### 10.2 Endpoints usados pelo frontend

| Uso | Método e endpoint | Resposta |
|---|---|---|
| Lista de pastas | `GET /api/folders` | `FolderSummary[]` |
| Criar pasta | `POST /api/folders` `{ name }` | `201 FolderSummary` / `409` se o nome já existir |
| Detalhe da pasta | `GET /api/folders/{id}` | `FolderSummary & { pages: PageSummary[] }` |
| **Processar imagem** | `POST /api/folders/{id}/pages/process` (multipart `file`, `page_number`) | `200 { page: PageSummary, blocos: TextBlockExport[] }` |
| Reprocessar página (card de erro / botão **Reprocessar** do modal) | `POST /api/pages/{id}/process?force=true` | `200 { page: PageSummary, blocos: TextBlockExport[] }` / `409` se já estiver em processamento |
| JSON da página | `GET /api/pages/{id}/json` | `TextBlockExport[]` |
| **Salvar edição** | `PUT /api/pages/{id}/json` (body: `TextBlockExport[]`) | `200 TextBlockExport[]` / `422 { error: { details: { "<idx>.traducoes.0.traducao": "..." } } }` |
| **Exportar pasta** | `GET /api/folders/{id}/export` | `FolderExport` |
| Imagem / miniatura | `GET /api/pages/{id}/image`, `GET /api/pages/{id}/thumbnail` | binário |

### 10.3 Exemplo: resposta de `pages/process`

```json
{
  "page": { "id": "pg_01H…", "page_number": 1, "file_name": "001.jpg", "status": "REVIEW",
            "block_count": 2, "edited": false,
            "thumbnail_url": "/api/pages/pg_01H…/thumbnail", "image_url": "/api/pages/pg_01H…/image" },
  "blocos": [
    { "ordem": 1, "tipo": "$", "original": "待ど", "localizacao": "Topo direita",
      "traducoes": [
        { "traducao": "...",   "observacao": "Silêncio envergonhado.", "relevancia": 1 },
        { "traducao": "Ah...", "observacao": "Reação tímida.",         "relevancia": 2 } ] },
    { "ordem": 2, "tipo": "#", "original": "ビグタン", "localizacao": "Topo direita",
      "traducoes": [ { "traducao": "Bem...", "observacao": "", "relevancia": 1 } ] }
  ]
}
```

## 11. Impactos no PRD e no backend

O fluxo pedido muda alguns pontos do PRD. Eles devem ser refletidos no PRD e nos cards de backend:

| # | Impacto | Seção do PRD afetada |
|---|---|---|
| I1 | **Novo endpoint síncrono por imagem**, `POST /api/folders/{id}/pages/process`, que faz upload + análise e devolve o JSON. Internamente pode usar o worker; a requisição aguarda o resultado (timeout de 180 s). | 16, 17 |
| I2 | **`PUT /api/pages/{id}/json`**: salva a página inteira de uma vez (substitui os blocos numa transação, com validação da seção 22). Os blocos editados passam a `source=MANUAL`. | 16, 17.2 |
| I3 | **`GET /api/folders/{id}/export`**: agrega os JSONs de todas as páginas, evitando N requisições para gerar o TXT. | 16 |
| I4 | **`GET /api/pages/{id}/thumbnail`**: miniatura (por exemplo 300 px de largura, WebP) gerada no upload. | 16 |
| I5 | **Status da pasta** (`DONE`, `DONE_WITH_ERRORS`, `INCOMPLETE`, `PROCESSING`), derivado das páginas e exposto no `GET /api/folders`. | 14, 21 |
| I6 | A tela de **revisão com overlay** (PRD seções 19 e 20) fica simplificada no MVP: imagem + tabela. Os bboxes numerados sobre a imagem passam a ser uma melhoria posterior. | 19, 20 |
| I7 | **Nova saída de exportação em TXT** (gerada no frontend). O JSON continua sendo o contrato oficial. | 12, 22 |
| I8 | A **aprovação da página** (`APPROVED`) não aparece neste fluxo. Salvar mantém a página em `REVIEW`. Ver Q3. | 21 |
| I9 | **`POST /api/pages/{id}/process?force=true`** (botão Reprocessar): novo `processing_run` do tipo `FULL` sobre a imagem armazenada. Substitui **todos** os blocos e sugestões, inclusive os `MANUAL`, numa única transação (rollback em caso de falha), volta `edited=false` e devolve o JSON novo. Mantém o lock por página (`409`). | 16, 17.2 |

## 12. Estados, erros e casos-limite

| Caso | Comportamento |
|---|---|
| Backend fora do ar ao abrir a home | Estado de erro com o botão "Tentar novamente". |
| Erro 5xx em uma imagem durante o processamento | 1 retentativa automática; se falhar de novo, marca erro e segue a fila. |
| Imagem rejeitada pelo backend (`415`/`413`) | Marca erro com a mensagem "Formato não suportado" ou "Arquivo muito grande", sem retentativa. |
| Todas as imagens falham | Um toast de erro; o redirecionamento acontece mesmo assim, e a grade mostra todas com "Tentar novamente". |
| Perda de conexão no meio | Os itens pendentes ficam com erro de rede; um banner "Conexão perdida — [Retomar]" reprocessa só os que falharam (se os arquivos ainda estiverem na sessão). |
| `422` ao salvar no modal | Os erros aparecem nos campos correspondentes e o modal continua aberto. |
| `409` ao salvar (página sendo reprocessada) | Toast "A página está sendo processada, tente em instantes". |
| Reprocessar falha ou expira | O conteúdo anterior é mantido; banner de erro com "Tentar novamente" (seção 7.5). |
| Reprocessar gera 0 blocos | A tabela fica vazia com "Nenhum texto detectado" e a opção "+ Adicionar bloco". |
| Nome de pasta com caracteres especiais | Permitido na interface; sanitizado só no nome do arquivo TXT (T10). |
| Duas abas processando | Permitido (as pastas são independentes). O botão "Nova tradução" é bloqueado apenas na aba que está processando. |

## 13. Acessibilidade e responsividade

- O modal usa `role="dialog"`, `aria-modal="true"` e `aria-labelledby` apontando para o título, com foco preso dentro dele (`cdkTrapFocus`) e o foco devolvido à miniatura ao fechar.
- A barra de progresso usa `role="progressbar"`, e o texto "5 de 30" fica numa região `aria-live="polite"` (atualizada a cada item concluído, sem anunciar cada byte).
- Os campos japoneses usam `lang="ja"`, e a fonte `Noto Sans JP` é carregada com `display=swap`.
- Todos os botões de ícone (↑ ↓ 🗑 ✕) têm `aria-label`.
- Contraste AA com os tokens da seção 27 do PRD; o foco é sempre visível (`ring-primary-500`).
- Atalhos: `Ctrl+S` salva; `Esc` fecha; `←`/`→` navega entre páginas (fora de inputs).
- Breakpoints: a grade vai de 2 a 6 colunas; o modal empilha as colunas abaixo de `lg`; a tabela vira cards abaixo de `md`.

## 14. Cards de entrega do frontend

IDs `FE-<nn>`, agrupados por entrega. As dependências de backend usam os itens da seção 11.

### Entrega A — Base e lista de pastas

| Card | Descrição | Depende de |
|---|---|---|
| FE-01 | Shell do app: header com "Nova tradução", roteamento (seção 2), tema red (PRD 27), fonte JP. | PRD F0 |
| FE-02 | Componentes `ui-*` usados neste fluxo: button, badge, dialog, toast, skeleton, progress, dropzone, empty-state. | FE-01 |
| FE-03 | `FoldersApi` + modelos TS (seção 10.1). | I5 |
| FE-04 | `FolderListPage`: tabela/cards, busca, badges, estados vazio/carregando/erro. | FE-03 |
| FE-05 | `txt-export.ts` (seção 8.4) com testes unitários para T1–T10 e a seção 8.3. | — |
| FE-06 | Botão "Baixar TXT" na lista, integrado a `GET /folders/{id}/export`. | FE-05, I3 |

**Aceite:** a home lista as pastas, e o TXT baixado de uma pasta de exemplo é idêntico, byte a byte, ao arquivo esperado do teste.

### Entrega B — Nova tradução

| Card | Descrição | Depende de |
|---|---|---|
| FE-07 | `folder-reader.ts` (seção 9.3) com testes: filtro, ocultos, subpastas, tamanho, ordenação natural. | — |
| FE-08 | `FolderPickerComponent`: input `webkitdirectory` + arrastar e soltar pasta, nome editável, resumo de imagens e ignorados com popover de motivos. | FE-07 |
| FE-09 | `ProcessingStore` + fila RxJS (concorrência, retentativa, timeout, cancelamento). | I1 |
| FE-10 | `ProcessingProgressComponent`: barra, "N de T", arquivo atual, tempo restante, contagem de erros, `aria-live`. | FE-09 |
| FE-11 | Guard `CanDeactivate` + `beforeunload` durante o processamento; tratamento de `409` no nome da pasta. | FE-09 |
| FE-12 | Redirecionamento ao concluir + toast de resumo. | FE-09 |

**Aceite:** numa pasta com 30 imagens e 4 arquivos não-imagem, 4 são ignorados com o motivo, o contador vai de "0 de 30" a "30 de 30", e uma imagem com erro simulado não interrompe a fila.

### Entrega C — Miniaturas, modal e TXT final

| Card | Descrição | Depende de |
|---|---|---|
| FE-13 | `FolderDetailPage` + `ThumbnailGridComponent`: miniaturas locais (object URL) ou da API, contagem de blocos, ícone ✎, card de erro com "Tentar novamente". | I4 |
| FE-14 | `PageReviewModalComponent`: layout 40/60, header com navegação, footer, deep link `?pagina=N`, trap focus. | FE-13 |
| FE-15 | Coluna da imagem: `object-contain`, zoom e pan. | FE-14 |
| FE-16 | `BlockTableComponent`: `FormArray` tipado; editar tipo, original e localização; mover ↑↓ com renumeração; adicionar e excluir bloco. | FE-14 |
| FE-17 | `TranslationListComponent`: adicionar, remover e editar; reordenar por relevância no blur; mínimo 1 e máximo 5. | FE-16 |
| FE-18 | Salvar (`PUT /pages/{id}/json`): indicador de sujo, `Ctrl+S`, mapeamento de `422` para os campos, diálogo de alterações não salvas ao navegar ou fechar. | I2 |
| FE-19 | Aba "Pré-visualizar texto" usando `buildPageLines`. | FE-05, FE-16 |
| FE-20 | Botão "Baixar TXT final" na grade. | FE-06 |
| FE-22 | Botão **Reprocessar** no footer do modal (seção 7.5): diálogo destrutivo, `PagesApi.reprocess(id)`, overlay de carregamento com bloqueio de navegação, reconstrução do formulário no sucesso, preservação do conteúdo no erro e atualização do card da grade. | FE-14, FE-18, I9 |
| FE-21 | E2E (Playwright): home → nova tradução (pasta fixture) → progresso → miniaturas → editar e salvar → baixar TXT → conferir o conteúdo. | todos |

**Aceite:** o fluxo completo da seção 1 roda no E2E, e o TXT final reflete as edições salvas no modal. Reprocessar uma página editada substitui as edições pelo novo resultado da IA; uma falha simulada no reprocessamento mantém o conteúdo anterior.

## 15. Questões em aberto

| ID | Questão | Proposta |
|---|---|---|
| Q1 | O exemplo de TXT tinha aspas soltas e `Página 2` sem dois-pontos. A normalização da seção 8 está correta? | Sem aspas; sempre `Página: N`. |
| Q2 | Uma pasta **incompleta** pode ser retomada? | MVP: sim, selecionando a mesma pasta de novo. O frontend envia só as páginas que faltam, casando pelo nome do arquivo. Depois: usar a File System Access API (Chromium) para lembrar a pasta. |
| Q3 | O fluxo de **aprovação** (`APPROVED`) do PRD continua existindo? | Salvar no modal não aprova. Adicionar depois um toggle "Página conferida" no footer, com um contador na grade ("18 de 30 conferidas"). |
| Q4 | O TXT deve incluir o nome do arquivo da imagem ou a localização de cada bloco? | Não por padrão, seguindo o formato pedido. Pode virar uma opção do botão de download mais adiante. |
| Q5 | Processar em paralelo (concorrência > 1)? | Começar sequencial (1) para controlar custo e carga, e ajustar depois das métricas. |
| Q6 | Subpastas (por exemplo `capitulo 1/extras/`) devem ser processadas? | Não: são ignoradas e listadas com o motivo. |
| Q7 | O **Reprocessar** refaz tudo (OCR + traduções) ou só as traduções, mantendo os originais corrigidos à mão? | Refaz **tudo**, conforme o pedido ("substituindo as alterações atuais"). Se surgir necessidade, adicionar depois um menu no botão com "Só traduções" (`POST /api/pages/{id}/regenerate`, que preserva o OCR). |
