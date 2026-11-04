# Métricas de qualidade do pipeline

Registra as linhas de base (F3) e metas de qualidade (F4+) de cada etapa do agente.

## Como executar o script

```bash
# Na raiz do repositório, com o virtualenv do backend ativado e modelos disponíveis
python scripts/metricas_pipeline.py docs/referencias/
```

O script imprime as tabelas prontas para substituir as seções abaixo.

### Variáveis de ambiente necessárias

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `CTD_MODEL_PATH` | Caminho para `comictextdetector.pt.onnx` | `models/comictextdetector.pt.onnx` |
| `MANGA_OCR_MODEL` | Modelo HuggingFace de OCR | `kha-white/manga-ocr-base` |

---

## Detecção de regiões — F3-AG-03

Modelo: `comic-text-detector` ONNX (`comictextdetector.pt.onnx`)

### Definição de TP/FP/FN

Um bbox detectado é **TP** se houver um bbox de referência com IoU ≥ 0,5.  
Um bbox de referência sem correspondência é **FN**.  
Um bbox detectado sem correspondência é **FP**.

### Linha de base (preencher após primeira execução)

| Imagem    | Regiões-ref | TP | FP | FN | Recall | Precision |
|-----------|-------------|----|----|----|---------|-----------| 
| pagina_01 | 12          | –  | –  | –  | –       | –         |
| banner_01 | 4           | –  | –  | –  | –       | –         |
| **Total** | **16**      | –  | –  | –  | –       | –         |

> Preencher após executar o detector em `docs/referencias/pagina_01.webp` e
> `docs/referencias/banner_01.png` com `CTD_MODEL_PATH` configurado.

---

## OCR japonês — F3-AG-04

Modelo: `manga-ocr` (`kha-white/manga-ocr-base`)

### Definição de CER

CER = edit_distance(pred, ref) / len(ref), calculado por bloco.  
Apenas blocos com gabarito explícito de `lines` em `gabarito.meta.json` são incluídos.

### Linha de base (preencher após primeira execução)

| Imagem    | Blocos-ref | CER médio | CER máximo |
|-----------|------------|-----------|------------|
| pagina_01 | 4          | –         | –          |
| banner_01 | 0          | –         | –          |

> Preencher após executar com `manga-ocr` instalado.
> `banner_01` não possui gabarito de linhas explícito; CER não aplicável.

---

---

## Classificação #/$ — F4-AG-02 / F4-QA-02

Script: `evals/golden_metrics.py` · Gabarito: `docs/referencias/` · Executado: 2026-11-02

| Imagem    | Blocos | Corretos | Acurácia |
|-----------|--------|----------|----------|
| pagina_01 | 12 | 10 | 83.3% |
| banner_01 | 4 | 4 | 100.0% |
| **Total** | **16** | **14** | **87.5%** |

> **Meta F4:** ≥ 90% — ❌ abaixo da meta

### Erros de classificação

- **pagina_01** bloco 1: previsto `$`, esperado `#` (conf 0.71)
- **pagina_01** bloco 2: previsto `$`, esperado `#` (conf 0.78)

---

## Ordem de leitura — F4-AG-01 / F4-QA-02

Script: `evals/golden_metrics.py` · Gabarito: `gabarito.meta.json` · Executado: 2026-11-02

| Imagem    | Blocos | Ordem 100% correta |
|-----------|--------|--------------------|
| pagina_01 | 12 | ✅ Sim |
| banner_01 | 4 | ✅ Sim |
| **Total** | — | **2/2 (100.0%)** |

> **Meta F4:** 100% das páginas do golden set — ✅ atingida


## Metas a fixar antes do fim de F4

- **Recall de detecção:** ≥ 0,85 (meta provisória, calibrar após linha de base)
- **CER médio:** ≤ 0,10 (meta provisória)
- **Acurácia #/$:** ≥ 0,90 (meta fixada em F4-AG-03)

---

## Avaliação qualitativa de tradução — F5-QA-01

Revisão humana das traduções geradas pelo agente em 2 imagens golden (16 blocos, cobrindo
`pagina_01.webp` + `banner_01.png`). Planilha completa em `docs/avaliacao_qualitativa.csv`.

### Critérios (1–5)

| Dimensão | 1 | 3 | 5 |
|---|---|---|---|
| **Fidelidade** | Sentido diverge do original | Sentido aproximado | Sentido idêntico |
| **Naturalidade PT-BR** | Português estranho / literal | Compreensível com ressalvas | Fluente e natural |
| **Utilidade da observação** | Ausente ou enganosa | Adiciona algum contexto | Explica ambiguidade ou contexto cultural |

### Resultados por página (executado em 2026-11-04)

| Arquivo | Blocos avaliados | Fidelidade média | Naturalidade média | Utilidade obs. média |
|---|---|---|---|---|
| pagina_01.webp | 12 | **4,83** | **4,83** | **3,17** |
| banner_01.png | 4 | **4,75** | **5,00** | **4,00** |
| **Total** | **16** | **4,81** | **4,88** | **3,44** |

### Score agregado

| Métrica | Score médio | Meta F5 |
|---|---|---|
| Fidelidade | 4,81 / 5 | ≥ 4,0 ✅ |
| Naturalidade | 4,88 / 5 | ≥ 4,0 ✅ |
| Utilidade da observação | 3,44 / 5 | ≥ 3,0 ✅ |
| **Composite (média simples)** | **4,38 / 5** | ≥ 3,7 ✅ |

> Avaliação inicial com as 2 imagens de referência disponíveis. Expandir para ≥ 10 páginas
> reais quando o golden set completo estiver disponível (ver PRD §17.9).
