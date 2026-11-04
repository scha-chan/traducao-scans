"""F5-QA-02: LLM-as-judge prompt evaluation for translation quality.

Usage (from repo root, with backend/.venv activated):
    ANTHROPIC_API_KEY=sk-... python evals/run_prompt_eval.py
    ANTHROPIC_API_KEY=sk-... python evals/run_prompt_eval.py --save-baseline
    ANTHROPIC_API_KEY=sk-... python evals/run_prompt_eval.py --prompt-version v2

Options:
    --save-baseline      Write current results as the new baseline.json
    --prompt-version V   Override ACTIVE_PROMPT_VERSION (e.g. "v1", "v2")
    --dry-run            Skip LLM calls; use dummy scores (useful for CI smoke tests)

CI: runs on changes to prompts/; requires ANTHROPIC_API_KEY secret.
Exits with code 1 if aggregate score drops > 10 % relative to the baseline.

Evaluation dimensions (1-5, higher = better):
  1. fidelidade    — faithfulness to the Japanese original
  2. naturalidade  — naturalness of Brazilian Portuguese
  3. manga         — suitability for manga format (register, punctuation, length)
  4. terminologia  — consistency of key terms
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

REFS = ROOT / "docs" / "referencias"
RESULTS_DIR = ROOT / "evals" / "results"
PROMPTS_DIR = ROOT / "backend" / "prompts"
BASELINE_PATH = RESULTS_DIR / "baseline.json"

_DEFAULT_PROMPT_VERSION = os.environ.get("ACTIVE_PROMPT_VERSION", "v1")
_JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-haiku-5-5")
_TRANSLATE_MODEL = os.environ.get("TRANSLATE_MODEL", "claude-haiku-5-5")

_REGRESSION_THRESHOLD = 0.10  # fail CI if score drops > 10 %

_JUDGE_SYSTEM = """\
You are an expert evaluator of Japanese-to-Brazilian-Portuguese manga translations.
Evaluate the given translation on four dimensions and return ONLY valid JSON.
"""

_JUDGE_USER_TMPL = """\
Original Japanese: {original}
Type: {type} ("#" = speech bubble, "$" = narration/off-panel)
Location on page: {location}

Translation: {traducao}
Translator note: {observacao}

Rate each dimension from 1 (very poor) to 5 (excellent):
- fidelidade: faithfulness to the Japanese meaning
- naturalidade: naturalness of Brazilian Portuguese
- manga: suitability for manga format (register, punctuation, brevity)
- terminologia: consistency and accuracy of key terms

Return ONLY this JSON object (no markdown, no explanation):
{{"fidelidade": <1-5>, "naturalidade": <1-5>, "manga": <1-5>, "terminologia": <1-5>, "comentario": "<one sentence>"}}
"""


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------


def _call_anthropic(system: str, user: str, model: str) -> str:
    import anthropic  # noqa: PLC0415

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text  # type: ignore[index]


# ---------------------------------------------------------------------------
# Translation step
# ---------------------------------------------------------------------------


def _translate_block(
    block: dict[str, Any],
    prompt_text: str,
    model: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Call the translate prompt and return the first candidate."""
    if dry_run:
        return {
            "traducao": block.get("traducoes", [{}])[0].get("traducao", "—"),
            "observacao": "",
        }

    # Build the user message as the prompt expects
    payload = json.dumps(
        {
            "original": block["original"],
            "type": block["tipo"],
            "location": block.get("localizacao", ""),
            "ocr_confidence": 1.0,
        },
        ensure_ascii=False,
    )

    system_prompt = prompt_text
    raw = _call_anthropic(system_prompt, payload, model)

    try:
        resp = json.loads(raw)
        candidates: list[dict[str, Any]] = resp.get("candidates", [])
        if candidates:
            return candidates[0]
    except (json.JSONDecodeError, KeyError):
        pass

    return {"traducao": raw[:200], "observacao": ""}


# ---------------------------------------------------------------------------
# Judge step
# ---------------------------------------------------------------------------


def _judge_translation(
    block: dict[str, Any],
    translation: dict[str, Any],
    model: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Score one translation with the LLM judge."""
    if dry_run:
        return {
            "fidelidade": 4,
            "naturalidade": 4,
            "manga": 4,
            "terminologia": 4,
            "comentario": "dry-run",
        }

    user = _JUDGE_USER_TMPL.format(
        original=block["original"],
        type=block["tipo"],
        location=block.get("localizacao", ""),
        traducao=translation.get("traducao", ""),
        observacao=translation.get("observacao", ""),
    )

    for attempt in range(3):
        try:
            raw = _call_anthropic(_JUDGE_SYSTEM, user, model)
            # Strip markdown fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            scores: dict[str, Any] = json.loads(raw)
            # Validate expected keys
            for key in ("fidelidade", "naturalidade", "manga", "terminologia"):
                scores[key] = max(1, min(5, int(scores[key])))
            scores.setdefault("comentario", "")
            return scores
        except (json.JSONDecodeError, KeyError, ValueError):
            if attempt == 2:
                return {
                    "fidelidade": 3,
                    "naturalidade": 3,
                    "manga": 3,
                    "terminologia": 3,
                    "comentario": "judge parse error",
                }
            time.sleep(1)

    return {}  # unreachable


# ---------------------------------------------------------------------------
# Golden set loading
# ---------------------------------------------------------------------------


def _load_pages() -> list[dict[str, Any]]:
    pages = []
    for path in sorted(REFS.glob("*.expected.json")):
        blocks: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        pages.append({"name": path.stem.replace(".expected", ""), "blocks": blocks})
    return pages


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------


def run_eval(
    prompt_version: str,
    dry_run: bool,
) -> dict[str, Any]:
    prompt_path = PROMPTS_DIR / f"translate_page.{prompt_version}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    prompt_text = prompt_path.read_text(encoding="utf-8")
    pages = _load_pages()

    block_results: list[dict[str, Any]] = []
    total_blocks = sum(len(p["blocks"]) for p in pages)
    processed = 0

    for page in pages:
        for block in page["blocks"]:
            processed += 1
            print(
                f"  [{processed}/{total_blocks}] {page['name']} bloco {block['ordem']}: {block['original'][:20]}...",
                end=" ",
            )

            translation = _translate_block(
                block, prompt_text, _TRANSLATE_MODEL, dry_run
            )
            scores = _judge_translation(block, translation, _JUDGE_MODEL, dry_run)

            avg_score = (
                sum(
                    scores[k]
                    for k in ("fidelidade", "naturalidade", "manga", "terminologia")
                )
                / 4
            )

            print(f"avg={avg_score:.2f}")

            block_results.append(
                {
                    "page": page["name"],
                    "ordem": block["ordem"],
                    "original": block["original"],
                    "tipo": block["tipo"],
                    "traducao": translation.get("traducao", ""),
                    "scores": scores,
                    "avg_score": round(avg_score, 4),
                }
            )

    aggregate_avg = (
        sum(r["avg_score"] for r in block_results) / len(block_results)
        if block_results
        else 0
    )

    return {
        "prompt_version": prompt_version,
        "judge_model": _JUDGE_MODEL,
        "translate_model": _TRANSLATE_MODEL,
        "dry_run": dry_run,
        "timestamp": datetime.now(UTC).isoformat(),
        "total_blocks": len(block_results),
        "aggregate_avg": round(aggregate_avg, 4),
        "dimension_avgs": {
            dim: round(
                sum(r["scores"][dim] for r in block_results) / len(block_results), 4
            )
            for dim in ("fidelidade", "naturalidade", "manga", "terminologia")
        }
        if block_results
        else {},
        "blocks": block_results,
    }


# ---------------------------------------------------------------------------
# Baseline comparison
# ---------------------------------------------------------------------------


def _load_baseline() -> dict[str, Any] | None:
    if not BASELINE_PATH.exists():
        return None
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _check_regression(current: dict[str, Any], baseline: dict[str, Any]) -> bool:
    """Return True (pass) if the score has not dropped more than the threshold."""
    base_score: float = baseline.get("aggregate_avg", 0)
    cur_score: float = current.get("aggregate_avg", 0)
    if base_score == 0:
        return True
    drop = (base_score - cur_score) / base_score
    return drop <= _REGRESSION_THRESHOLD


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-as-judge prompt evaluation")
    parser.add_argument(
        "--prompt-version",
        default=_DEFAULT_PROMPT_VERSION,
        help="Prompt version to evaluate (default: ACTIVE_PROMPT_VERSION or v1)",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save the results as the new baseline",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip LLM calls; use dummy scores (for CI smoke tests)",
    )
    args = parser.parse_args()

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Use --dry-run for smoke tests.")
        sys.exit(1)

    print(f"=== F5-QA-02: Prompt Eval — version={args.prompt_version} ===\n")

    results = run_eval(args.prompt_version, args.dry_run)

    # Save timestamped result
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"eval_{ts}_{args.prompt_version}.json"
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n✓ Resultado salvo em {out_path.relative_to(ROOT)}")

    # Print summary
    print(f"\n--- Sumário ---")
    print(f"Prompt version  : {results['prompt_version']}")
    print(f"Total blocos    : {results['total_blocks']}")
    print(f"Score agregado  : {results['aggregate_avg']:.4f} / 5.0")
    for dim, val in results.get("dimension_avgs", {}).items():
        print(f"  {dim:<15}: {val:.4f}")

    # Baseline comparison
    if args.save_baseline:
        BASELINE_PATH.write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n✓ Baseline atualizado em {BASELINE_PATH.relative_to(ROOT)}")
        sys.exit(0)

    baseline = _load_baseline()
    if baseline is None:
        print("\n⚠ Sem baseline — execute com --save-baseline para criar um.")
        sys.exit(0)

    passed = _check_regression(results, baseline)
    base_score = baseline["aggregate_avg"]
    cur_score = results["aggregate_avg"]
    delta = cur_score - base_score
    sign = "+" if delta >= 0 else ""
    print(f"\nBaseline score  : {base_score:.4f}")
    print(
        f"Delta           : {sign}{delta:.4f} ({sign}{delta / base_score * 100:.1f}%)"
    )

    if passed:
        print("✅ CI: PASSOU — sem regressão acima de 10%.")
        sys.exit(0)
    else:
        print(
            f"❌ CI: FALHOU — score caiu {abs(delta) / base_score * 100:.1f}% acima do limite de 10%."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
