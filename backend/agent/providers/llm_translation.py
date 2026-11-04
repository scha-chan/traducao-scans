"""ClaudeTranslationProvider — LLM-backed JA→PT translation (F5-AG-03)."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from agent.cache import TranslationCache, dialogue_cache_key
from agent.state import (
    AgentLogEntry,
    DialogueState,
    PageAnalysisState,
    ProviderSpan,
    TranslationCandidate,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-haiku-5-5"
_DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


# ---------------------------------------------------------------------------
# Pydantic models for LLM structured output
# ---------------------------------------------------------------------------


class LLMCandidate(BaseModel):
    traducao: str
    observacao: str = ""
    relevancia: int = Field(ge=1, le=5)


class LLMTranslationResponse(BaseModel):
    candidates: list[LLMCandidate] = Field(min_length=1, max_length=5)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class LLMTranslationProvider(Protocol):
    def translate_dialogue(
        self,
        dialogue: DialogueState,
        prompt_version: str,
        state: PageAnalysisState | None = None,
    ) -> list[TranslationCandidate]: ...


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class ClaudeTranslationProvider:
    """Translate manga dialogue via the Claude API with Pydantic-validated output.

    Reads the versioned system prompt from *prompts_dir*/<prompt_version>.txt.
    Retries up to *max_retries* times when the model returns malformed JSON.
    If a transient API error occurs (5xx or timeout), falls back to *fallback_model*
    when configured, recording ``fallback_used=True`` in the provider span.
    """

    def __init__(
        self,
        api_key: str | None = None,
        primary_model: str | None = None,
        fallback_model: str | None = None,
        prompts_dir: str | Path | None = None,
        max_retries: int = 2,
        cache: TranslationCache | None = None,
        # Legacy alias kept for backward compatibility
        model: str | None = None,
    ) -> None:
        resolved_key: str = api_key or os.environ.get("ANTHROPIC_API_KEY") or ""
        if not resolved_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set the ANTHROPIC_API_KEY environment variable or pass api_key=."
            )
        self._api_key = resolved_key
        # `primary_model` takes precedence; `model` is the legacy kwarg
        effective_primary = primary_model or model
        self._model: str = (
            effective_primary or os.environ.get("ANTHROPIC_TRANSLATION_MODEL") or _DEFAULT_MODEL
        )
        self._fallback_model: str | None = fallback_model
        self._prompts_dir = Path(prompts_dir) if prompts_dir is not None else _DEFAULT_PROMPTS_DIR
        self._max_retries = max_retries
        self._cache = cache

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_system_prompt(self, prompt_version: str) -> str:
        prompt_path = self._prompts_dir / f"translate_page.{prompt_version}.txt"
        if not prompt_path.exists():
            logger.warning("Prompt version %s not found, falling back to v1", prompt_version)
            prompt_path = self._prompts_dir / "translate_page.v1.txt"
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_message(self, dialogue: DialogueState) -> str:
        payload: dict[str, Any] = {  # noqa: ANN401
            "original": dialogue.original or "",
            "type": dialogue.type,
            "location": dialogue.location,
            "ocr_confidence": dialogue.ocr_confidence,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _parse_response(self, text: str) -> LLMTranslationResponse:
        return LLMTranslationResponse.model_validate_json(text)

    def _call_api(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> tuple[str, int, int]:
        """Call the Anthropic API and return (response_text, input_tokens, output_tokens)."""
        import anthropic  # noqa: PLC0415

        effective_model = model or self._model
        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=effective_model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,  # type: ignore[arg-type]
        )
        text: str = ""
        if response.content:
            block = response.content[0]
            if hasattr(block, "text"):
                text = str(block.text)
        input_tokens: int = response.usage.input_tokens if response.usage else 0
        output_tokens: int = response.usage.output_tokens if response.usage else 0
        return text, input_tokens, output_tokens

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def translate_dialogue(
        self,
        dialogue: DialogueState,
        prompt_version: str,
        state: PageAnalysisState | None = None,
    ) -> list[TranslationCandidate]:
        effective_version = state.prompt_version if state is not None else prompt_version
        cache_key = dialogue_cache_key(dialogue, effective_version)

        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                if state is not None:
                    state.agent_log.append(
                        AgentLogEntry(
                            timestamp=datetime.now(UTC),
                            stage="translation",
                            trigger="cache",
                            action="cache_hit",
                            detail={"cache_hit": True, "dialogue_id": dialogue.id},
                        )
                    )
                logger.debug(
                    "cache_hit dialogue=%s prompt_version=%s", dialogue.id, effective_version
                )
                return cached

        system_prompt = self._load_system_prompt(effective_version)
        user_message = self._build_user_message(dialogue)
        t0 = time.monotonic()

        import anthropic as _anthropic  # noqa: PLC0415

        total_input = 0
        total_output = 0
        fallback_used: bool = False
        active_model: str = self._model

        def _attempt(model: str) -> list[TranslationCandidate] | None:
            """Run the JSON-retry loop for *model*. Returns candidates or None on parse failure."""
            nonlocal total_input, total_output
            messages: list[dict[str, str]] = [{"role": "user", "content": user_message}]
            last_error: str = ""
            response_text: str = ""
            for attempt in range(self._max_retries + 1):
                response_text, in_tok, out_tok = self._call_api(
                    system_prompt, messages, model=model
                )
                total_input += in_tok
                total_output += out_tok
                try:
                    parsed = self._parse_response(response_text)
                    return [
                        TranslationCandidate(
                            translation=c.traducao,
                            observation=c.observacao,
                            relevance=c.relevancia,
                        )
                        for c in parsed.candidates
                    ]
                except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                    last_error = str(exc)
                    logger.warning(
                        "llm_translation attempt=%d/%d failed dialogue=%s: %s",
                        attempt + 1,
                        self._max_retries + 1,
                        dialogue.id,
                        last_error,
                    )
                    if attempt < self._max_retries:
                        messages.append({"role": "assistant", "content": response_text})
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"Your previous response was not valid JSON or did not match "
                                    f"the required schema. Error: {last_error}\n"
                                    "Please respond again with ONLY the JSON object as specified."
                                ),
                            }
                        )
            return None  # all parse attempts exhausted

        try:
            candidates = _attempt(active_model)
        except (_anthropic.APIStatusError, _anthropic.APITimeoutError) as exc:
            if self._fallback_model is None:
                self._record_span(
                    dialogue=dialogue,
                    state=state,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    latency_ms=int((time.monotonic() - t0) * 1000),
                    success=False,
                    fallback_used=False,
                    model=active_model,
                )
                dialogue.needs_review = True
                dialogue.review_reason = "llm_translation_failed"
                raise
            logger.warning(
                "llm_translation primary_model=%s transient error, "
                "switching to fallback_model=%s dialogue=%s: %s",
                active_model,
                self._fallback_model,
                dialogue.id,
                exc,
            )
            active_model = self._fallback_model
            fallback_used = True
            try:
                candidates = _attempt(active_model)
            except (_anthropic.APIStatusError, _anthropic.APITimeoutError):
                self._record_span(
                    dialogue=dialogue,
                    state=state,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    latency_ms=int((time.monotonic() - t0) * 1000),
                    success=False,
                    fallback_used=True,
                    model=active_model,
                )
                dialogue.needs_review = True
                dialogue.review_reason = "llm_translation_failed"
                raise

        if candidates is None:
            self._record_span(
                dialogue=dialogue,
                state=state,
                input_tokens=total_input,
                output_tokens=total_output,
                latency_ms=int((time.monotonic() - t0) * 1000),
                success=False,
                fallback_used=fallback_used,
                model=active_model,
            )
            dialogue.needs_review = True
            dialogue.review_reason = "llm_translation_failed"
            return []

        self._record_span(
            dialogue=dialogue,
            state=state,
            input_tokens=total_input,
            output_tokens=total_output,
            latency_ms=int((time.monotonic() - t0) * 1000),
            success=True,
            fallback_used=fallback_used,
            model=active_model,
        )
        if self._cache is not None:
            self._cache.set(cache_key, candidates)
        return candidates

    def _record_span(
        self,
        dialogue: DialogueState,
        state: PageAnalysisState | None,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        success: bool,
        fallback_used: bool = False,
        model: str | None = None,
    ) -> None:
        if state is None:
            return
        run_id = str(state.run_id)
        span = ProviderSpan(
            span_id=str(uuid.uuid4()),
            run_id=run_id,
            stage="translation",
            provider="claude",
            model_version=model or self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=0.0,
            success=success,
            fallback_used=fallback_used,
        )
        state.spans.append(span)
