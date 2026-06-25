from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db.database import engine, get_session
from app.db.models import PromptDB, PromptSupportTextDB

router = APIRouter(
    prefix="/prompts",
    tags=["Propostas de Redação"],
)


class PromptCreate(BaseModel):
    title: str = Field(
        ...,
        description="Título interno da proposta."
    )
    theme: str = Field(
        ...,
        description="Tema da redação."
    )
    instructions: str = Field(
        ...,
        description="Comando da proposta de redação."
    )
    support_texts: list[str] = Field(
        default_factory=list,
        description="Textos motivadores da proposta."
    )


class PromptResponse(BaseModel):
    id: str
    title: str
    theme: str
    instructions: str
    support_texts: list[str]

def prompt_db_to_response(
    prompt: PromptDB,
    support_texts: list[PromptSupportTextDB],
) -> PromptResponse:
    return PromptResponse(
        id=prompt.id,
        title=prompt.title,
        theme=prompt.theme,
        instructions=prompt.instructions,
        support_texts=[
            support_text.content for support_text in support_texts
        ],
    )


def get_prompt_support_texts(
    session: Session,
    prompt_id: str,
) -> list[PromptSupportTextDB]:
    return session.exec(
        select(PromptSupportTextDB).where(
            PromptSupportTextDB.prompt_id == prompt_id
        )
    ).all()

def find_prompt(prompt_id: str) -> PromptResponse | None:
    with Session(engine) as session:
        prompt = session.get(PromptDB, prompt_id)

        if prompt is None:
            return None

        support_texts = get_prompt_support_texts(
            session=session,
            prompt_id=prompt.id,
        )

        return prompt_db_to_response(
            prompt=prompt,
            support_texts=support_texts,
        )

@router.post("/", response_model=PromptResponse)
def create_prompt(
    prompt_data: PromptCreate,
    session: Session = Depends(get_session),
):
    prompt_id = str(uuid4())

    prompt = PromptDB(
        id=prompt_id,
        title=prompt_data.title,
        theme=prompt_data.theme,
        instructions=prompt_data.instructions,
    )

    session.add(prompt)

    for text in prompt_data.support_texts:
        support_text = PromptSupportTextDB(
            prompt_id=prompt_id,
            content=text,
        )
        session.add(support_text)

    session.commit()
    session.refresh(prompt)

    support_texts = get_prompt_support_texts(
        session=session,
        prompt_id=prompt.id,
    )

    return prompt_db_to_response(
        prompt=prompt,
        support_texts=support_texts,
    )


@router.get("/", response_model=list[PromptResponse])
def list_prompts(session: Session = Depends(get_session)):
    prompts = session.exec(select(PromptDB)).all()

    result = []

    for prompt in prompts:
        support_texts = get_prompt_support_texts(
            session=session,
            prompt_id=prompt.id,
        )

        result.append(
            prompt_db_to_response(
                prompt=prompt,
                support_texts=support_texts,
            )
        )

    return result

@router.get("/{prompt_id}", response_model=PromptResponse)
def get_prompt(
    prompt_id: str,
    session: Session = Depends(get_session),
):
    prompt = session.get(PromptDB, prompt_id)

    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail="Proposta não encontrada."
        )

    support_texts = get_prompt_support_texts(
        session=session,
        prompt_id=prompt.id,
    )

    return prompt_db_to_response(
        prompt=prompt,
        support_texts=support_texts,
    )