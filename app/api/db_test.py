from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.database import get_session
from app.db.models import PromptDB, PromptSupportTextDB

router = APIRouter(
    prefix="/db-test",
    tags=["Banco de Dados - Teste"],
)

TEST_PROMPT_ID = "prompt-db-test-enem-2018"


@router.post("/seed-prompt")
def seed_test_prompt(session: Session = Depends(get_session)):
    existing_prompt = session.get(PromptDB, TEST_PROMPT_ID)

    if existing_prompt is not None:
        return {
            "status": "already_exists",
            "message": "A proposta de teste já existe no banco.",
            "prompt_id": TEST_PROMPT_ID,
        }

    prompt = PromptDB(
        id=TEST_PROMPT_ID,
        title="Tema ENEM 2018 - Teste no Banco",
        theme="Manipulação do comportamento do usuário pelo controle de dados na internet",
        instructions="Produza um texto dissertativo-argumentativo em modalidade escrita formal da língua portuguesa sobre o tema apresentado.",
    )

    session.add(prompt)

    support_texts = [
        "Texto motivador 1: discussão sobre coleta de dados e comportamento online.",
        "Texto motivador 2: reflexão sobre algoritmos, publicidade direcionada e influência sobre escolhas individuais.",
    ]

    for text in support_texts:
        support_text = PromptSupportTextDB(
            prompt_id=TEST_PROMPT_ID,
            content=text,
        )
        session.add(support_text)

    session.commit()

    return {
        "status": "ok",
        "message": "Proposta de teste criada no banco com sucesso.",
        "prompt_id": TEST_PROMPT_ID,
    }


@router.get("/prompts")
def list_db_prompts(session: Session = Depends(get_session)):
    prompts = session.exec(select(PromptDB)).all()

    result = []

    for prompt in prompts:
        support_texts = session.exec(
            select(PromptSupportTextDB).where(
                PromptSupportTextDB.prompt_id == prompt.id
            )
        ).all()

        result.append(
            {
                "id": prompt.id,
                "title": prompt.title,
                "theme": prompt.theme,
                "instructions": prompt.instructions,
                "support_texts": [
                    support_text.content for support_text in support_texts
                ],
            }
        )

    return {
        "total": len(result),
        "prompts": result,
    }