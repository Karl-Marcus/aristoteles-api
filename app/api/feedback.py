import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.api.essays import find_essay
from app.api.prompts import find_prompt
from app.db.database import get_session
from app.db.models import FeedbackRecordDB
from app.services.feedback_service import (
    CompareFeedbackResult,
    FeedbackItem,
    FullFeedbackResult,
    generate_ai_comparison_feedback,
    generate_ai_full_feedback,
    generate_ai_paragraph_feedback,
    generate_mock_paragraph_feedback,
    split_paragraphs,
)

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback Pedagógico"],
)

class ParagraphFeedbackRequest(BaseModel):
    essay_id: str = Field(
        ...,
        description="ID da redação que será analisada."
    )
    paragraph_number: int = Field(
        ...,
        ge=1,
        description="Número do parágrafo que receberá feedback."
    )

class FeedbackHistoryItem(BaseModel):
    id: str
    essay_id: str
    feedback_type: str
    version_number: int | None
    previous_version_number: int | None
    current_version_number: int | None
    payload: dict
    created_at: datetime

class ParagraphFeedbackResponse(BaseModel):
    essay_id: str
    paragraph_number: int
    feedback: list[FeedbackItem]

class FullFeedbackRequest(BaseModel):
    essay_id: str = Field(
        ...,
        description="ID da redação completa que será analisada."
    )

class FullFeedbackResponse(FullFeedbackResult):
    essay_id: str
def get_essay_and_selected_paragraph(essay_id: str, paragraph_number: int):
    essay = find_essay(essay_id)

    if essay is None:
        raise HTTPException(
            status_code=404,
            detail="Redação não encontrada."
        )

    latest_version = essay.versions[-1]
    paragraphs = split_paragraphs(latest_version.content)

    if paragraph_number > len(paragraphs):
        raise HTTPException(
            status_code=400,
            detail="O número do parágrafo informado não existe nesta redação."
        )

    selected_paragraph = paragraphs[paragraph_number - 1]

    return essay, selected_paragraph

def get_essay_version_content(essay, version_number: int) -> str:
    for version in essay.versions:
        if version.version_number == version_number:
            return version.content

    raise HTTPException(
        status_code=404,
        detail=f"Versão {version_number} não encontrada nesta redação."
    )

class CompareFeedbackRequest(BaseModel):
    essay_id: str = Field(
        ...,
        description="ID da redação que terá duas versões comparadas."
    )
    previous_version_number: int = Field(
        ...,
        ge=1,
        description="Número da versão anterior."
    )
    current_version_number: int = Field(
        ...,
        ge=1,
        description="Número da versão atual."
    )

class CompareFeedbackResponse(CompareFeedbackResult):
    essay_id: str
    previous_version_number: int
    current_version_number: int

def now_utc() -> datetime:
    return datetime.now(UTC)


def save_feedback_record(
    session: Session,
    essay_id: str,
    feedback_type: str,
    payload: dict,
    version_number: int | None = None,
    previous_version_number: int | None = None,
    current_version_number: int | None = None,
) -> FeedbackRecordDB:
    feedback_record = FeedbackRecordDB(
        id=str(uuid4()),
        essay_id=essay_id,
        feedback_type=feedback_type,
        version_number=version_number,
        previous_version_number=previous_version_number,
        current_version_number=current_version_number,
        payload_json=json.dumps(payload, ensure_ascii=False),
        created_at=now_utc(),
    )

    session.add(feedback_record)
    session.commit()
    session.refresh(feedback_record)

    return feedback_record


def feedback_record_to_response(
    feedback_record: FeedbackRecordDB,
) -> FeedbackHistoryItem:
    return FeedbackHistoryItem(
        id=feedback_record.id,
        essay_id=feedback_record.essay_id,
        feedback_type=feedback_record.feedback_type,
        version_number=feedback_record.version_number,
        previous_version_number=feedback_record.previous_version_number,
        current_version_number=feedback_record.current_version_number,
        payload=json.loads(feedback_record.payload_json),
        created_at=feedback_record.created_at,
    )

@router.post("/paragraph", response_model=ParagraphFeedbackResponse)
def analyze_paragraph_mock(request: ParagraphFeedbackRequest):
    essay, selected_paragraph = get_essay_and_selected_paragraph(
        essay_id=request.essay_id,
        paragraph_number=request.paragraph_number,
    )

    feedback = generate_mock_paragraph_feedback(selected_paragraph)

    return ParagraphFeedbackResponse(
        essay_id=request.essay_id,
        paragraph_number=request.paragraph_number,
        feedback=feedback,
    )


@router.post("/paragraph-ai", response_model=ParagraphFeedbackResponse)
def analyze_paragraph_ai(request: ParagraphFeedbackRequest):
    essay, selected_paragraph = get_essay_and_selected_paragraph(
        essay_id=request.essay_id,
        paragraph_number=request.paragraph_number,
    )

    prompt = find_prompt(essay.prompt_id)

    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail="Proposta vinculada à redação não encontrada."
        )

    try:
        feedback = generate_ai_paragraph_feedback(
            paragraph=selected_paragraph,
            theme=prompt.theme,
        )

        return ParagraphFeedbackResponse(
            essay_id=request.essay_id,
            paragraph_number=request.paragraph_number,
            feedback=feedback,
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar feedback com IA: {error}"
        )
    
@router.post("/full-ai", response_model=FullFeedbackResponse)
def analyze_full_essay_ai(
    request: FullFeedbackRequest,
    session: Session = Depends(get_session),
):
    essay = find_essay(request.essay_id)

    if essay is None:
        raise HTTPException(
            status_code=404,
            detail="Redação não encontrada."
        )

    if not essay.versions:
        raise HTTPException(
            status_code=400,
            detail="A redação não possui versões para análise."
        )

    prompt = find_prompt(essay.prompt_id)

    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail="Proposta vinculada à redação não encontrada."
        )

    latest_version = essay.versions[-1]

    try:
        feedback = generate_ai_full_feedback(
            essay_text=latest_version.content,
            theme=prompt.theme,
        )

        response_data = FullFeedbackResponse(
            essay_id=request.essay_id,
            **feedback.model_dump(),
        )

        save_feedback_record(
            session=session,
            essay_id=request.essay_id,
            feedback_type="full",
            version_number=latest_version.version_number,
            payload=response_data.model_dump(mode="json"),
        )

        return response_data

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar feedback completo com IA: {error}"
        )
    
@router.post("/compare-ai", response_model=CompareFeedbackResponse)
def compare_essay_versions_ai(
    request: CompareFeedbackRequest,
    session: Session = Depends(get_session),
):
    if request.previous_version_number == request.current_version_number:
        raise HTTPException(
            status_code=400,
            detail="As versões comparadas precisam ser diferentes."
        )

    essay = find_essay(request.essay_id)

    if essay is None:
        raise HTTPException(
            status_code=404,
            detail="Redação não encontrada."
        )

    prompt = find_prompt(essay.prompt_id)

    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail="Proposta vinculada à redação não encontrada."
        )

    previous_text = get_essay_version_content(
        essay=essay,
        version_number=request.previous_version_number,
    )

    current_text = get_essay_version_content(
        essay=essay,
        version_number=request.current_version_number,
    )

    try:
        feedback = generate_ai_comparison_feedback(
            previous_text=previous_text,
            current_text=current_text,
            theme=prompt.theme,
        )

        response_data = CompareFeedbackResponse(
            essay_id=request.essay_id,
            previous_version_number=request.previous_version_number,
            current_version_number=request.current_version_number,
            **feedback.model_dump(),
        )

        save_feedback_record(
            session=session,
            essay_id=request.essay_id,
            feedback_type="compare",
            previous_version_number=request.previous_version_number,
            current_version_number=request.current_version_number,
            payload=response_data.model_dump(mode="json"),
        )

        return response_data

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao comparar versões com IA: {error}"
        )
    
@router.get("/history/{essay_id}", response_model=list[FeedbackHistoryItem])
def list_feedback_history(
    essay_id: str,
    session: Session = Depends(get_session),
):
    essay = find_essay(essay_id)

    if essay is None:
        raise HTTPException(
            status_code=404,
            detail="Redação não encontrada."
        )

    feedback_records = session.exec(
        select(FeedbackRecordDB)
        .where(FeedbackRecordDB.essay_id == essay_id)
        .order_by(FeedbackRecordDB.created_at.desc())
    ).all()

    return [
        feedback_record_to_response(feedback_record)
        for feedback_record in feedback_records
    ]