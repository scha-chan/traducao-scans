"""LowConfidenceStage: marca diálogos com OCR abaixo do threshold (F3-AG-05)."""

from __future__ import annotations

from agent.stage import Stage
from agent.state import PageAnalysisState

_DEFAULT_THRESHOLD = 0.80


class LowConfidenceStage(Stage):
    """Seta needs_review=True em diálogos cujo ocr_confidence < threshold.

    Deve rodar após OcrStage e antes de TranslationStage, pois depende de
    ocr_confidence já preenchido e permite que o tradutor saiba que o texto
    pode estar incorreto antes de tentar traduzir.

    Diálogos sem ocr_confidence (None) são ignorados silenciosamente.
    """

    def __init__(self, threshold: float = _DEFAULT_THRESHOLD) -> None:
        self._threshold = threshold

    @property
    def name(self) -> str:
        return "low_confidence"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        for dialogue in state.dialogues:
            if dialogue.ocr_confidence is None:
                continue
            if dialogue.ocr_confidence < self._threshold:
                dialogue.needs_review = True
                dialogue.review_reason = "low_ocr_confidence"
        return state
