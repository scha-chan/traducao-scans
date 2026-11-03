from fastapi import APIRouter
from pydantic import BaseModel

from app.settings import settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsOut(BaseModel):
    ocr_low_confidence_threshold: float
    export_policy: str
    budget_usd_per_run: float


@router.get("")
def get_settings() -> SettingsOut:
    return SettingsOut(
        ocr_low_confidence_threshold=settings.ocr_low_confidence_threshold,
        export_policy=settings.export_policy,
        budget_usd_per_run=settings.budget_usd_per_run,
    )
