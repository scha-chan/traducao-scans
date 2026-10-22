from fastapi import APIRouter

from app.api.folders import router as folders_router
from app.api.pages import router as pages_router
from app.api.works import router as works_router

api_router = APIRouter(prefix="/api")
api_router.include_router(works_router)
api_router.include_router(folders_router)
api_router.include_router(pages_router)
