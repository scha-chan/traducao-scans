#!/usr/bin/env python3
"""Script de métricas do pipeline — F3-QA-01.

Uso:
    python scripts/metricas_pipeline.py docs/referencias/

Métricas calculadas:
  - Recall e Precision de detecção de regiões (IoU ≥ 0,5)
  - CER médio e máximo de OCR (blocos com gabarito de linhas)

Requisitos de ambiente:
  - CTD_MODEL_PATH: caminho para comictextdetector.pt.onnx
  - MANGA_OCR_MODEL: modelo HuggingFace (default: kha-white/manga-ocr-base)
  - Dependências: onnxruntime, opencv-python-headless, manga-ocr, Pillow

Quando os modelos não estiverem disponíveis o script imprime avisos e
pula as etapas correspondentes sem falhar.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

# Adiciona backend/ ao path para importar os módulos do agente
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))


# ---------------------------------------------------------------------------
# Tipos de dados
# ---------------------------------------------------------------------------


class _BBox(NamedTuple):
    x: int
    y: int
    width: int
    height: int


# ---------------------------------------------------------------------------
# Funções de métricas
# ---------------------------------------------------------------------------


def _iou(a: _BBox, b: _BBox) -> float:
    """Intersection over Union entre dois bboxes."""
    ix1 = max(a.x, b.x)
    iy1 = max(a.y, b.y)
    ix2 = min(a.x + a.width, b.x + b.width)
    iy2 = min(a.y + a.height, b.y + b.height)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    inter = (ix2 - ix1) * (iy2 - iy1)
    union = a.width * a.height + b.width * b.height - inter
    return inter / union if union > 0 else 0.0


def _edit_distance(s: str, t: str) -> int:
    """Distância de Levenshtein entre duas strings."""
    m, n = len(s), len(t)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if s[i - 1] == t[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _cer(pred: str, ref: str) -> float:
    """Character Error Rate: edit_distance / len(ref)."""
    return 0.0 if not ref else _edit_distance(pred, ref) / len(ref)


def compute_detection_metrics(
    ref_bboxes: list[_BBox],
    pred_bboxes: list[_BBox],
    iou_threshold: float = 0.5,
) -> dict[str, int | float]:
    """Calcula TP, FP, FN, recall e precision via greedy matching."""
    matched_ref = [False] * len(ref_bboxes)
    tp = fp = 0

    for pred in pred_bboxes:
        best_iou = 0.0
        best_idx = -1
        for i, ref in enumerate(ref_bboxes):
            if matched_ref[i]:
                continue
            v = _iou(pred, ref)
            if v > best_iou:
                best_iou = v
                best_idx = i

        if best_iou >= iou_threshold and best_idx >= 0:
            tp += 1
            matched_ref[best_idx] = True
        else:
            fp += 1

    fn = matched_ref.count(False)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "recall": round(recall, 3),
        "precision": round(precision, 3),
    }


# ---------------------------------------------------------------------------
# Acesso aos modelos (falha silenciosa quando indisponíveis)
# ---------------------------------------------------------------------------


def _try_detection(image_path: str) -> list[_BBox] | None:
    """Executa o detector CTD. Retorna None se o modelo não estiver disponível."""
    import os  # noqa: PLC0415

    try:
        from agent.providers.detection import ComicTextDetectorProvider  # noqa: PLC0415

        model_path = os.environ.get(
            "CTD_MODEL_PATH", "models/comictextdetector.pt.onnx"
        )
        provider = ComicTextDetectorProvider(model_path=model_path)
        bboxes = provider.detect(image_path)
        return [_BBox(b.x, b.y, b.width, b.height) for b in bboxes]
    except Exception as exc:  # noqa: BLE001
        print(f"    [aviso] detector indisponível: {exc}", file=sys.stderr)
        return None


def _try_ocr(
    image_path: str, blocks_with_lines: list[dict]
) -> list[tuple[str, str]] | None:
    """Executa OCR nos blocos com gabarito de lines.

    Retorna lista de (texto_predito, texto_referencia) ou None se indisponível.
    Inicializa o modelo uma única vez para todos os blocos.
    """
    if not blocks_with_lines:
        return []

    try:
        from PIL import Image  # noqa: PLC0415

        from agent.providers.ocr import MangaOcrProvider  # noqa: PLC0415
        from agent.state import BBox  # noqa: PLC0415

        provider = MangaOcrProvider()
        img = Image.open(image_path).convert("RGB")
        pairs: list[tuple[str, str]] = []

        for block in blocks_with_lines:
            b = block["bbox"]
            bbox = BBox(x=b["x"], y=b["y"], width=b["width"], height=b["height"])
            region = img.crop(
                (bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height)
            )
            result = provider.ocr_region(region, bbox)
            ref_text = "".join(block["lines"])
            pairs.append((result.original, ref_text))

        return pairs

    except Exception as exc:  # noqa: BLE001
        print(f"    [aviso] OCR indisponível: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Processamento por imagem
# ---------------------------------------------------------------------------


def process_image(
    image_path: str,
    meta: dict,
) -> dict:
    """Executa as etapas de detecção e OCR e retorna as métricas brutas."""
    ref_bboxes = [
        _BBox(
            x=b["bbox"]["x"],
            y=b["bbox"]["y"],
            width=b["bbox"]["width"],
            height=b["bbox"]["height"],
        )
        for b in meta["blocos"]
    ]

    # Detecção
    pred_bboxes = _try_detection(image_path)
    det_metrics = (
        compute_detection_metrics(ref_bboxes, pred_bboxes)
        if pred_bboxes is not None
        else None
    )

    # OCR — apenas blocos que possuem gabarito de linhas
    blocks_with_lines = [b for b in meta["blocos"] if b.get("lines")]
    ocr_pairs = _try_ocr(image_path, blocks_with_lines)
    if ocr_pairs is not None and ocr_pairs:
        cer_values = [_cer(pred, ref) for pred, ref in ocr_pairs]
        ocr_metrics: dict | None = {
            "blocks_tested": len(cer_values),
            "cer_mean": round(sum(cer_values) / len(cer_values), 3),
            "cer_max": round(max(cer_values), 3),
        }
    else:
        ocr_metrics = None

    return {
        "ref_count": len(ref_bboxes),
        "pred_count": len(pred_bboxes) if pred_bboxes is not None else None,
        "detection": det_metrics,
        "ocr": ocr_metrics,
    }


# ---------------------------------------------------------------------------
# Relatório em Markdown
# ---------------------------------------------------------------------------


def _print_detection_table(rows: list[dict]) -> None:
    print("\n## Detecção de regiões — linha de base\n")
    print("| Imagem | Regiões-ref | TP | FP | FN | Recall | Precision |")
    print("|--------|-------------|----|----|----|---------|-----------| ")
    tot_ref = tot_tp = tot_fp = tot_fn = 0
    for r in rows:
        d = r["detection"]
        print(
            f"| {r['imagem']} | {r['ref_count']} | {d['tp']} | {d['fp']} | {d['fn']}"
            f" | {d['recall']:.3f} | {d['precision']:.3f} |"
        )
        tot_ref += r["ref_count"]
        tot_tp += d["tp"]
        tot_fp += d["fp"]
        tot_fn += d["fn"]
    rec = tot_tp / (tot_tp + tot_fn) if (tot_tp + tot_fn) > 0 else 0.0
    pre = tot_tp / (tot_tp + tot_fp) if (tot_tp + tot_fp) > 0 else 0.0
    print(
        f"| **Total** | **{tot_ref}** | **{tot_tp}** | **{tot_fp}** | **{tot_fn}**"
        f" | **{rec:.3f}** | **{pre:.3f}** |"
    )


def _print_ocr_table(rows: list[dict]) -> None:
    print("\n## OCR japonês — linha de base\n")
    print("| Imagem | Blocos-ref | CER médio | CER máximo |")
    print("|--------|------------|-----------|------------|")
    total_blocks = total_cer_weighted = 0.0
    max_cer = 0.0
    for r in rows:
        o = r["ocr"]
        print(
            f"| {r['imagem']} | {o['blocks_tested']} | {o['cer_mean']:.3f} | {o['cer_max']:.3f} |"
        )
        total_blocks += o["blocks_tested"]
        total_cer_weighted += o["cer_mean"] * o["blocks_tested"]
        max_cer = max(max_cer, o["cer_max"])
    if total_blocks > 0:
        overall = total_cer_weighted / total_blocks
        print(
            f"| **Total** | **{int(total_blocks)}** | **{overall:.3f}** | **{max_cer:.3f}** |"
        )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calcula métricas de detecção (recall/precision) e OCR (CER) "
        "em relação ao gabarito de referência."
    )
    parser.add_argument(
        "referencias_dir",
        help="Diretório contendo as imagens e gabarito.meta.json (ex.: docs/referencias/)",
    )
    args = parser.parse_args()

    refs_dir = Path(args.referencias_dir)
    meta_path = refs_dir / "gabarito.meta.json"

    if not meta_path.exists():
        print(f"Erro: {meta_path} não encontrado.", file=sys.stderr)
        sys.exit(1)

    with meta_path.open(encoding="utf-8") as f:
        meta_all: dict = json.load(f)

    gabaritos = {k: v for k, v in meta_all.items() if not k.startswith("_")}

    det_rows: list[dict] = []
    ocr_rows: list[dict] = []

    for name, meta in gabaritos.items():
        arquivo = meta.get("arquivo", name)
        image_path = str(refs_dir / arquivo)
        if not Path(image_path).exists():
            print(f"[aviso] imagem não encontrada: {image_path}", file=sys.stderr)
            continue

        print(
            f"→ {arquivo} ({meta['dimensoes']['width']}×{meta['dimensoes']['height']})"
        )
        result = process_image(image_path, meta)

        if result["detection"]:
            d = result["detection"]
            det_rows.append(
                {"imagem": name, "ref_count": result["ref_count"], "detection": d}
            )
            print(
                f"  detecção: TP={d['tp']} FP={d['fp']} FN={d['fn']}"
                f" recall={d['recall']:.3f} precision={d['precision']:.3f}"
            )
        else:
            print("  detecção: modelo não disponível (CTD_MODEL_PATH)")

        if result["ocr"]:
            o = result["ocr"]
            ocr_rows.append({"imagem": name, "ocr": o})
            print(
                f"  ocr: {o['blocks_tested']} blocos"
                f" CER_médio={o['cer_mean']:.3f} CER_máx={o['cer_max']:.3f}"
            )
        else:
            print("  ocr: modelo não disponível (manga-ocr)")

    if det_rows:
        _print_detection_table(det_rows)
    else:
        print(
            "\n[sem dados de detecção — configure CTD_MODEL_PATH e execute novamente]",
            file=sys.stderr,
        )

    if ocr_rows:
        _print_ocr_table(ocr_rows)
    else:
        print(
            "\n[sem dados de OCR — instale manga-ocr e execute novamente]",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
