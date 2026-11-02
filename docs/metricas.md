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

## Metas a fixar antes do fim de F4

- **Recall de detecção:** ≥ 0,85 (meta provisória, calibrar após linha de base)
- **CER médio:** ≤ 0,10 (meta provisória)
- **Acurácia #/$:** ≥ 0,90 (meta fixada em F4-AG-03)
