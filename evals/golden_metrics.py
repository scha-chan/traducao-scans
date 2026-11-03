"""F4-QA-02: #/$ accuracy and reading-order accuracy on the golden set.

Usage (from repo root, with backend/.venv activated):
    python evals/golden_metrics.py

Outputs metrics to stdout; writes the F4 section of docs/metricas.md.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from PIL import Image  # noqa: E402 — after sys.path update

from agent.providers.classification import HeuristicClassificationProvider  # noqa: E402
from agent.stages.reading_order import TieredColumnRtlStrategy  # noqa: E402
from agent.state import BBox, DialogueState  # noqa: E402

REFS = ROOT / "docs" / "referencias"
META: dict = json.loads((REFS / "gabarito.meta.json").read_text(encoding="utf-8"))

PAGES = [
    {
        "name": "pagina_01",
        "image": REFS / "pagina_01.webp",
        "expected": json.loads(
            (REFS / "pagina_01.expected.json").read_text(encoding="utf-8")
        ),
        "meta": META["pagina_01"],
    },
    {
        "name": "banner_01",
        "image": REFS / "banner_01.png",
        "expected": json.loads(
            (REFS / "banner_01.expected.json").read_text(encoding="utf-8")
        ),
        "meta": META["banner_01"],
    },
]


# ---------------------------------------------------------------------------
# Classification (#/$)
# ---------------------------------------------------------------------------


def _run_classification(page: dict) -> dict:
    provider = HeuristicClassificationProvider()
    img = Image.open(page["image"]).convert("RGB")
    meta_blocos: list[dict] = page["meta"]["blocos"]
    expected_by_ordem = {e["ordem"]: e["tipo"] for e in page["expected"]}

    results = []
    for b in meta_blocos:
        bd = b["bbox"]
        bbox = BBox(x=bd["x"], y=bd["y"], width=bd["width"], height=bd["height"])
        pred = provider.classify(img, bbox)
        exp_tipo = expected_by_ordem.get(b["ordem"], "?")
        results.append(
            {
                "ordem": b["ordem"],
                "predicted": pred.type,
                "expected": exp_tipo,
                "confidence": pred.confidence,
                "ok": pred.type == exp_tipo,
            }
        )

    correct = sum(1 for r in results if r["ok"])
    return {"correct": correct, "total": len(results), "results": results}


# ---------------------------------------------------------------------------
# Reading order
# ---------------------------------------------------------------------------


def _run_order(page: dict) -> dict:
    meta = page["meta"]
    blocos: list[dict] = meta["blocos"]
    divisas: list[int] = meta.get("divisas_painel_y", [])
    w: int = meta["dimensoes"]["width"]
    h: int = meta["dimensoes"]["height"]

    dialogues = [
        DialogueState(
            id=str(b["ordem"]),  # id == expected order
            bbox=BBox(
                x=b["bbox"]["x"],
                y=b["bbox"]["y"],
                width=b["bbox"]["width"],
                height=b["bbox"]["height"],
            ),
        )
        for b in blocos
    ]

    strategy = TieredColumnRtlStrategy()
    ordered = strategy.order(
        dialogues, page_width=w, page_height=h, panel_divisa_ys=divisas
    )

    mismatches = [
        {"expected": int(d.id), "predicted": d.order}
        for d in ordered
        if d.order != int(d.id)
    ]
    return {
        "correct": len(mismatches) == 0,
        "mismatches": mismatches,
        "total": len(ordered),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _print_classification(results: dict[str, dict]) -> None:
    print("\n### Classificação #/$ — resultados por bloco\n")
    total_c = total_t = 0
    for name, r in results.items():
        print(f"**{name}** — {r['correct']}/{r['total']}")
        wrong = [x for x in r["results"] if not x["ok"]]
        if wrong:
            for x in wrong:
                print(
                    f"  ✗ bloco {x['ordem']}: previsto={x['predicted']!r} esperado={x['expected']!r} conf={x['confidence']:.2f}"
                )
        else:
            print("  ✓ todos corretos")
        total_c += r["correct"]
        total_t += r["total"]
    acc = total_c / total_t if total_t else 0
    print(f"\n**Acurácia total: {total_c}/{total_t} = {acc:.1%}**")


def _print_order(results: dict[str, dict]) -> None:
    print("\n### Ordem de leitura — resultados\n")
    pages_correct = sum(1 for r in results.values() if r["correct"])
    pages_total = len(results)
    for name, r in results.items():
        status = (
            "✓ 100% correto" if r["correct"] else f"✗ {len(r['mismatches'])} erro(s)"
        )
        print(f"**{name}** — {status}")
        for m in r["mismatches"]:
            print(f"  bloco esperado={m['expected']} → previsto={m['predicted']}")
    pct = pages_correct / pages_total if pages_total else 0
    print(f"\n**Páginas 100% corretas: {pages_correct}/{pages_total} = {pct:.1%}**")


def _build_metricas_section(
    cls_results: dict[str, dict], ord_results: dict[str, dict]
) -> str:
    today = date.today().isoformat()

    total_c = sum(r["correct"] for r in cls_results.values())
    total_t = sum(r["total"] for r in cls_results.values())
    cls_acc = total_c / total_t if total_t else 0

    pages_correct = sum(1 for r in ord_results.values() if r["correct"])
    pages_total = len(ord_results)
    ord_pct = pages_correct / pages_total if pages_total else 0

    lines = [
        "---",
        "",
        "## Classificação #/$ — F4-AG-02 / F4-QA-02",
        "",
        f"Script: `evals/golden_metrics.py` · Gabarito: `docs/referencias/` · Executado: {today}",
        "",
        "| Imagem    | Blocos | Corretos | Acurácia |",
        "|-----------|--------|----------|----------|",
    ]
    for name, r in cls_results.items():
        acc = r["correct"] / r["total"] if r["total"] else 0
        lines.append(f"| {name} | {r['total']} | {r['correct']} | {acc:.1%} |")
    lines += [
        f"| **Total** | **{total_t}** | **{total_c}** | **{cls_acc:.1%}** |",
        "",
        f"> **Meta F4:** ≥ 90% — {'✅ atingida' if cls_acc >= 0.9 else '❌ abaixo da meta'}",
        "",
        "### Erros de classificação",
        "",
    ]
    any_error = False
    for name, r in cls_results.items():
        wrong = [x for x in r["results"] if not x["ok"]]
        if wrong:
            any_error = True
            for x in wrong:
                lines.append(
                    f"- **{name}** bloco {x['ordem']}: "
                    f"previsto `{x['predicted']}`, esperado `{x['expected']}` "
                    f"(conf {x['confidence']:.2f})"
                )
    if not any_error:
        lines.append("_Nenhum erro._")

    lines += [
        "",
        "---",
        "",
        "## Ordem de leitura — F4-AG-01 / F4-QA-02",
        "",
        f"Script: `evals/golden_metrics.py` · Gabarito: `gabarito.meta.json` · Executado: {today}",
        "",
        "| Imagem    | Blocos | Ordem 100% correta |",
        "|-----------|--------|--------------------|",
    ]
    for name, r in ord_results.items():
        ok = "✅ Sim" if r["correct"] else f"❌ Não ({len(r['mismatches'])} erro(s))"
        lines.append(f"| {name} | {r['total']} | {ok} |")
    lines += [
        f"| **Total** | — | **{pages_correct}/{pages_total} ({ord_pct:.1%})** |",
        "",
        f"> **Meta F4:** 100% das páginas do golden set — {'✅ atingida' if ord_pct == 1.0 else '❌ abaixo da meta'}",
        "",
    ]
    return "\n".join(lines)


def _update_metricas_md(section: str) -> None:
    path = ROOT / "docs" / "metricas.md"
    content = path.read_text(encoding="utf-8")

    marker_start = "## Classificação #/$ — F4-AG-02 / F4-QA-02"
    marker_end = "## Metas a fixar antes do fim de F4"

    if marker_start in content:
        # Replace existing F4 section
        idx_start = content.index("---\n\n" + marker_start)
        if marker_end in content:
            idx_end = content.index("\n" + marker_end)
            content = content[:idx_start] + section + "\n" + content[idx_end:]
        else:
            content = content[:idx_start] + section + "\n"
    else:
        # Append before the "Metas" section if it exists, else append at end
        if marker_end in content:
            idx = content.index("\n" + marker_end)
            content = content[:idx] + "\n" + section + "\n" + content[idx:]
        else:
            content = content.rstrip() + "\n\n" + section + "\n"

    path.write_text(content, encoding="utf-8")
    print("\n✓ docs/metricas.md atualizado.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("=== F4-QA-02: Golden Set Metrics ===")

    cls_results: dict[str, dict] = {}
    ord_results: dict[str, dict] = {}

    for page in PAGES:
        print(f"\n--- {page['name']} ---")
        cls_results[page["name"]] = _run_classification(page)
        ord_results[page["name"]] = _run_order(page)

    _print_classification(cls_results)
    _print_order(ord_results)

    section = _build_metricas_section(cls_results, ord_results)
    _update_metricas_md(section)


if __name__ == "__main__":
    main()
