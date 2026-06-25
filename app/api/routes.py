from app.api.dev import router as dev_router
from app.api.ai_test import router as ai_test_router
from fastapi import APIRouter

from app.api.essays import router as essays_router
from app.api.feedback import router as feedback_router
from app.api.prompts import router as prompts_router
from app.api.db_test import router as db_test_router

router = APIRouter()

@router.get("/")
def read_root():
    return {
        "message": "Bem-vindo à API do Aristóteles."
    }

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Aristóteles está vivo."
    }

router.include_router(prompts_router)
router.include_router(essays_router)
router.include_router(feedback_router)
router.include_router(ai_test_router)
router.include_router(dev_router)
router.include_router(db_test_router)
