from fastapi import APIRouter

from app.api.works import router as works_router

api_router = APIRouter(prefix="/api")
api_router.include_router(works_router)
