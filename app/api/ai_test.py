from fastapi import APIRouter, HTTPException

from app.clients.openai_client import get_openai_client
from app.core.config import OPENAI_MODEL


router = APIRouter(
    prefix="/ai-test",
    tags=["Teste de IA"],
)


@router.get("/")
def test_ai_connection():
    try:
        client = get_openai_client()

        response = client.responses.create(
            model=OPENAI_MODEL,
            input="Responda apenas: Aristóteles conectado."
        )

        return {
            "status": "ok",
            "message": response.output_text
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )