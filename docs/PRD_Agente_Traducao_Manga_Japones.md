# PRD — Agente de OCR e Tradução de Mangá Japonês

> **Projeto:** Manga Translator Agent
> **Stack:** Frontend Angular + Tailwind CSS (paleta `red`) • Backend Python + FastAPI • PostgreSQL • Geração de JSON
> **Versão do documento:** 1.1 (revisada) — convertida de `PRD_Agente_Traducao_Manga_Japones.docx` em 2026-09-24

Documento de requisitos para um aplicativo que recebe páginas de mangá em japonês, detecta e enumera os textos pela ordem de leitura, extrai o original, classifica o tipo (balão ou texto fora do balão), identifica a localização e gera sugestões de tradução em português, persistindo todo o conteúdo no banco de dados.

---

## Sumário

- [0. Revisão do PRD (o que mudou e por quê)](#0-revisão-do-prd-o-que-mudou-e-por-quê)
- [1. Visão do produto](#1-visão-do-produto)
- [2. Objetivos](#2-objetivos)
- [3. Fora do escopo inicial](#3-fora-do-escopo-inicial)
- [4. Arquitetura](#4-arquitetura)
  - [4.1 Separação conceitual: Application API × AI Orchestrator](#41-separação-conceitual-application-api--ai-orchestrator-ai-first)
  - [4.2 Camada de AI Providers](#42-camada-de-ai-providers-ai-first)
- [5. Fluxo principal](#5-fluxo-principal)
- [6. Regra central de ordem de leitura](#6-regra-central-de-ordem-de-leitura)
- [7. Regra de classificação do tipo](#7-regra-de-classificação-do-tipo)
- [8. Regra de localização](#8-regra-de-localização)
- [9. OCR e preservação do original](#9-ocr-e-preservação-do-original)
- [10. Tradução e sugestões](#10-tradução-e-sugestões)
- [11. Regras especiais de tradução](#11-regras-especiais-de-tradução)
- [12. Estrutura do JSON gerado](#12-estrutura-do-json-gerado)
- [13. Contrato de dados](#13-contrato-de-dados)
- [14. Modelo de banco de dados](#14-modelo-de-banco-de-dados)
- [15. Hierarquia de conteúdo](#15-hierarquia-de-conteúdo)
- [16. API REST — Backend Python + FastAPI](#16-api-rest--backend-python--fastapi)
- [17. Pipeline do agente](#17-pipeline-do-agente)
  - [17.4 Estado estruturado da análise (`PageAnalysisState`)](#174-estado-estruturado-da-análise-pageanalysisstate-ai-first)
  - [17.5 Re-avaliação de etapas](#175-re-avaliação-de-etapas-ai-first)
  - [17.6 Verificação de consistência](#176-verificação-de-consistência-ai-first)
  - [17.7 Guardrails](#177-guardrails-ai-first)
  - [17.8 Observabilidade e controle de custo](#178-observabilidade-e-controle-de-custo-ai-first)
  - [17.9 Avaliação de prompts](#179-avaliação-de-prompts-ai-first)
- [18. Contexto enviado ao agente de tradução](#18-contexto-enviado-ao-agente-de-tradução)
- [19. Frontend Angular](#19-frontend-angular)
- [20. UX da revisão](#20-ux-da-revisão)
- [21. Estados de processamento](#21-estados-de-processamento)
- [22. Validações do JSON](#22-validações-do-json)
- [23. Exemplo de análise da página fornecida](#23-exemplo-de-análise-da-página-fornecida)
- [24. Prompt-base do agente](#24-prompt-base-do-agente)
- [25. Requisitos não funcionais](#25-requisitos-não-funcionais)
- [26. Critérios de aceite do MVP](#26-critérios-de-aceite-do-mvp)
- [27. Design system — Tailwind CSS, paleta red](#27-design-system--tailwind-css-paleta-red)
- [28. Fases de entrega (detalhadas)](#28-fases-de-entrega-detalhadas)
- [29. Decisões importantes](#29-decisões-importantes)
- [30. Glossário da obra (memória de tradução)](#30-glossário-da-obra-memória-de-tradução)
- [31. Questões em aberto](#31-questões-em-aberto)
- [32. Nomenclatura](#32-nomenclatura)

---

## 0. Revisão do PRD (o que mudou e por quê)

A revisão encontrou inconsistências e lacunas no documento original. Os pontos abaixo já foram aplicados ao longo deste arquivo; as seções alteradas trazem a marca **Revisão**.

### 0.1 Inconsistências corrigidas

| # | Problema no original | Correção aplicada |
|---|---|---|
| R1 | O subtítulo e a seção 16 definem o backend como **Python + FastAPI**, mas a tabela de arquitetura (seção 4) diz **Node.js + TypeScript** e os requisitos não funcionais (seção 25) exigem "TypeScript no frontend e backend". | Backend padronizado em **Python 3.12+ / FastAPI / Pydantic v2**. A exigência de tipagem no backend passa a ser cumprida com type hints + `mypy`/`pyright`. |
| R2 | Os endpoints usam a sintaxe do Express (`/:id`). | Convertidos para a sintaxe do FastAPI (`/{id}`). |
| R3 | A hierarquia da seção 15 começa em **Pasta**, mas a seção 30 (Glossário) começa em **Obra → Pasta/Capítulo**. O modelo de banco não tem a entidade Obra. | Criada a entidade `works` (obra). `folders.work_id` entra no MVP como coluna *nullable* para evitar uma migração que quebre dados na V2. |
| R4 | O Glossário (seção 30) não aparece no modelo de banco nem na API. | Tabelas `glossary_entries` e `glossary_occurrences` foram definidas e ficam para a fase V2. |
| R5 | A seção 29 sugere o nome de arquivo `.docx`. | A especificação oficial passa a ser este `.md`, versionado junto do código. |
| R6 | A seção 23 cita uma "imagem de referência" que não está no documento. | **Resolvido:** as imagens estão em `docs/referencias/` (`pagina_01.webp`, `banner_01.png`), com os gabaritos `*.expected.json` e os metadados técnicos em `gabarito.meta.json`. A análise está na seção 23. |
| R7 | O exemplo de JSON (seção 12) traz originais que não aparecem nas imagens de referência (`ビグタン` → "Bem...", `待ど` → "..."), o que sugere OCR incorreto. | **Resolvido:** o exemplo foi substituído por um trecho real do gabarito da `pagina_01`. |

### 0.2 Lacunas preenchidas

| # | Lacuna | Definição adicionada |
|---|---|---|
| L1 | Não havia como **criar ou excluir blocos manualmente** quando o OCR não detecta uma região ou detecta algo que não é texto. | Endpoints `POST /api/pages/{id}/text-blocks` e `DELETE /api/text-blocks/{id}`, com o campo `source` (`AUTO`/`MANUAL`). |
| L2 | Não havia endpoints de exclusão (pastas, páginas, sugestões) nem de aprovação da página (`REVIEW → APPROVED`). | Endpoints `DELETE` e `POST /api/pages/{id}/approve` adicionados. |
| L3 | Não estava definido o que acontece com as **edições humanas** quando a página é reanalisada. | Política de reprocessamento definida na seção 17.2. |
| L4 | O limite de "baixa confiança" do OCR não estava definido. | Configuração `OCR_LOW_CONFIDENCE_THRESHOLD` (padrão `0.80`) e política `EXPORT_BLOCK_ON_LOW_CONFIDENCE`. |
| L5 | `text_blocks` não era ligado a `processing_runs`, o que impedia o versionamento e a idempotência. | Colunas `processing_run_id`, `source`, `lines`, `orientation`, `created_at` e `updated_at` adicionadas. |
| L6 | Não se sabia como a localização seria gerada: por LLM ou por regra. | Abordagem híbrida (seção 8.1): uma regra determinística a partir do bbox gera a base, e o LLM refina apenas relações visuais ("Dentro do logo"). |
| L7 | Os modelos e ferramentas de OCR/visão/LLM não estavam definidos. | Recomendações adicionadas na seção 17.3. A escolha final é uma questão em aberto (Q1). |
| L8 | O design system do frontend não estava definido. | Nova seção 27 com Tailwind CSS usando a paleta `red`. |
| L9 | O backlog (antiga seção 27) tinha só uma linha por fase. | Substituído pela seção 28, com objetivo, escopo, cards candidatos, critérios de aceite e dependências de cada fase. |
| L10 | O PRD não trata **furigana** (ruby), que aparece nas duas imagens de referência (`誰`→だれ, `君`→きみ, `連載`→れんさい). | Regra na seção 9.1: o furigana não vira bloco, não entra em `original` e fica guardado em `text_blocks.ruby`. |
| L11 | O PRD não diz quando colunas ou linhas vizinhas formam **um bloco ou vários** (por exemplo `──誰よりも` / `何よりも`, `君の` / `おかげだから`). | Regra na seção 9.2: texto contínuo do mesmo balão ou da mesma narração forma um bloco, com as linhas em `lines`. |
| L12 | O PRD não trata **texto manuscrito** (letra infantil, anotações em cadernos e desenhos) nem **falsos positivos gráficos** (por exemplo `田` desenhado como janela). | O manuscrito recebe a marcação `handwritten` e revisão obrigatória; os falsos positivos são excluídos na revisão (seção 9.3). |

### 0.3 Riscos identificados

- **Ordem de leitura em páginas com vários painéis (alto — confirmado nas imagens de referência).** O protótipo `docs/prototipos/ordem_leitura.py` aplicou a regra literal por colunas aos bboxes das imagens de referência:
  - na `pagina_01`, os nomes do painel inferior (`とくだ さきこ`…) ficam **entre** `きめたよ!` e `おれも`, os dois balões do painel superior;
  - no `banner_01`, o logo `幸福喫茶3丁目` cai para o **último** lugar.
  
  Com a divisão prévia em **faixas** (divisas de painel + blocos largos), as duas imagens saem na ordem esperada. Por isso a divisão em faixas passa a fazer parte do MVP (seção 6.1, card F4-AG-01).
- **OCR de onomatopeias estilizadas e textos em fontes artísticas (alto).** Os OCRs especializados em mangá erram muito nesses casos. Mitigação: sinalizar baixa confiança e permitir edição do original.
- **Custo e latência do LLM por página (médio).** Mitigação: traduzir a página inteira em uma única chamada e cachear por `hash(original + contexto)`.
- **Confusão visual na paleta vermelha (médio).** Vermelho como cor primária pode ser confundido com erro. Mitigação: os estados sempre combinam ícone e texto, nunca só a cor (seção 27.4).

---

## 1. Visão do produto

O sistema será um assistente de tradução e preparação de mangá. O usuário poderá organizar uma obra em pastas, adicionar páginas e executar um agente sobre cada imagem. O agente deve combinar visão/OCR, análise espacial, contexto da página e tradução para produzir uma estrutura revisável. O usuário continua sendo o responsável pela revisão final da tradução.

## 2. Objetivos

- Capturar automaticamente os textos japoneses presentes na página.
- Identificar cada unidade textual e preservar o original reconhecido.
- Ordenar os textos da direita para a esquerda e de cima para baixo.
- Distinguir texto dentro de balão (`#`) de texto fora de balão (`$`).
- Descrever a localização de cada texto na página.
- Gerar várias sugestões de tradução em português, com observações contextuais.
- Atribuir relevância às sugestões para facilitar a revisão.
- Persistir pastas, páginas, blocos de texto e sugestões no banco.
- Gerar, para cada página, um JSON com estrutura estável para uso posterior na edição do mangá.

## 3. Fora do escopo inicial

- Redesenhar a página ou apagar automaticamente o texto japonês.
- Inserir a tradução diretamente na imagem.
- Fazer lettering ou finalização gráfica.
- Publicar ou distribuir a obra.
- Garantir tradução perfeita sem revisão humana.
- Substituir um OCR especializado quando o texto estiver extremamente deteriorado.
- **(Revisão)** Autenticação e multiusuário. O MVP é monousuário e roda localmente; a API já nasce preparada para receber autenticação depois.

## 4. Arquitetura

| Camada | Tecnologia | Responsabilidades |
|---|---|---|
| Frontend | Angular (standalone components, signals) + TypeScript + **Tailwind CSS (paleta red)** | Upload e organização, visualização da página, regiões detectadas, edição e revisão, execução do agente e exportação. |
| Backend | **Python 3.12+ + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic** *(Revisão R1)* | API REST, autenticação futura, processamento assíncrono, OCR/visão, tradução, regras de ordenação e classificação, geração e validação do JSON. |
| Worker | Processo Python separado (fila) | Executa o pipeline do agente fora do ciclo de request. No MVP pode ser `arq`/RQ com Redis ou uma fila na própria tabela `processing_runs`. |
| Banco | PostgreSQL 16+ | Obras, pastas, páginas, blocos de texto, traduções, execuções, status e metadados. |
| Arquivos | Filesystem local no MVP; storage compatível com S3 na V2 | Imagens originais e, opcionalmente, versões processadas. O banco guarda apenas a referência do arquivo. |
| Agente | Pipeline de visão + OCR + LLM | Detectar regiões → OCR → classificar → localizar → ordenar → traduzir → validar → persistir. |

```
[Angular + Tailwind] ──HTTP/JSON──> [FastAPI] ──SQL──> [PostgreSQL]
                                        │
                                        ├──enfileira──> [Worker: pipeline do agente]
                                        │                   ├─ detector de texto
                                        │                   ├─ OCR japonês
                                        │                   └─ LLM (visão + tradução)
                                        └──lê/grava──> [Storage de imagens]
```

### 4.1 Separação conceitual: Application API × AI Orchestrator *(AI-First)*

O backend é composto por duas camadas conceituais. No MVP rodam no mesmo processo Python; na V2 podem ser separadas em serviços distintos.

| Camada | Módulo Python | Responsabilidades |
|---|---|---|
| **Application API** | `api/` | Autenticação (futura), obras, pastas, páginas, blocos, sugestões; upload e storage; endpoints REST; comunicação com o Angular. |
| **AI Orchestrator** | `agent/` | Analisar a página; orquestrar detecção, OCR e LLM; manter o `PageAnalysisState`; decidir quando re-avaliar uma etapa; persistir o resultado final. |

O Orchestrator é o núcleo inteligente do sistema — não um middleware que repassa chamadas. A Application API o invoca como um serviço interno (chamada de função no MVP, chamada HTTP ou fila na V2).

### 4.2 Camada de AI Providers *(AI-First)*

Todas as chamadas a modelos externos passam por uma interface `AIProvider` comum, para que trocar um modelo não exija alterar o Orchestrator:

```
AI Orchestrator
      │
      ├── VisionProvider      (detecção de regiões, classificação #/$, re-avaliação de recortes)
      ├── OCRProvider         (extração de texto japonês por região)
      ├── TranslationProvider (LLM multimodal, saída estruturada via Pydantic)
      └── ValidationProvider  (opcional — LLM ou regras determinísticas)
```

Cada `Provider` expõe `analyze(input) → output` e registra modelo, versão e latência em `model_metadata`. A troca de implementação (por exemplo, de `manga-ocr` para um LLM multimodal no OCR) é feita por configuração, sem alterar o Orchestrator.

## 5. Fluxo principal

1. O usuário cria ou seleciona uma pasta da obra.
2. O usuário adiciona uma ou mais páginas. Cada página recebe o nome do arquivo e um número/ordem opcional.
3. O backend armazena a referência da imagem e cria o registro da página (`PENDING`).
4. O usuário executa "Analisar página".
5. O backend cria um `processing_run`, muda a página para `PROCESSING` e enfileira o trabalho. *(Revisão)*
6. O agente detecta as regiões textuais e seus limites (bounding boxes).
7. O OCR japonês extrai o texto de cada região.
8. O agente classifica cada região como dentro de balão (`#`) ou fora de balão (`$`).
9. O agente calcula a ordem de leitura: direita → esquerda; depois, cima → baixo.
10. O agente descreve a localização em linguagem curta, por exemplo "Topo direita" ou "Centro em destaque".
11. O agente traduz cada original considerando o contexto visual e textual disponível.
12. O agente gera uma ou mais sugestões para cada bloco, cada uma com tradução, observação e relevância.
13. O backend valida e persiste o resultado no banco, e a página vai para `REVIEW`.
14. O frontend, que acompanha o status por polling, apresenta a página com as falas enumeradas e permite a revisão.
15. Depois da revisão, o usuário aprova a página (`APPROVED`) e pode gerar ou exportar o JSON final.

## 6. Regra central de ordem de leitura

A ordem deve ser determinada pela posição espacial, e não pela ordem em que o OCR devolve os resultados.

- Regra padrão da página: direita → esquerda e, dentro de cada faixa/coluna, cima → baixo.
- Em blocos dispostos em colunas verticais, a coluna mais à direita recebe o menor número de ordem.
- Entre blocos aproximadamente na mesma coluna/faixa, o bloco mais acima vem primeiro.
- Quando dois blocos se sobrepõem, o agente deve desempatar usando o centro da região e os limites do bounding box.
- O número de ordem começa em 1 e é sequencial.
- A ordem é da página, não da obra inteira: cada página recomeça em 1.
- O agente deve guardar o bounding box e as coordenadas internamente, para permitir auditar a ordenação.
- O OCR deve preservar a orientação dos caracteres japoneses. A regra de ordenação não significa inverter os caracteres.

### 6.1 Algoritmo de referência *(Revisão)*

1. Normalizar os bboxes para coordenadas relativas (0–1) da página.
2. **Dividir a página em faixas horizontais** *(Revisão, validada com as imagens de referência)*:
   - a. Detectar as **divisas de painel horizontais**: linhas de moldura ou calhas brancas que atravessam ≥ 80% da largura da página. Cada bloco pertence à faixa em que está o seu centro `y`.
   - b. Dentro de cada faixa, um **bloco largo** (largura > 60% da faixa, como uma manchete) funciona como sub-faixa própria e separa os blocos acima dos blocos abaixo.
3. Em cada faixa ou sub-faixa, **agrupar em colunas**: dois blocos pertencem à mesma coluna quando a sobreposição horizontal é ≥ 50% da largura do menor bloco (a tolerância é configurável).
4. Ordenar as colunas pela borda direita (`x + width`), em ordem decrescente.
5. Dentro de cada coluna, ordenar pelo topo (`y`), em ordem crescente.
6. Desempate: centro `x` decrescente e, em seguida, centro `y` crescente.
7. Concatenar as faixas de cima para baixo e numerar de 1 a N.

Se nenhuma divisa for detectada, a página inteira é uma faixa e o resultado equivale à regra literal do PRD.

A ordenação deve ser implementada como uma **estratégia plugável** (`ReadingOrderStrategy`):

- `tiered_column_rtl` (**padrão do MVP**): os passos 1–7 acima;
- `column_rtl`: só os passos 3–6, a regra literal (fica como opção e para comparação);
- `panel_aware` (V2): detectar os painéis completos, inclusive divisas verticais e inclinadas, ordená-los por linhas (cima → baixo; na mesma linha, direita → esquerda) e aplicar `column_rtl` dentro de cada painel.

**Resultado do protótipo nas imagens de referência** (`docs/prototipos/ordem_leitura.py`):

| Imagem | `column_rtl` (literal) | `tiered_column_rtl` |
|---|---|---|
| `pagina_01` | きめたよ! → **とくだ さきこ → しあわせにするん → あべかわ さくら → みやた ゆき** → おれも → … ❌ | きめたよ! → おれも → だれかを… → ──誰よりも… → とくだ さきこ → … ✅ |
| `banner_01` | 上位5名… → 連載50回… → キャラクター… → **幸福喫茶3丁目** ❌ | 上位5名… → 幸福喫茶3丁目 → 連載50回… → キャラクター… ✅ |

## 7. Regra de classificação do tipo

| Valor | Significado | Exemplos |
|---|---|---|
| `#` | Texto dentro de um balão de fala ou pensamento, ou de uma área claramente delimitada como balão. | Balão oval, balão irregular, balão de pensamento. |
| `$` | Texto fora de balão. | Legenda, título, onomatopeia, texto sobre o cenário, placa, texto do logo, chamadas editoriais. |

A cor branca não pode ser a única regra. O agente deve analisar o contorno, a área interna, a cauda do balão, a posição do texto e a relação com o desenho. Um balão branco é apenas o caso mais comum.

## 8. Regra de localização

A propriedade `localizacao` deve ser curta, legível e útil para encontrar o texto visualmente. A descrição pode combinar posição com destaque ou tamanho.

| Categoria | Exemplos válidos |
|---|---|
| Posição | Topo direita; Topo esquerda; Centro; Inferior direita; Canto superior esquerdo |
| Posição + destaque | Centro em destaque; Centro (grande); Topo direita (pequeno) |
| Relação com elemento | Dentro do logo (direita); Sobre o cenário (esquerda); Abaixo do título |
| Região | Painel inferior esquerdo; Balão central; Painel superior direito |

- Não usar coordenadas como única descrição no JSON final. As coordenadas podem continuar no banco como metadado técnico.
- Se o texto estiver dentro de um elemento identificável, priorizar a relação visual: "Dentro do logo (direita)".

### 8.1 Geração híbrida *(Revisão)*

1. **Base determinística:** dividir a página numa grade 3×3 (Topo/Centro/Inferior × esquerda/centro/direita) a partir do centro do bbox. O sufixo "(grande)" entra quando a área do bbox for ≥ 8% da página, e "(pequeno)" quando for ≤ 0,5% (limites configuráveis).
2. **Refinamento pelo LLM (opcional):** o LLM pode substituir a base por uma relação visual ("Dentro do logo (direita)"). Se a resposta vier vazia ou inválida, mantém-se a base.

## 9. OCR e preservação do original

- O campo `original` deve conter o texto japonês reconhecido, incluindo kanji, hiragana, katakana, pontuação e sinais relevantes.
- Não traduzir nem romanizar o campo `original`.
- Não "corrigir" silenciosamente um kanji duvidoso. Quando a confiança for baixa, o sistema deve sinalizar que o bloco precisa de revisão.
- As quebras de linha visuais podem ser normalizadas no texto lógico, mas a informação das linhas deve poder ser preservada como metadado (`text_blocks.lines`).
- Quando o texto estiver parcialmente ilegível, manter o que foi reconhecido e sinalizar a incerteza numa observação técnica ou de revisão.
- **(Revisão)** A baixa confiança é definida por `ocr_confidence < OCR_LOW_CONFIDENCE_THRESHOLD` (padrão `0.80`). Nesse caso, `review_status` recebe `NEEDS_REVIEW`.

### 9.1 Furigana (ruby) *(Revisão L10)*

- O furigana é o texto pequeno ao lado ou acima do kanji que indica a leitura, como `誰`→だれ e `君`→きみ na `pagina_01`, ou `連載`→れんさい e `幸福`→コウフク no `banner_01`.
- Ele **não é um bloco independente**: se o detector o separar, a região deve ser fundida ao bloco-pai (a região pequena adjacente ao kanji, com fonte ≤ 50% da altura do texto principal).
- Ele **não entra em `original`**: `original` guarda apenas o texto base (`君のおかげだから`, e não `君きみのおかげだから`).
- A leitura fica guardada em `text_blocks.ruby` (JSONB), no formato `[{ "base": "君", "reading": "きみ" }]`, e é enviada ao tradutor como contexto, o que ajuda com nomes e leituras incomuns.

### 9.2 Agrupamento em blocos *(Revisão L11)*

- **Um bloco** é um texto contínuo do mesmo balão, da mesma legenda ou da mesma narração, mesmo quando ocupa várias colunas ou linhas. Exemplos: `──誰よりも` + `何よりも` formam **um** bloco; `君の` + `おかげだから` formam **um** bloco. As linhas visuais ficam em `lines`.
- **Blocos distintos** são textos em balões diferentes, em elementos gráficos diferentes (logo × chamada) ou em etiquetas diferentes (cada nome sob um desenho).
- Uma narração que continua em outro painel (por exemplo, o bloco 4 continuando no bloco 9 da `pagina_01`) permanece em **blocos separados**. A continuidade é registrada na `observacao`.

### 9.3 Texto manuscrito e falsos positivos *(Revisão L12)*

- Texto manuscrito (anotações, letra infantil, textos dentro de desenhos) recebe `handwritten = true` e entra como `NEEDS_REVIEW` independentemente da confiança do OCR. Na `pagina_01`, `しあわせにするん` pode ser lido como `しあわせにする人`.
- Os elementos gráficos que parecem caracteres (por exemplo, `田` desenhado como a janela de uma casa) são **falsos positivos esperados**. O revisor os exclui (`DELETE /api/text-blocks/{id}`), e o gabarito lista esses casos em `nao_texto`.

## 10. Tradução e sugestões

O agente deve gerar uma ou mais alternativas de tradução para cada bloco. A tradução deve considerar o contexto da fala, a relação com outros textos, o tipo do texto, a localização, os elementos visuais e as características do mangá, sem inventar informação ausente.

| Campo | Regra |
|---|---|
| `traducao` | Texto sugerido em português brasileiro. |
| `observacao` | Explica nuance, ambiguidade, fragmento, onomatopeia, leitura possível ou contexto útil. |
| `relevancia` | Inteiro de 1 a 5: 1 é a sugestão mais adequada ou provável, 5 a menos adequada. Usado para ordenar as alternativas. |

- Quando houver uma tradução claramente adequada, pode existir uma única sugestão.
- Quando houver ambiguidade relevante, gerar alternativas e explicar a diferença em `observacao`.
- A relevância não é uma probabilidade matemática: é uma indicação ordinal para a revisão humana.
- O agente deve preferir traduções naturais em português, sem perder o sentido original.
- **(Revisão)** Máximo de **5 sugestões por bloco**. Relevâncias repetidas no mesmo bloco são permitidas, mas a exportação ordena por `relevancia` e, em seguida, por `created_at`.

## 11. Regras especiais de tradução

- **Onomatopeias:** indicar na observação que se trata de som, movimento, reação ou efeito visual, quando isso for pertinente.
- **Fragmentos:** preservar a sensação de frase interrompida quando o original estiver incompleto.
- **Silêncio, hesitação e timidez:** a tradução pode usar reticências e partículas equivalentes, com observação contextual.
- **Nomes próprios:** não inventar tradução. Quando necessário, manter a transliteração ou sugerir a forma adequada (na V2, consultar o glossário da obra).
- **Títulos e logos:** tratar como texto fora de balão (`$`), salvo evidência visual de que o texto está dentro de um balão.
- **Texto editorial ou promocional:** traduzir separadamente, sem misturar com as falas.
- **Leitura incerta do OCR:** a incerteza deve aparecer na revisão, e não ser escondida por uma tradução confiante demais.

## 12. Estrutura do JSON gerado

O JSON final de uma página é um array de objetos. Exemplo:

> **Revisão R7:** trecho real do gabarito `docs/referencias/pagina_01.expected.json` (blocos 1, 2 e 4 de 12).

```json
[
  {
    "ordem": 1,
    "tipo": "#",
    "original": "きめたよ!",
    "localizacao": "Topo direita",
    "traducoes": [
      { "traducao": "Decidi!",    "observacao": "よ dá tom de anúncio/afirmação enfática.", "relevancia": 1 },
      { "traducao": "Já decidi!", "observacao": "Reforça que a decisão está tomada.",       "relevancia": 2 }
    ]
  },
  {
    "ordem": 2,
    "tipo": "#",
    "original": "おれも",
    "localizacao": "Topo centro-direita (abaixo do balão 1)",
    "traducoes": [
      { "traducao": "Eu também!",        "observacao": "おれ é pronome masculino informal; responde ao balão anterior.", "relevancia": 1 },
      { "traducao": "Eu também decidi.", "observacao": "Explicita o verbo omitido (きめた).",                           "relevancia": 2 }
    ]
  },
  {
    "ordem": 4,
    "tipo": "$",
    "original": "──誰よりも何よりも",
    "localizacao": "Painel superior esquerdo",
    "traducoes": [
      { "traducao": "— Mais do que qualquer pessoa, mais do que qualquer coisa", "observacao": "Narração. Paralelismo 誰 (pessoas) / 何 (coisas). O travessão indica continuação no painel inferior (君のおかげだから).", "relevancia": 1 },
      { "traducao": "— Mais que ninguém, mais que tudo", "observacao": "Versão mais curta e natural para lettering.", "relevancia": 2 }
    ]
  }
]
```

> O trecho omite o bloco 3 só para ficar curto. O JSON completo e válido tem `ordem` sequencial de 1 a 12, sem lacunas (seção 22).

## 13. Contrato de dados

| Propriedade | Tipo | Obrigatória | Descrição |
|---|---|---|---|
| `ordem` | integer | sim | Número sequencial da unidade textual na página. |
| `tipo` | string | sim | Somente `#` ou `$`. |
| `original` | string | sim | Texto japonês extraído. |
| `localizacao` | string | sim | Descrição visual curta. |
| `traducoes` | array | sim | Lista de sugestões. |
| `traducoes[].traducao` | string | sim | Sugestão em português. |
| `traducoes[].observacao` | string | sim | Contexto, nuance ou explicação (pode ser `""`). |
| `traducoes[].relevancia` | integer 1..5 | sim | 1 é a alternativa mais relevante. |

**(Revisão)** O contrato deve existir como modelo Pydantic (`PageExport = RootModel[list[TextBlockExport]]`), e o JSON Schema gerado a partir dele fica versionado em `contracts/page-export.schema.json`. O frontend gera os tipos TypeScript a partir desse schema, para que haja uma única fonte da verdade.

## 14. Modelo de banco de dados

O banco mantém os dados estruturados. O JSON é uma representação derivada e exportável.

| Tabela | Campos principais | Relacionamento |
|---|---|---|
| `works` *(Revisão R3)* | id, title, created_at, updated_at | 1:N com folders |
| `folders` | id, **work_id (nullable)**, name, created_at, updated_at | N:1 com works; 1:N com pages |
| `pages` | id, folder_id, file_name, file_path, **mime_type, width, height, sha256**, page_number, status, created_at, updated_at | N:1 com folders; 1:N com text_blocks |
| `text_blocks` | id, page_id, **processing_run_id**, order_number, type, original, location, bbox, **lines, orientation, ruby, handwritten**, ocr_confidence, review_status, **source**, **created_at, updated_at** | N:1 com pages; 1:N com translation_suggestions |
| `translation_suggestions` | id, text_block_id, translation, observation, relevance, **source**, created_at, **updated_at** | N:1 com text_blocks |
| `processing_runs` | id, page_id, **run_type**, status, started_at, finished_at, error_message, model_metadata, **prompt_version** | N:1 com pages |
| `characters` *(MVP)* | id, work_id, name_original, name_preferred, gender, speech_register, notes | N:1 com works |
| `character_mentions` *(MVP)* | id, character_id, page_id, text_block_id | associa personagem a bloco específico; N:1 com characters e text_blocks |
| `glossary_entries` *(V2)* | id, work_id, category, source_term, preferred_translation, notes | N:1 com works |
| `glossary_occurrences` *(V2)* | id, glossary_entry_id, page_id, text_block_id | N:1 com glossary_entries e pages |

**Domínios** *(Revisão)*:

- `pages.status`: `PENDING | PROCESSING | REVIEW | APPROVED | ERROR`
- `text_blocks.type`: `# | $` (check constraint)
- `text_blocks.review_status`: `PENDING | NEEDS_REVIEW | REVIEWED`
- `text_blocks.source` e `translation_suggestions.source`: `AUTO | MANUAL`
- `text_blocks.orientation`: `VERTICAL | HORIZONTAL`
- `processing_runs.run_type`: `FULL | TRANSLATE_ONLY`
- `translation_suggestions.relevance`: check `BETWEEN 1 AND 5`
- Constraint única `(page_id, order_number)` em `text_blocks`, *deferrable*, para permitir a renumeração dentro de uma transação.

`bbox` é armazenado como JSONB com `x`, `y`, `width` e `height`, em pixels da imagem original. Ele não aparece no JSON de exportação, mas é necessário para desenhar as regiões no frontend e para auditar a ordem.

## 15. Hierarquia de conteúdo

Estrutura lógica: **Obra → Pasta (capítulo) → Páginas → Blocos de texto → Sugestões de tradução.** *(Revisão R3)*

| Entidade | Exemplo |
|---|---|
| Obra | Minha Obra |
| Pasta | capitulo_01 |
| Página | 001.jpg |
| Bloco | ordem 1 / `#` / ビグタン / Topo direita |
| Sugestões | Bem... / Então... |

## 16. API REST — Backend Python + FastAPI

*(Revisão R2: sintaxe `{id}`. As linhas marcadas com ➕ são novas.)*

| Método | Endpoint | Objetivo |
|---|---|---|
| GET | `/api/folders` | Listar pastas. |
| POST | `/api/folders` | Criar pasta. |
| GET | `/api/folders/{id}` | Consultar a pasta e suas páginas. |
| ➕ PATCH | `/api/folders/{id}` | Renomear pasta. |
| ➕ DELETE | `/api/folders/{id}` | Excluir pasta (em cascata, com confirmação). |
| POST | `/api/folders/{id}/pages` | Adicionar página ou imagem (multipart, aceita vários arquivos). |
| GET | `/api/pages/{id}` | Consultar a página e os resultados. |
| ➕ GET | `/api/pages/{id}/image` | Servir a imagem original. |
| ➕ PATCH | `/api/pages/{id}` | Alterar `page_number` e `file_name`. |
| ➕ DELETE | `/api/pages/{id}` | Excluir página. |
| POST | `/api/pages/{id}/analyze` | Executar o agente. Responde `202` com `run_id`. |
| ➕ GET | `/api/pages/{id}/runs` | Histórico de execuções e status atual (usado pelo polling). |
| POST | `/api/pages/{id}/regenerate` | Regenerar traduções sem necessariamente refazer o OCR (`run_type=TRANSLATE_ONLY`). |
| ➕ POST | `/api/pages/{id}/text-blocks` | Criar bloco manual (bbox, tipo, original). *(L1)* |
| PATCH | `/api/text-blocks/{id}` | Editar original, tipo, localização, bbox ou `review_status`. |
| ➕ DELETE | `/api/text-blocks/{id}` | Excluir bloco (renumera os demais). *(L1)* |
| POST | `/api/pages/{id}/reorder` | Confirmar ou reordenar blocos manualmente (recebe a lista ordenada de ids). |
| ➕ POST | `/api/pages/{id}/reorder/auto` | Recalcular a ordem a partir dos bboxes. |
| POST | `/api/text-blocks/{id}/translations` | Adicionar sugestão. |
| PATCH | `/api/translations/{id}` | Editar tradução, observação ou relevância. |
| ➕ DELETE | `/api/translations/{id}` | Remover sugestão (o bloco precisa manter pelo menos uma). |
| ➕ POST | `/api/pages/{id}/approve` | Mudar `REVIEW → APPROVED`, aplicando a política de baixa confiança. *(L2)* |
| GET | `/api/pages/{id}/json` | Gerar e retornar o JSON final (`?download=true` define `Content-Disposition`). |

**Padrão de erro** *(Revisão)*: `{"error": {"code": "STRING_CODE", "message": "texto legível", "details": {...}}}`, com os status HTTP coerentes (400, 404, 409, 413, 415, 422 e 500).

## 17. Pipeline do agente

| Etapa | Entrada | Saída |
|---|---|---|
| 1. Pré-processamento | Imagem | Imagem otimizada para OCR/visão |
| 2. Detecção | Imagem | Regiões textuais + bounding boxes |
| 3. OCR | Regiões | Texto japonês + confiança |
| 4. Classificação | Região + contexto | `#` ou `$` |
| 5. Localização | Bounding box + imagem | Descrição textual |
| 6. Ordenação | Bounding boxes | ordem 1..N |
| 7. Tradução | Original + contexto + personagens + páginas aprovadas anteriores | Sugestões |
| 8. Verificação de consistência | Sugestões + histórico da obra | Sugestões anotadas; alertas de inconsistência |
| 9. Guardrails | Objeto completo | Objeto com violações sinalizadas ou bloqueadas |
| 10. Validação estrutural | Objeto aprovado pelos guardrails | JSON validado pelo schema Pydantic |
| 11. Persistência | Resultado | Registros no banco |

### 17.1 Contrato interno entre etapas *(Revisão)*

Cada etapa é uma função pura e tipada (`Stage[In, Out]`), para que possa ser testada isoladamente e trocada de implementação (por exemplo, trocar o OCR sem mexer na ordenação). Todas registram duração e metadados em `processing_runs.model_metadata`.

### 17.2 Política de reprocessamento e idempotência *(Revisão L3)*

- **Analisar (`FULL`):** cria um novo `processing_run`. Se a página tiver blocos com `source=MANUAL` ou `review_status=REVIEWED`, a API responde `409` e só prossegue com `?force=true`. Com `force`, os blocos anteriores são substituídos numa única transação, e o run anterior continua no histórico.
- **Regenerar (`TRANSLATE_ONLY`):** mantém os blocos e o OCR e substitui apenas as sugestões `source=AUTO`. As sugestões `MANUAL` são preservadas.
- Duas execuções simultâneas na mesma página são proibidas: um lock por `page_id` faz a segunda chamada devolver `409`.

### 17.3 Ferramentas recomendadas *(Revisão L7 — decisão final em Q1)*

| Etapa | Opção recomendada | Alternativa |
|---|---|---|
| Detecção | `comic-text-detector` (modelo treinado em mangá) | LLM multimodal devolvendo bboxes |
| OCR | `manga-ocr` (especializado em japonês de mangá, texto vertical) | PaddleOCR (japonês), LLM multimodal |
| Classificação `#`/`$` | LLM multimodal com o recorte ampliado + heurística de contorno | Classificador próprio (V2) |
| Tradução | LLM multimodal (por exemplo Claude), numa única chamada por página, com saída estruturada | — |

### 17.4 Estado estruturado da análise (`PageAnalysisState`) *(AI-First)*

O Orchestrator trabalha sobre um objeto de estado que acumula decisões ao longo das etapas. Cada etapa lê e atualiza esse objeto; o banco só recebe o estado final (ou checkpoints intermediários para recuperação de falhas).

```python
@dataclass
class DialogueState:
    id: str
    bbox: BBox
    original: str | None
    lines: list[str]
    ruby: list[RubyPair]
    handwritten: bool
    orientation: Orientation
    type: Literal["#", "$"] | None
    location: str | None
    order: int | None
    ocr_confidence: float | None
    needs_review: bool
    review_reason: str | None
    translations: list[TranslationSuggestion]

@dataclass
class PageAnalysisState:
    page_id: UUID
    run_id: UUID
    image_path: str
    reading_direction: Literal["rtl", "ltr"]
    panels: list[PanelRegion]
    dialogues: list[DialogueState]
    agent_log: list[AgentLogEntry]  # decisões e re-avaliações auditáveis
```

O `agent_log` registra cada decisão do Orchestrator (incluindo re-avaliações), o que permite auditar o comportamento do agente e calcular métricas por etapa. O estado completo é serializado em `processing_runs.model_metadata` ao final da execução.

### 17.5 Re-avaliação de etapas *(AI-First)*

O Orchestrator não é um pipeline rígido: quando uma etapa produz baixa confiança, ele pode retroceder e tentar com mais informação antes de delegar ao revisor humano.

```
OCR devolve confidence < threshold
         ↓
Orchestrator avalia o contexto:
  handwritten = true  → mantém, marca NEEDS_REVIEW, segue
  bbox muito pequeno  → tenta mesclar com região vizinha e re-executa OCR
  caso geral          → envia recorte ampliado (padding 20%) ao VisionProvider
         ↓
VisionProvider devolve texto corrigido
         ↓
OCR corrigido → classificação → tradução
```

Regras de re-avaliação definidas para o MVP:

| Gatilho | Ação do Orchestrator |
|---|---|
| `ocr_confidence < threshold` e `handwritten = false` | Envia recorte ampliado ao `VisionProvider`; substitui `original` se a nova confiança for maior. |
| Resposta do LLM inválida (Pydantic) | Nova tentativa com a mensagem de erro no prompt (máx. 2 tentativas, conforme F5-AG-03). |
| `type` indefinido após classificação | Re-envia a região com os blocos vizinhos como contexto adicional. |

Cada re-avaliação é registrada em `agent_log` com o gatilho, a ação e o resultado (confiança antes/depois). O limite de tentativas por bloco é configurável (`MAX_REEVAL_PER_BLOCK`, padrão `2`) para evitar loops infinitos.

### 17.6 Verificação de consistência *(AI-First)*

Após a tradução (etapa 7), o Orchestrator executa uma verificação de consistência semântica antes de persistir. Esta etapa é diferente da validação estrutural (etapa 10): ela verifica o significado, não o formato.

**Regras de consistência aplicadas no MVP:**

| Verificação | Como é feita | Ação |
|---|---|---|
| Nome próprio novo | Nome em `traducao` não está em `characters` nem no original romanizado | Sinaliza `needs_review = true`, `review_reason = "nome não catalogado"` |
| Tradução idêntica para originais diferentes | Mesmo texto em `traducao` para 3+ blocos com originais distintos | Sinaliza como provável erro de cópia |
| Tradução contém japonês | Detecta caracteres CJK em `traducao` | Rejeita e tenta nova geração (até 1 retry) |
| Comprimento desproporcional | `len(traducao) > 5 × len(original)` ou `< 0.1 × len(original)` | Sinaliza para revisão humana |
| Inconsistência com página anterior aprovada | Mesmo `original` apareceu em outra página com tradução diferente na mesma obra | Injeta ambas no prompt e pede ao agente para desambiguar ou confirmar a preferência |

A verificação de inconsistência com páginas anteriores requer que existam páginas com status `APPROVED` na mesma obra. No MVP é feita como lookup no banco antes da chamada ao LLM.

### 17.7 Guardrails *(AI-First)*

Guardrails são regras de controle aplicadas na etapa 9, após a verificação de consistência e antes da validação estrutural. Ao contrário das verificações de consistência (que podem gerar uma nova chamada ao LLM), guardrails são determinísticos e imediatos.

**Guardrails do MVP:**

| Regra | Violação → Ação |
|---|---|
| `original` não pode estar vazio ou ser só espaço | Bloqueia persistência; registra `ERROR` no bloco |
| `traducao` não pode ser idêntica a `original` (o LLM devolveu o japonês sem traduzir) | Rejeita e faz retry; se persistir, marca `NEEDS_REVIEW` |
| `relevancia` deve ser inteiro 1–5 | Corrige automaticamente para 1 se inválido (non-breaking) |
| Número de sugestões > 5 | Trunca para as 5 primeiras por `relevancia` |
| `observacao` com mais de 500 caracteres | Trunca com aviso no log; não bloqueia |
| Output do LLM sem campo `traducoes` | Bloqueia e faz retry; se persistir, `ERROR` na página |
| Token budget excedido (`MAX_TOKENS_PER_PAGE`) | Interrompe a chamada, divide a página em lotes menores e retenta |

Os guardrails são configuráveis via env vars e podem ser desativados individualmente para testes. Todas as violações são registradas em `agent_log` com o guardrail acionado e a ação tomada.

### 17.8 Observabilidade e controle de custo *(AI-First)*

Cada chamada a um `AIProvider` é um **span** rastreável, associado ao `run_id` da execução:

```python
@dataclass
class ProviderSpan:
    span_id: UUID
    run_id: UUID
    stage: str           # "ocr", "classification", "translation", etc.
    provider: str        # "manga-ocr", "claude-3-5-sonnet", etc.
    model_version: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float      # estimado, baseado no pricing configurado
    success: bool
    fallback_used: bool
```

Os spans são gravados em `processing_runs.model_metadata` (JSONB) e expõem os dados via `GET /api/pages/{id}/runs`.

**Budget guard:** se `sum(cost_usd)` dos spans de um run exceder `MAX_COST_PER_PAGE_USD` (padrão `0.10`), o Orchestrator pausa, registra alerta em `agent_log` e aguarda confirmação via `POST /api/runs/{id}/approve-cost`. No MVP o alerta aparece no frontend como toast; na V2 pode enviar notificação.

**Fallback de modelos:** cada Provider define uma cadeia de fallback ativada em timeout (> `PROVIDER_TIMEOUT_S`) ou erro HTTP 5xx:

| Provider | Primário | Fallback 1 | Fallback 2 |
|---|---|---|---|
| `TranslationProvider` | Claude (configurado) | GPT-4o | — |
| `VisionProvider` | GPT-4o Vision | Claude Vision | — |
| `OCRProvider` | `manga-ocr` (local) | PaddleOCR (local) | `VisionProvider` (LLM) |

`fallback_used = true` no span sinaliza que o modelo primário falhou. Se todas as alternativas falharem, a etapa vai para `ERROR` e o Orchestrator interrompe o pipeline.

### 17.9 Avaliação de prompts *(AI-First)*

O versionamento de prompts (seção 24) só é útil se existir uma forma sistemática de medir o impacto de uma mudança. A avaliação de prompts usa o conjunto *golden* (F3-QA-01) como base.

**Fluxo de avaliação:**

```
Novo prompt candidato (v2.txt)
         ↓
Rodar sobre o golden set (≥10 páginas com gabarito humano)
         ↓
LLM-as-judge: o modelo avalia cada tradução em 4 dimensões:
  1. Fidelidade ao original (1–5)
  2. Naturalidade em PT-BR (1–5)
  3. Consistência com o contexto da obra (1–5)
  4. Utilidade da observação (1–5)
         ↓
Score agregado comparado com o prompt anterior
         ↓
Aprovado? → promove para versão ativa em production
Reprovado? → registra no histórico, descarta
```

O script de avaliação fica em `evals/run_prompt_eval.py`, produz um relatório JSON em `evals/results/` e é executado no CI a cada mudança em `prompts/`. A versão ativa é controlada por variável de ambiente (`ACTIVE_PROMPT_VERSION`), sem precisar de novo deploy.

## 18. Contexto enviado ao agente de tradução

- Texto original.
- Tipo (`#` ou `$`).
- Localização.
- Textos anteriores e posteriores da mesma página, respeitando a ordem de leitura.
- Imagem da página ou recorte, quando houver modelo de visão disponível.
- Indicação de que a saída deve ser em português brasileiro.
- Instrução para não inventar contexto.
- **(MVP — seção 30.1)** Personagens da obra: nome preferido, registro de fala e notas. Se o bloco tiver um personagem associado via `character_mentions`, ele é destacado no contexto: "Este texto é de Sakiko (registro: infantil)."
- **(MVP — seção 17.6)** Traduções já aprovadas do mesmo `original` em outras páginas da obra, para suportar a verificação de consistência: "Este original já foi traduzido como X na página 3."
- **(V2)** Entradas do glossário da obra que aparecem no texto.
- **(Revisão)** Confiança do OCR, para que o modelo sinalize a incerteza na observação.
- **(Revisão L10)** O furigana (`ruby`) e a marcação `handwritten` de cada bloco.

## 19. Frontend Angular

> **Atualização:** o fluxo detalhado do frontend (pastas locais, processamento "N de T", miniaturas, modal de conferência e exportação TXT) está em [FRONTEND_Especificacao.md](FRONTEND_Especificacao.md). Onde houver conflito, ele prevalece sobre as seções 19 e 20. Os impactos no backend estão listados na seção 11 daquele documento.

Telas e módulos previstos (visão original):

| Tela | Funcionalidades |
|---|---|
| Pastas | Criar, renomear, abrir, excluir e listar pastas. |
| Páginas | Upload (arrastar e soltar, vários arquivos), nome do arquivo, status de processamento, página seguinte/anterior. |
| Revisão da página | Imagem central com caixas numeradas e painel lateral com original, tipo, localização e traduções. |
| Editor de tradução | Editar sugestões, adicionar ou remover sugestões, alterar relevância e observação. |
| Ordenação | Mostrar a ordem aplicada e permitir correção manual. |
| Exportação | Visualizar e baixar ou copiar o JSON final. |

## 20. UX da revisão

- Cada região detectada é desenhada sobre a imagem com o número correspondente à propriedade `ordem`.
- Clicar numa região seleciona o item correspondente na lista.
- Clicar num item destaca a região correspondente na imagem.
- O tipo `#`/`$` deve ser fácil de alterar.
- O usuário deve conseguir editar o original quando o OCR errar.
- O usuário deve conseguir mudar a ordem sem editar todos os números à mão.
- Ao mudar a ordem, o sistema renumera automaticamente.
- O usuário deve conseguir marcar um bloco como "revisado".
- A exportação deve ser bloqueada ou sinalizada quando houver blocos com OCR de baixa confiança, se essa política estiver habilitada.
- **(Revisão)** A ordem é alterada arrastando os itens da lista (Angular CDK DragDrop) ou com os atalhos `Alt+↑`/`Alt+↓`.
- **(Revisão)** Um bloco manual é criado desenhando um retângulo sobre a imagem, no modo "Adicionar região".
- **(Revisão)** Atalhos de teclado: `J`/`K` para o próximo/anterior bloco, `T` para alternar `#`/`$`, `R` para marcar como revisado, `←`/`→` para a página anterior/seguinte.
- **(Revisão)** Zoom e pan na imagem, com as caixas acompanhando a escala.

## 21. Estados de processamento

| Status | Significado |
|---|---|
| `PENDING` | Página cadastrada, ainda não analisada. |
| `PROCESSING` | Agente em execução. |
| `REVIEW` | Resultado disponível para revisão humana. |
| `APPROVED` | Página revisada e aprovada. |
| `ERROR` | O processamento falhou; o erro fica registrado. |

**Transições permitidas** *(Revisão)*:

```
PENDING ──analyze──> PROCESSING ──ok──> REVIEW ──approve──> APPROVED
                          │                ▲                   │
                          └──falha──> ERROR ┘(reanalyze)       │
REVIEW/APPROVED/ERROR ──analyze/regenerate──> PROCESSING       │
APPROVED ──qualquer edição──> REVIEW <─────────────────────────┘
```

## 22. Validações do JSON

- A raiz deve ser um array.
- `ordem` deve ser um inteiro positivo e não repetido.
- **(Revisão)** `ordem` deve ser sequencial, de 1 a N, sem lacunas.
- `tipo` deve ser exatamente `#` ou `$`.
- `original` não pode ser nulo.
- `localizacao` não pode ser nula.
- `traducoes` deve ser um array.
- **(Revisão)** `traducoes` deve ter pelo menos 1 e no máximo 5 itens.
- Cada tradução deve ter `traducao`, `observacao` e `relevancia`.
- `relevancia` deve ser um inteiro de 1 a 5.
- Não é permitido exportar JSON inválido.
- O backend é a fonte final da validação, mesmo que o frontend também valide.

## 23. Exemplo de análise da página fornecida

A imagem de referência mostra dois padrões que o sistema precisa suportar: falas em balões e textos editoriais ou gráficos fora de balão. O sistema deve tratar títulos, chamadas, nomes, legendas e elementos de logo como unidades independentes, sempre que forem detectáveis como texto.

A numeração visual segue a regra definida neste PRD, mesmo quando a posição dos elementos é irregular. Por exemplo, um balão no topo direito vem antes de um balão logo abaixo dele. Os textos fora de balão também participam da mesma sequência, a menos que uma configuração futura permita separar "fala" e "editorial".

### 23.1 Imagens de referência *(Revisão R6)*

| Arquivo | Dimensões | Conteúdo | Gabarito |
|---|---|---|---|
| `docs/referencias/pagina_01.webp` | 750×1200 | Página com 2 painéis: caderno manuscrito, 2 balões e narração em cima; seis desenhos infantis com etiquetas de nome e narração central embaixo | `pagina_01.expected.json` (12 blocos) |
| `docs/referencias/banner_01.png` | 750×166 | Faixa editorial horizontal: chamada comemorativa, logo da obra, chamada de suspense e manchete | `banner_01.expected.json` (4 blocos) |

Os metadados técnicos (bbox estimado, `lines`, `ruby`, manuscrito, falsos positivos) estão em `gabarito.meta.json`.

> ⚠️ Os gabaritos foram montados a partir da leitura visual das imagens e **precisam ser validados por um revisor humano** antes de servirem como métrica oficial. Os bboxes são estimativas manuais.

### 23.2 Ordem esperada — `pagina_01`

| Ordem | Tipo | Original | Localização | Observação de análise |
|---|---|---|---|---|
| 1 | `#` | きめたよ! | Topo direita | Balão |
| 2 | `#` | おれも | Topo centro-direita (abaixo do balão 1) | Balão |
| 3 | `$` | だれかをしあわせにするひと | Dentro do caderno (topo) | Manuscrito, horizontal, 2 linhas |
| 4 | `$` | ──誰よりも何よりも | Painel superior esquerdo | Narração vertical, 2 colunas, furigana |
| 5 | `$` | とくだ さきこ | Painel inferior, etiqueta superior direita | Etiqueta de nome |
| 6 | `$` | しあわせにするん | Dentro do desenho (centro direita) | Manuscrito, **leitura incerta** (ん/人) |
| 7 | `$` | あべかわ さくら | Painel inferior, etiqueta central direita | Etiqueta de nome |
| 8 | `$` | みやた ゆき | Painel inferior, etiqueta inferior direita | Etiqueta de nome |
| 9 | `$` | 君のおかげだから | Centro do painel inferior (grande) | Narração, continua o bloco 4, furigana |
| 10 | `$` | はせがわ ごうた | Painel inferior, etiqueta superior esquerda | Etiqueta de nome |
| 11 | `$` | にしかわ じろう | Painel inferior, etiqueta central esquerda | Etiqueta de nome |
| 12 | `$` | くぼ りょうじ | Painel inferior, etiqueta inferior esquerda | Etiqueta de nome |

Não é texto: o `田` desenhado como janela da casa e os traços do sol, que são falsos positivos esperados.

### 23.3 Ordem esperada — `banner_01`

| Ordem | Tipo | Original | Localização | Observação de análise |
|---|---|---|---|---|
| 1 | `$` | 上位5名に続く人気キャラは誰かな…!? | Topo direita (2 linhas) | Chamada editorial, furigana |
| 2 | `$` | 幸福喫茶3丁目 | Dentro do logo (centro) | Título da obra, candidato ao glossário |
| 3 | `$` | 連載50回記念企画♡ | Topo esquerda | Editorial; preservar `♡` |
| 4 | `$` | キャラクターコンテスト結果発表!! | Inferior (grande, largura total) | Manchete, bloco largo que forma sub-faixa |

### 23.4 O que as imagens revelaram

1. A regra literal de ordenação falha nas duas imagens, e a divisão em faixas resolve os dois casos (seção 6.1).
2. Furigana está presente em quase todo texto impresso com kanji (seção 9.1).
3. Uma narração pode ocupar duas colunas, ou atravessar painéis como os blocos 4 e 9 (seção 9.2).
4. O texto manuscrito é frequente e ambíguo (seção 9.3).
5. Nenhum `#` aparece no banner: o texto editorial é todo `$`, o que confirma a regra de títulos e logos (seção 11).
6. Um banner horizontal (*yokogaki*) seria lido naturalmente da **esquerda para a direita** (連載 → logo → chamada), mas a regra do PRD produz a ordem inversa na linha superior. Ver a questão Q8.

## 24. Prompt-base do agente

```text
Você é um agente especializado em análise e tradução de páginas de mangá japonês.

REGRAS:
1. Detecte todas as regiões textuais relevantes.
2. Preserve o original japonês exatamente como reconhecido; não traduza o campo original.
3. Ordene as regiões da direita para a esquerda e de cima para baixo.
4. Dentro de cada região, preserve a orientação e a sequência natural dos caracteres japoneses.
5. Use tipo "#" para texto dentro de balão e "$" para texto fora de balão.
6. Descreva a localização em português de forma curta, como "Topo direita", "Centro (grande)" ou "Dentro do logo (direita)".
7. Traduza para português brasileiro.
8. Gere alternativas quando houver ambiguidade real.
9. Use relevancia de 1 a 5, sendo 1 a sugestão mais adequada.
10. Use observacao para explicar onomatopeias, fragmentos, ambiguidades, nuances e contexto relevante.
11. Não invente nomes, acontecimentos ou contexto que não estejam sustentados pela imagem ou pelos textos disponíveis.
12. Retorne somente a estrutura JSON definida pelo contrato.
```

> **Revisão:** o prompt deve ser versionado (`prompts/translate_page.v1.txt`), e a versão usada fica registrada em `processing_runs.prompt_version`. Quando o pipeline já tiver feito a detecção, o OCR e a ordenação (etapas 2–6), o LLM **não** deve reordenar nem alterar o `original`: ele recebe os blocos prontos e devolve apenas `tipo` (quando for o caso), `localizacao` (refinamento) e `traducoes`, identificados pelo `ordem`. Assim o LLM não sobrescreve decisões determinísticas.

## 25. Requisitos não funcionais

- **(Revisão R1)** TypeScript *strict* no frontend. No backend, Python tipado (type hints + `mypy --strict` ou `pyright`) e Pydantic v2.
- API com tratamento consistente de erros (padrão definido na seção 16).
- Processamento assíncrono para páginas grandes ou várias páginas.
- Logs de cada execução do agente (estruturados em JSON, com `run_id` e `page_id`).
- Idempotência: reprocessar uma página não pode criar duplicações silenciosas (seção 17.2).
- Versionamento dos resultados de OCR e tradução (recomendado).
- Banco relacional com migrations (Alembic).
- Segredos das APIs mantidos somente no backend (variáveis de ambiente, nunca no bundle do Angular).
- Upload validado por extensão, MIME type (verificando os *magic bytes*) e tamanho. **(Revisão)** Formatos `jpg`, `jpeg`, `png` e `webp`, com limite padrão de 20 MB por arquivo.
- JSON exportado em UTF-8 (`ensure_ascii=False`), para preservar o japonês e o português.
- **(Revisão)** Meta de desempenho: uma página A5 típica processada (`FULL`) em até 60 s (p90).
- **(Revisão)** Acessibilidade: contraste AA na paleta (seção 27) e navegação completa por teclado na tela de revisão.
- **(Revisão)** Testes: unitários para a ordenação, a localização e o validador; testes de contrato da API; conjunto *golden* de páginas reais.
- **(AI-First — seção 17.8)** Observabilidade: cada chamada a um AIProvider gera um span com model, tokens, latência e custo estimado. Spans gravados em `model_metadata` e acessíveis via API.
- **(AI-First — seção 17.8)** Controle de custo: budget guard por página (`MAX_COST_PER_PAGE_USD`); frontend exibe custo acumulado da obra na tela de pastas.
- **(AI-First — seção 17.8)** Fallback de modelos: cada Provider define cadeia primário → fallback; `fallback_used` registrado no span.
- **(AI-First — seção 17.7)** Guardrails determinísticos aplicados antes da persistência; violações registradas em `agent_log`.
- **(AI-First — seção 17.9)** Avaliação de prompts: script `evals/run_prompt_eval.py` roda no CI a cada mudança em `prompts/`; usa LLM-as-judge contra o golden set.

## 26. Critérios de aceite do MVP

- [ ] Consigo criar uma pasta e cadastrar páginas.
- [ ] Consigo ver o nome do arquivo de cada página.
- [ ] Consigo executar a análise de uma página.
- [ ] O agente detecta os textos e cria blocos persistidos no banco.
- [ ] Cada bloco tem original, tipo, localização e ordem.
- [ ] A ordem segue direita → esquerda e cima → baixo.
- [ ] Cada bloco tem pelo menos uma sugestão de tradução.
- [ ] Cada sugestão tem `traducao`, `observacao` e `relevancia`.
- [ ] Consigo editar OCR, tipo, localização, ordem e traduções.
- [ ] O frontend mostra as regiões numeradas sobre a imagem.
- [ ] O backend gera um JSON válido, exatamente no contrato definido.
- [ ] Depois de recarregar a aplicação, os resultados continuam disponíveis porque estão persistidos no banco.
- [ ] Consigo exportar o JSON da página.
- [ ] **(Revisão)** Consigo criar e excluir blocos manualmente.
- [ ] **(Revisão)** Consigo aprovar a página, e a política de baixa confiança é respeitada.
- [ ] **(Revisão)** Reanalisar uma página revisada exige confirmação e não duplica blocos.

---

## 27. Design system — Tailwind CSS, paleta red

*(Nova seção — Revisão L8)*

### 27.1 Setup

- Tailwind CSS v4 integrado ao Angular via PostCSS (`tailwindcss`, `@tailwindcss/postcss`, `.postcssrc.json`).
- Tokens semânticos em `src/styles.css`, apontando para a paleta `red` do Tailwind. Os componentes usam **apenas os tokens semânticos** (`bg-primary-600`), nunca `red-*` diretamente, para que a cor possa ser trocada sem refatoração.

```css
@import "tailwindcss";

@theme {
  --color-primary-50:  var(--color-red-50);
  --color-primary-100: var(--color-red-100);
  --color-primary-200: var(--color-red-200);
  --color-primary-300: var(--color-red-300);
  --color-primary-400: var(--color-red-400);
  --color-primary-500: var(--color-red-500);
  --color-primary-600: var(--color-red-600);
  --color-primary-700: var(--color-red-700);
  --color-primary-800: var(--color-red-800);
  --color-primary-900: var(--color-red-900);
  --color-primary-950: var(--color-red-950);
}

@custom-variant dark (&:where(.dark, .dark *));
```

### 27.2 Tokens de uso

| Papel | Claro | Escuro |
|---|---|---|
| Fundo da aplicação | `bg-zinc-50` | `bg-zinc-950` |
| Superfície (cards e painéis) | `bg-white border-zinc-200` | `bg-zinc-900 border-zinc-800` |
| Texto principal / secundário | `text-zinc-900` / `text-zinc-600` | `text-zinc-100` / `text-zinc-400` |
| Botão primário | `bg-primary-600 hover:bg-primary-700 active:bg-primary-800 text-white` | `bg-primary-500 hover:bg-primary-400 text-zinc-950` |
| Botão secundário | `border-primary-600 text-primary-700 hover:bg-primary-50` | `border-primary-400 text-primary-300 hover:bg-primary-950` |
| Link | `text-primary-700 hover:text-primary-800 underline` | `text-primary-400` |
| Foco (todos os interativos) | `focus-visible:ring-2 ring-primary-500 ring-offset-2` | idem, `ring-offset-zinc-950` |
| Item selecionado na lista | `bg-primary-50 border-l-4 border-primary-600` | `bg-primary-950 border-primary-500` |

> Contraste: `red-600` sobre branco atinge ~4,8:1 (AA para texto normal). Não usar `red-500` ou mais claro para texto sobre fundo branco.

### 27.3 Overlays da tela de revisão

Os tipos se distinguem por **cor e padrão de borda**, para não depender só da cor:

| Elemento | Classes |
|---|---|
| Região `#` (balão) | `border-2 border-solid border-primary-600 bg-primary-500/10` |
| Região `$` (fora de balão) | `border-2 border-dashed border-primary-400 bg-primary-300/10` |
| Região selecionada | `ring-4 ring-primary-300 bg-primary-500/20` |
| Região com baixa confiança | ícone ⚠ no canto + `outline-dotted outline-amber-500` |
| Selo do número (`#`) | `bg-primary-600 text-white rounded-full size-6 text-xs font-bold` |
| Selo do número (`$`) | `bg-white text-primary-700 border-2 border-primary-600 rounded-full size-6 text-xs font-bold` |

### 27.4 Status e feedback

Como o vermelho é a cor da marca, os estados **sempre** combinam ícone e rótulo de texto. As exceções `amber` e `emerald`, limitadas a estados semânticos, dependem da questão Q5.

| Status | Badge |
|---|---|
| `PENDING` | `bg-zinc-100 text-zinc-700` + ícone relógio |
| `PROCESSING` | `bg-primary-50 text-primary-700` + spinner `animate-spin` |
| `REVIEW` | `bg-amber-100 text-amber-800` + ícone olho |
| `APPROVED` | `bg-emerald-100 text-emerald-800` + ícone check |
| `ERROR` | `bg-primary-900 text-white` + ícone alerta (tom escuro, para não confundir com o primário) |

**Relevância (1–5)**, com gradiente da própria paleta: `1 → bg-primary-700 text-white`, `2 → bg-primary-500 text-white`, `3 → bg-primary-300 text-primary-950`, `4 → bg-primary-200 text-primary-900`, `5 → bg-primary-100 text-primary-800`.

### 27.5 Componentes base (biblioteca interna)

`ui-button`, `ui-badge`, `ui-card`, `ui-input`, `ui-textarea`, `ui-select`, `ui-dialog` (confirmação destrutiva), `ui-toast`, `ui-dropzone`, `ui-empty-state`, `ui-skeleton`, `ui-kbd` (atalhos).

---

## 28. Fases de entrega (detalhadas)

*(Substitui o antigo "Backlog sugerido" — Revisão L9)*

**Visão geral:**

| Fase | Nome | Resultado demonstrável |
|---|---|---|
| F0 | Fundação | Monorepo rodando com `docker compose up`, CI verde e tema red aplicado |
| F1 | Obras, pastas, páginas e personagens | Criar obra/pasta, subir páginas, cadastrar personagens |
| F2 | Blocos, revisão manual e contrato JSON | Criar blocos à mão sobre a imagem e exportar JSON válido |
| F3 | Pipeline assíncrono, detecção e OCR | "Analisar página" gera blocos com bbox e original |
| F4 | Ordenação, classificação e localização | Blocos numerados na ordem correta, com `#`/`$` e localização |
| F5 | Agente de tradução completo | Sugestões em PT-BR com consistência, guardrails e observabilidade |
| F6 | Revisão completa, aprovação e exportação | Fluxo ponta a ponta: MVP pronto |
| V2 | Escala e memória da obra | Lote por capítulo, glossário, versionamento, painéis completos |
| V3 | Integrações | Exportação para ferramentas de lettering |

> O contrato JSON e o validador sobem para a F2 (antes em MVP-6) porque são a etapa 10 do pipeline. Desde a F3 toda saída do agente já é validada contra o contrato final, e a tela de revisão pode ser construída e testada com blocos manuais antes de o OCR existir.

**Estrutura de cada card:** `ID | Descrição | Aceite | Ref` — onde **Aceite** é a condição verificável e objetiva de conclusão do card e **Ref** é a seção do PRD com a especificação detalhada. Cards ordenados por área: DB → OPS → BE → AG → FE → QA.

---

### F0 — Fundação

**Objetivo:** base técnica para que todas as fases seguintes entreguem funcionalidade sem retrabalho de infraestrutura.

| ID | Descrição | Aceite | Ref |
|---|---|---|---|
| F0-DB-01 | SQLAlchemy 2 + Alembic configurados; migration inicial vazia; sessão por request. | `alembic upgrade head` aplica sem erro; `/health` retorna `{"db": "ok"}`. | 14 |
| F0-OPS-01 | Estrutura de diretórios (`frontend/`, `backend/`, `contracts/`, `docs/`, `prompts/`, `evals/`) e README de setup. | Clone + README é suficiente para rodar o projeto do zero. | 4.1 |
| F0-OPS-02 | `docker-compose` com PostgreSQL, Redis (fila), backend e frontend; `.env.example` com todas as variáveis. | `docker compose up` sobe tudo; `GET /health` responde `200`. | 4 |
| F0-OPS-03 | CI: lint + typecheck + testes (ruff, mypy, pytest; eslint, `tsc --noEmit`, testes Angular). | Push no branch executa CI; falha em erro de tipo ou lint. | 25 |
| F0-BE-01 | Esqueleto FastAPI: settings (pydantic-settings), `/health`, handler de erro padrão, logging estruturado com `run_id`. | Erro proposital gera resposta `{"error": {...}}` no padrão da seção 16. | 16 |
| F0-FE-01 | Esqueleto Angular (standalone, roteamento, `HttpClient` com interceptor de erro global). | Rotas `/**` renderizam sem erro de console; interceptor exibe toast em 4xx/5xx. | 19 |
| F0-FE-02 | Tailwind v4 + tokens `primary` → `red`, modo escuro, fonte CJK (`Noto Sans JP`). | Página de demo exibe os tokens em claro e escuro com contraste AA verificado. | 27.1 |
| F0-FE-03 | Componentes base: `ui-button`, `ui-badge`, `ui-card`, `ui-dialog`, `ui-toast`. | Todos os componentes renderizados nos dois temas sem erro de console. | 27.5 |

**Aceite da fase:** `docker compose up` → CI verde → página de demo com todos os componentes em light/dark com contraste AA.  
**Dependências:** nenhuma. **Riscos:** baixos.

---

### F1 — Obras, pastas, páginas e personagens

**Objetivo:** organizar obras, pastas, páginas e personagens com upload seguro; base de contexto para o agente.

| ID | Descrição | Aceite | Ref |
|---|---|---|---|
| F1-DB-01 | Migrations de `works`, `folders`, `pages`, `characters` e `character_mentions` com enums de status. | `alembic upgrade head` aplica; todas as constraints e enums criados. | 14, 30.1 |
| F1-BE-01 | CRUD de obras: `GET/POST /api/works`, `GET/PATCH/DELETE /api/works/{id}`. | CRUD completo com validações; exclusão em cascata com confirmação. | 16 |
| F1-BE-02 | CRUD de pastas: `GET/POST /api/folders`, `GET/PATCH/DELETE /api/folders/{id}`. | `folder.work_id` nullable no MVP; CRUD completo. | 16 |
| F1-BE-03 | Upload `POST /api/folders/{id}/pages`: vários arquivos, validação de extensão, MIME (magic bytes) e tamanho; grava `width`, `height` e `sha256`. | `.exe` renomeado para `.jpg` → `415`; arquivo > 20 MB → `413`. | 16 |
| F1-BE-04 | `GET/PATCH/DELETE /api/pages/{id}` e `GET /api/pages/{id}/image`; número de página automático pelo nome. | Imagem servida com Content-Type correto; `page_number` editável. | 16 |
| F1-BE-05 | CRUD de personagens: `GET/POST /api/works/{id}/characters`, `GET/PATCH/DELETE /api/characters/{id}`; `POST /api/text-blocks/{id}/character` para associação. | Personagem criado e associado a um bloco; context builder inclui o personagem no payload ao agente. | 30.1 |
| F1-FE-01 | Tela **Obras/Pastas**: listar, criar, renomear, excluir (com confirmação); estado vazio. | Criar obra → criar pasta → navegar; `ui-empty-state` exibido quando vazio. | 19 |
| F1-FE-02 | Tela **Páginas**: `ui-dropzone` para arrastar e soltar, progresso do upload, grade de miniaturas com status badge. | Upload de 10 imagens simultâneas; cada uma aparece com nome e badge `PENDING`. | 19 |
| F1-FE-03 | Navegação entre páginas (anterior/seguinte) e rota `/folders/{id}/pages/{pageId}`. | Atalhos `←`/`→` navegam; URL reflete a página atual. | 20 |
| F1-FE-04 | Tela **Personagens da obra**: listar, criar e editar (nome, pronomes, registro de fala, notas). | Criar personagem → salvar → campo `speech_register` com select de opções válidas. | 30.1 |
| F1-QA-01 | Testes de API para CRUD de obras, pastas, páginas e upload (inválido, grande demais, MIME falso). | Happy paths e os 3 erros de upload cobertos por testes automáticos. | 16 |

**Aceite da fase:** criar obra → pasta → subir 10 imagens → criar personagem → associar a um bloco; tudo persiste após reload.  
**Dependências:** F0. **Riscos:** baixos.

---

### F2 — Blocos de texto, revisão manual e contrato JSON

**Objetivo:** tela de revisão e persistência de blocos funcionando sem IA; contrato de exportação estabelecido desde o início.

| ID | Descrição | Aceite | Ref |
|---|---|---|---|
| F2-DB-01 | Migrations de `text_blocks`, `translation_suggestions` e `processing_runs` com constraints (tipo, relevância, `(page_id, order_number)` deferrable). | Insert com `order_number` duplicado rejeita fora de transação; constraint de relevância 1–5 aplicada. | 14 |
| F2-BE-01 | Modelos Pydantic do contrato + geração de `contracts/page-export.schema.json`. | `python -m contracts.generate` produz o JSON Schema versionado no repo. | 13 |
| F2-BE-02 | Validador de exportação com todas as regras da seção 22, mensagens de erro por campo. | Cada regra tem teste unitário com caso válido e inválido. | 22 |
| F2-BE-03 | `POST /api/pages/{id}/text-blocks`, `PATCH/DELETE /api/text-blocks/{id}` (exclusão renumera os demais). | Criar → editar → excluir bloco; `order_number` renumerado em transação sem lacunas. | 16 |
| F2-BE-04 | `POST /api/text-blocks/{id}/translations`, `PATCH/DELETE /api/translations/{id}` (não permite remover a última). | Remover a única sugestão retorna `409`. | 16 |
| F2-BE-05 | `POST /api/pages/{id}/reorder` com lista de IDs renumerando em transação. | Lista aleatória enviada → `order_number` 1..N sem lacunas. | 16 |
| F2-BE-06 | `GET /api/pages/{id}/json`: gera do banco, valida e devolve UTF-8; `?download=true`. | JSON exportado passa no validador da seção 22; caracteres japoneses preservados. | 16, 22 |
| F2-FE-01 | Tela **Revisão**: imagem com zoom e pan; overlay SVG de regiões na escala da imagem (estilos da seção 27.3). | Zoom 0.5×–3×; caixas acompanham sem desalinhar em imagens grandes. | 20, 27.3 |
| F2-FE-02 | Seleção bidirecional: clicar na região seleciona o item; clicar no item destaca a região. | Clique em qualquer dos dois lados sincroniza a seleção visualmente. | 20 |
| F2-FE-03 | Modo "Adicionar região": desenhar retângulo sobre a imagem cria bloco manual. | Retângulo desenhado vira bloco com `source=MANUAL`; aparece na lista e no overlay. | 20 |
| F2-FE-04 | Painel lateral: original (editável), alternância `#`/`$`, localização, lista de sugestões. | Editar original e salvar persiste; tecla `T` troca o tipo. | 20 |
| F2-FE-05 | Geração dos tipos TypeScript a partir do JSON Schema (`json-schema-to-typescript`) no build. | `npm run build` gera `contracts/page-export.d.ts`; Angular usa os tipos gerados. | 13 |
| F2-QA-01 | Testes unitários do validador (seção 22) e testes de contrato da API para blocos e sugestões. | Cobertura total das regras da seção 22; testes de contrato passam no CI. | 22 |

**Aceite da fase:** desenhar 3 regiões → preencher original e traduções → exportar JSON válido; exportar bloco sem tradução retorna `422`.  
**Dependências:** F1. **Riscos:** médios (precisão do overlay com zoom e imagens grandes).

---

### F3 — Pipeline assíncrono, detecção e OCR

**Objetivo:** "Analisar página" detecta regiões e extrai o japonês em segundo plano; base do pipeline do agente.

| ID | Descrição | Aceite | Ref |
|---|---|---|---|
| F3-OPS-01 | Worker (`arq` ou RQ) no compose; fila `analysis`; retry com backoff exponencial para falhas transitórias. | Worker no `docker compose ps`; job re-enfileirado após falha simulada. | 4 |
| F3-BE-01 | `POST /api/pages/{id}/analyze` → `202 {run_id}`; lock por página; transições de status. | Duas chamadas simultâneas: a segunda recebe `409`. | 16, 17.2 |
| F3-BE-02 | `GET /api/pages/{id}/runs`: histórico com status, duração, erro e spans por etapa. | Resposta inclui `spans` com modelo, tokens e latência por etapa. | 16, 17.8 |
| F3-BE-03 | Política de reprocessamento (seção 17.2): `409` quando há edições manuais, `?force=true` prossegue. | Página com bloco `MANUAL` → `409`; com `?force=true` → blocos substituídos em transação. | 17.2 |
| F3-AG-01 | Interface `Stage[In, Out]`, `PageAnalysisState`, `ProviderSpan` e orquestrador do pipeline. | Cada stage testável isoladamente; `agent_log` acumulado no estado ao longo do pipeline. | 17.1, 17.4 |
| F3-AG-02 | Pré-processamento: normalização de orientação (EXIF), redimensionamento com limite, conversão para RGB. | Imagem girada 90° pelo EXIF é corrigida antes da detecção. | 17 |
| F3-AG-03 | Detecção de regiões (ferramenta escolhida em Q1) → bboxes em pixels originais. | Recall medido no golden set e registrado em `docs/metricas.md` como linha de base. | 17.3 |
| F3-AG-04 | OCR japonês por região → `original`, `lines`, `orientation`, `ocr_confidence`. | `pagina_01` retorna originais reconhecíveis; CER medido e registrado. | 9, 17.3 |
| F3-AG-05 | Baixa confiança → re-avaliação com recorte ampliado (seção 17.5); se persistir → `NEEDS_REVIEW`. | Bloco com `ocr_confidence < 0.80` tenta `VisionProvider` antes de marcar `NEEDS_REVIEW`. | 17.5 |
| F3-AG-06 | Fusão do furigana ao bloco-pai (`ruby`); agrupamento de linhas contínuas em um bloco (`lines`). | `pagina_01`: `誰` com `ruby: [{base:"誰", reading:"だれ"}]`; colunas contínuas fundidas. | 9.1, 9.2 |
| F3-AG-07 | Marcação `handwritten = true` → `NEEDS_REVIEW` automático. | Blocos manuscritos da `pagina_01` marcados com `handwritten` e `NEEDS_REVIEW`. | 9.3 |
| F3-FE-01 | Botão "Analisar página", polling 2 s + backoff, badge `PROCESSING` com spinner, toast ao concluir ou falhar. | Análise inicia, badge muda para `PROCESSING`, toast aparece ao finalizar. | 21 |
| F3-FE-02 | Diálogo de confirmação quando API responde `409` (edições seriam substituídas). | Usuário vê o diálogo e pode cancelar ou confirmar com `?force=true`. | 17.2 |
| F3-QA-01 | Golden set: validar os 2 gabaritos iniciais, completar até ≥ 10 páginas reais; script de métricas (recall de detecção, CER). | `docs/metricas.md` com linha de base; métricas geradas automaticamente pelo script. | 23 |

**Aceite da fase:** página analisada → `REVIEW` com blocos, bboxes e originais persistidos; linha de base de métricas registrada.  
**Dependências:** F2, decisão Q1. **Riscos:** altos (OCR em fontes estilizadas; dependências de ML na imagem Docker).

---

### F4 — Ordenação, classificação `#`/`$` e localização

**Objetivo:** blocos numerados na ordem de leitura correta, tipados e com localização descritiva.

| ID | Descrição | Aceite | Ref |
|---|---|---|---|
| F4-AG-01 | Detecção de divisas horizontais de painel (moldura/calha ≥ 80% da largura) e blocos largos (> 60%). | `banner_01` detecta `キャラクター…` como sub-faixa própria. | 6.1 |
| F4-AG-02 | `ReadingOrderStrategy` + `tiered_column_rtl` (padrão) e `column_rtl` (referência). | `pagina_01` e `banner_01` saem na ordem exata das seções 23.2 e 23.3. | 6.1 |
| F4-AG-03 | Classificador `#`/`$`: recorte ampliado + LLM multimodal e/ou heurística de contorno; confiança registrada. | Acurácia ≥ 90% no golden set (meta a confirmar em Q4). | 7, 17.3 |
| F4-AG-04 | Localização híbrida: base 3×3 + tamanho (seção 8.1); refinamento opcional pelo LLM. | Bloco 1 da `pagina_01` → "Topo direita"; bloco 9 → "Centro do painel inferior (grande)". | 8.1 |
| F4-BE-01 | `POST /api/pages/{id}/reorder/auto` recalcula a ordem a partir dos bboxes. | Resultado idêntico ao que o pipeline produziria para a mesma página. | 16 |
| F4-FE-01 | Painel **Ordenação**: lista arrastável (CDK DragDrop), atalhos `Alt+↑/↓`, renumeração otimista, botão "Recalcular ordem". | Arrastar e soltar persiste a nova ordem; renumeração sem lacunas. | 20 |
| F4-FE-02 | Linha pontilhada opcional sobre a imagem ligando 1 → 2 → 3 para auditar a ordem visualmente. | Toggle mostra/oculta as linhas; linhas acompanham o zoom. | 20 |
| F4-QA-01 | Testes unitários da ordenação com layouts sintéticos (colunas, sobreposição, empate, página vazia, banner). | 100% das regras da seção 6 cobertas; cada layout sintético produz a ordem esperada. | 6 |
| F4-QA-02 | Métricas no golden set: acurácia de `#`/`$` e % de páginas com ordem 100% correta. | Métricas adicionadas em `docs/metricas.md`; linha de base estabelecida antes do F5. | 23 |

**Aceite da fase:** `pagina_01` e `banner_01` com ordem correta; acurácia `#`/`$` ≥ 90%; reordenação manual persiste.  
**Dependências:** F3. **Riscos:** altos (ordem em páginas com vários painéis; ver Q2).

---

### F5 — Agente de tradução completo

**Objetivo:** cada bloco recebe sugestões em PT-BR com contexto, consistência, guardrails e observabilidade de custo.

| ID | Descrição | Aceite | Ref |
|---|---|---|---|
| F5-AG-01 | Prompt versionado `prompts/translate_page.v1.txt`; registro de `prompt_version` em `processing_runs`. | Trocar o arquivo de prompt muda a versão no run sem redeploy. | 24 |
| F5-AG-02 | Montagem do contexto completo (seção 18): blocos, vizinhos, tipo, localização, OCR confidence, imagem, personagens e páginas aprovadas anteriores. | Payload inclui personagens da obra e traduções aprovadas do mesmo `original` em outras páginas. | 18, 30.1 |
| F5-AG-03 | Chamada ao LLM com saída estruturada validada por Pydantic; retry com mensagem de erro (máx. 2). | Output inválido gera retry; após 2 falhas, página vai para `ERROR`. | 17 |
| F5-AG-04 | Regras especiais (seção 11) cobertas por exemplos *few-shot* no prompt. | Onomatopeia e fragmento produzem `observacao` com a classificação correta. | 11 |
| F5-AG-05 | Cache por `hash(página + blocos + prompt_version)` evita custo repetido. | Reanalisar mesma página com mesmo prompt não gera nova chamada ao LLM. | 17 |
| F5-AG-06 | Verificação de consistência (etapa 8): lookup de traduções aprovadas; alertas das regras da seção 17.6. | Nome não presente em `characters` → `needs_review`; japonês em `traducao` → retry. | 17.6 |
| F5-AG-07 | Guardrails determinísticos (etapa 9): todas as regras da seção 17.7; configuráveis por env var; violações em `agent_log`. | `original` vazio bloqueia persistência; output sem `traducoes` → retry; violações no log. | 17.7 |
| F5-BE-01 | `POST /api/pages/{id}/regenerate` (`TRANSLATE_ONLY`, preserva sugestões `MANUAL`). | Regenerar mantém OCR e sugestões manuais; substitui apenas as `AUTO`. | 16, 17.2 |
| F5-BE-02 | Fallback de modelos: cadeia primário → fallback por provider; `fallback_used` no span. | Simular timeout no primário → fallback ativado; `fallback_used=true` no span. | 17.8 |
| F5-BE-03 | Budget guard e `ProviderSpan`: custo estimado por etapa em `model_metadata`; alerta quando excede `MAX_COST_PER_PAGE_USD`. | Página acima do limite pausa e exige confirmação; frontend exibe alerta com o valor. | 17.8 |
| F5-FE-01 | Lista de sugestões ordenada por relevância, badge em gradiente red (seção 27.4), observação visível. | Relevância 1 aparece primeiro; badge usa gradiente correto. | 27.4 |
| F5-FE-02 | Botão "Regenerar traduções" com confirmação; custo estimado exibido no toast. | Toast exibe custo estimado; sugestões manuais mantidas após regenerar. | 17 |
| F5-QA-01 | Avaliação qualitativa: revisão humana em ≥ 5 páginas *golden* (fidelidade, naturalidade, utilidade da observação). | Planilha preenchida; score médio registrado em `docs/metricas.md`. | 17.9 |
| F5-QA-02 | Script `evals/run_prompt_eval.py` com LLM-as-judge, 4 dimensões, integrado ao CI. | CI falha se score cair > 10% em relação ao baseline registrado. | 17.9 |

**Aceite da fase:** 100% dos blocos com ≥ 1 sugestão válida; guardrails bloquearam pelo menos um caso de teste; custo e latência dentro da meta da seção 25.  
**Dependências:** F4, decisão Q1. **Riscos:** médios (custo, alucinação de nomes, consistência entre páginas).

---

### F6 — Revisão completa, aprovação e exportação (fecha o MVP)

**Objetivo:** fluxo de revisão produtivo do upload ao JSON aprovado; todos os critérios da seção 26 marcados.

| ID | Descrição | Aceite | Ref |
|---|---|---|---|
| F6-BE-01 | `POST /api/pages/{id}/approve` com política `EXPORT_BLOCK_ON_LOW_CONFIDENCE`. | Aprovar página com bloco `NEEDS_REVIEW` → `422` quando a política está ativa. | 16, 26 |
| F6-BE-02 | Transição `APPROVED → REVIEW` automática ao editar qualquer bloco da página aprovada. | Editar bloco de página `APPROVED` muda status para `REVIEW` sem ação explícita. | 21 |
| F6-BE-03 | `GET /api/settings`: threshold de confiança, política de exportação e budget expostos. | Mudar `OCR_LOW_CONFIDENCE_THRESHOLD` via env var reflete na resposta sem redeploy. | 17.7, 17.8 |
| F6-FE-01 | **Editor de tradução**: adicionar, editar e remover sugestões; alterar relevância e observação; salvamento automático com debounce. | Edição salva sem clique explícito; indicador "salvo" aparece após debounce. | 20 |
| F6-FE-02 | Marcar bloco como revisado; filtro "pendentes de revisão" e contador `N/T` na página. | Filtro exibe apenas blocos não revisados; contador atualiza ao marcar. | 20 |
| F6-FE-03 | Atalhos de teclado completos (seção 20) + `ui-kbd` com legenda visível. | `J`/`K`, `T`, `R` e `←`/`→` funcionam; `ui-kbd` lista todos os atalhos. | 20 |
| F6-FE-04 | Tela **Exportação**: pré-visualização do JSON formatado, copiar, baixar, erros de validação apontando para o bloco. | Erro de validação destaca o bloco problemático na lista e na imagem. | 22 |
| F6-QA-01 | Teste E2E (Playwright): criar obra → pasta → upload → analisar → editar → reordenar → aprovar → exportar. | E2E verde no CI cobrindo o happy path completo. | 26 |
| F6-QA-02 | Checagem de todos os critérios da seção 26 e acessibilidade por teclado (fluxo completo sem mouse). | Checklist da seção 26 100% marcado; fluxo navegável só com teclado. | 26, 25 |

**Aceite da fase:** E2E verde; todos os critérios da seção 26 marcados; MVP entregue.  
**Dependências:** F5. **Riscos:** baixos.

---

### V2 — Escala e memória da obra

| ID | Descrição | Ref |
|---|---|---|
| V2-DB-01 | `glossary_entries` e `glossary_occurrences`; `folders.work_id` passa a ser obrigatório. | 14, 30.2 |
| V2-BE-01 | CRUD do glossário e busca "em quais páginas este termo aparece". | 30.2 |
| V2-AG-01 | Injeção das entradas relevantes do glossário no contexto da tradução. | 18, 30.2 |
| V2-AG-02 | Sugestão automática de entradas para o glossário (nomes recorrentes detectados). | 30.2 |
| V2-AG-03 | Estratégia `panel_aware` de ordenação (detecção de painéis completos). | 6.1 |
| V2-AG-04 | Melhoria automática do OCR: reprocessar recortes de baixa confiança com segundo motor. | 17.5 |
| V2-BE-02 | Processamento em lote do capítulo (fila com concorrência limitada e progresso agregado). | 28 |
| V2-BE-03 | Histórico e versionamento: comparar runs e restaurar versão anterior dos blocos. | 14 |
| V2-OPS-01 | Storage compatível com S3; autenticação (se Q3 confirmar multiusuário). | 25 |
| V2-FE-01 | Tela do glossário por obra; diff entre versões; progresso do lote; dashboard de custo por obra. | 17.8, 30.2 |

### V3 — Integrações

| ID | Descrição | Ref |
|---|---|---|
| V3-BE-01 | Exportadores para ferramentas de lettering (formato a definir), incluindo bbox quando necessário. | 3 |
| V3-BE-02 | Reaproveitamento do glossário entre obras (glossário global + herança). | 30.2 |
| V3-BE-03 | Webhooks e API pública para automações externas. | — |

---

## 29. Decisões importantes

- O banco é a fonte da verdade dos dados estruturados; o JSON é uma saída derivada.
- O original japonês nunca é substituído pela tradução.
- A ordenação é persistida, mas pode ser recalculada a partir das coordenadas.
- As sugestões são alternativas, não traduções simultâneas.
- A relevância é ordinal e serve para orientar a revisão.
- A revisão humana faz parte do fluxo normal, principalmente para OCR, nomes, onomatopeias e frases fragmentadas.
- **(Revisão)** O backend é Python + FastAPI; o frontend é Angular + Tailwind (paleta red).
- **(Revisão)** O contrato JSON tem uma única fonte, o modelo Pydantic, que gera o JSON Schema e os tipos TypeScript.
- **(Revisão)** Etapas determinísticas (ordenação, localização base, validação) não são delegadas ao LLM.

## 30. Memória contextual da obra *(AI-First)*

A memória da obra é o que transforma o sistema de um "tradutor de páginas" em um "agente de localização com contexto". Ela é dividida em duas camadas com entregas diferentes:

### 30.1 Camada MVP — Personagens *(promovida de V2)*

Personagens são a unidade de contexto mais importante para um mangá. O registro do MVP é intencionalmente simples:

| Campo | Descrição |
|---|---|
| `name_original` | Nome em japonês (ex.: `久田 咲子`) |
| `name_preferred` | Forma preferida em português (ex.: "Sakiko Hisada") |
| `gender` | `male`, `female`, `unknown` — influencia pronomes |
| `speech_register` | `formal`, `informal`, `childlike`, `rough`, `polite` — influencia o tom da tradução |
| `notes` | Campo livre: relação com outros personagens, apelidos, contexto |

O agente consulta os personagens registrados da obra antes de traduzir e recebe contexto explícito:

> "Nesta cena, o texto está associado a Sakiko (speech_register: childlike). Prefira um tom informal e ingênuo."

`character_mentions` associa o personagem a blocos específicos. A associação pode ser feita manualmente pelo revisor ou sugerida automaticamente pelo agente quando detectar um nome familiar.

### 30.2 Camada V2 — Glossário e relações

```
Obra
 ├── Personagens (MVP)
 │    ├── nome, pronomes, registro de fala
 │    └── menções por bloco
 │
 ├── Glossário (V2)
 │    ├── local       → forma preferida
 │    ├── termo       → tradução preferida
 │    └── onomatopeia → tradução preferida
 │
 ├── Relações entre personagens (V2)
 │    ├── A chama B de 先輩 → traduzir como "sênior" nesta obra
 │    └── C e D são rivais → tom pode ser tenso
 │
 ├── Histórico de correções humanas (V2)
 │    └── quando o revisor corrigiu X para Y, o motivo fica salvo
 │
 └── Pasta / Capítulo → Páginas → Blocos
```

Assim, se um termo aparecer em 30 páginas, o agente recebe:

> "Para esta obra, este nome já foi traduzido como X. Mantenha consistência."

**(Revisão R4)** Modelagem de `glossary_entries` e `glossary_occurrences` na seção 14; entrega do glossário na fase V2 (seção 28). Personagens (`characters`, `character_mentions`) entram no MVP.

## 31. Questões em aberto

| ID | Questão | Recomendação | Bloqueia |
|---|---|---|---|
| Q1 | Quais ferramentas de detecção, OCR e LLM usar (e como hospedar: local/GPU ou API)? | `comic-text-detector` + `manga-ocr` locais e um LLM multimodal via API para classificação e tradução. Fazer um *spike* comparativo de 2–3 dias no início da F3. | F3, F5 |
| Q2 | A ordem deve seguir literalmente "direita → esquerda, depois cima → baixo" ou a leitura por painéis? | **Evidência nas imagens de referência:** a regra literal falha em ambas. O MVP usa `tiered_column_rtl` + reordenação manual; `panel_aware` completo fica para a V2. Falta confirmar com o dono do produto. | F4 |
| Q8 | Um texto editorial horizontal (*yokogaki*, como no `banner_01`) deve seguir a regra direita → esquerda do PRD ou a leitura natural esquerda → direita? | Manter a regra do PRD no MVP (gabarito atual) e avaliar na V2 uma opção por faixa: "faixa horizontal → esquerda → direita". | F4 |
| Q9 | Os nomes próprios em hiragana (etiquetas da `pagina_01`) devem ser exportados na ordem japonesa (sobrenome, nome) ou na ocidental? | Ordem japonesa por padrão, configurável por obra no glossário (V2). | F5 |
| Q3 | O produto será monousuário local ou multiusuário/hospedado? | Monousuário no MVP; autenticação na V2 se houver necessidade. | V2 |
| Q4 | Quais metas de qualidade (recall de detecção, CER do OCR, acurácia de `#`/`$`) definem "pronto"? | Medir a linha de base na F3 e fixar as metas antes do fim da F4. | F4, F6 |
| Q5 | A paleta será **somente** red ou podem entrar `amber`/`emerald` nos estados semânticos (REVIEW/APPROVED)? | Permitir as duas exceções apenas para estado, sempre com ícone. | F0 |
| Q6 | O JSON de exportação deve permitir separar "fala" e "editorial" (seção 23)? | Não no MVP; avaliar na V2 como um campo opcional (`categoria`). | — |
| Q7 | O JSON deve incluir a sugestão "escolhida" pelo revisor, para uso futuro no lettering? | Adicionar um `selected` opcional em `translation_suggestions` na V2 sem alterar o contrato atual; decidir na V3. | V3 |

## 32. Nomenclatura

- Nome do projeto: **Manga Translator Agent**.
- Especificação oficial: `PRD_Agente_Traducao_Manga_Japones.md` (este arquivo, versionado no repositório).
- Origem: `PRD_Agente_Traducao_Manga_Japones.docx` (v1.0).
