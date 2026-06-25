import json

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.api.prompts import find_prompt
from app.db.database import engine, get_session
from app.db.models import EssayDB, EssayVersionDB, FeedbackRecordDB


router = APIRouter(
    prefix="/essays",
    tags=["Redações"],
)


class EssayCreate(BaseModel):
    prompt_id: str = Field(
        ...,
        description="ID da proposta de redação vinculada."
    )
    student_alias: str = Field(
        ...,
        description="Identificação simples do aluno."
    )
    content: str = Field(
        ...,
        description="Conteúdo inicial da redação."
    )


class EssayVersionCreate(BaseModel):
    content: str = Field(
        ...,
        description="Nova versão da redação."
    )


class EssayVersionResponse(BaseModel):
    id: str
    version_number: int
    content: str
    created_at: datetime


class EssayResponse(BaseModel):
    id: str
    prompt_id: str
    student_alias: str
    status: str
    versions: list[EssayVersionResponse]
    created_at: datetime
    updated_at: datetime

class DashboardFeedbackSummary(BaseModel):
    id: str
    feedback_type: str
    version_number: int | None
    previous_version_number: int | None
    current_version_number: int | None
    summary: str | None
    overall_evolution: str | None
    next_steps: list[str]
    created_at: datetime


class EssayDashboardResponse(BaseModel):
    essay: EssayResponse
    prompt_title: str
    prompt_theme: str
    total_versions: int
    latest_version_number: int | None
    latest_full_feedback: DashboardFeedbackSummary | None
    latest_comparison: DashboardFeedbackSummary | None

def now_utc() -> datetime:
    return datetime.now(UTC)


def essay_version_db_to_response(
    version: EssayVersionDB,
) -> EssayVersionResponse:
    return EssayVersionResponse(
        id=version.id,
        version_number=version.version_number,
        content=version.content,
        created_at=version.created_at,
    )


def get_essay_versions(
    session: Session,
    essay_id: str,
) -> list[EssayVersionDB]:
    return session.exec(
        select(EssayVersionDB)
        .where(EssayVersionDB.essay_id == essay_id)
        .order_by(EssayVersionDB.version_number)
    ).all()


def essay_db_to_response(
    essay: EssayDB,
    versions: list[EssayVersionDB],
) -> EssayResponse:
    return EssayResponse(
        id=essay.id,
        prompt_id=essay.prompt_id,
        student_alias=essay.student_alias,
        status=essay.status,
        versions=[
            essay_version_db_to_response(version)
            for version in versions
        ],
        created_at=essay.created_at,
        updated_at=essay.updated_at,
    )

def feedback_record_to_dashboard_summary(
    feedback_record: FeedbackRecordDB,
) -> DashboardFeedbackSummary:
    payload = json.loads(feedback_record.payload_json)

    return DashboardFeedbackSummary(
        id=feedback_record.id,
        feedback_type=feedback_record.feedback_type,
        version_number=feedback_record.version_number,
        previous_version_number=feedback_record.previous_version_number,
        current_version_number=feedback_record.current_version_number,
        summary=payload.get("summary"),
        overall_evolution=payload.get("overall_evolution"),
        next_steps=payload.get("next_steps") or payload.get("next_revision_focus") or [],
        created_at=feedback_record.created_at,
    )


def get_latest_feedback_record(
    session: Session,
    essay_id: str,
    feedback_type: str,
) -> FeedbackRecordDB | None:
    return session.exec(
        select(FeedbackRecordDB)
        .where(FeedbackRecordDB.essay_id == essay_id)
        .where(FeedbackRecordDB.feedback_type == feedback_type)
        .order_by(FeedbackRecordDB.created_at.desc())
    ).first()

def find_essay(essay_id: str) -> EssayResponse | None:
    with Session(engine) as session:
        essay = session.get(EssayDB, essay_id)

        if essay is None:
            return None

        versions = get_essay_versions(
            session=session,
            essay_id=essay.id,
        )

        return essay_db_to_response(
            essay=essay,
            versions=versions,
        )

@router.post("/", response_model=EssayResponse)
def create_essay(
    essay_data: EssayCreate,
    session: Session = Depends(get_session),
):
    prompt = find_prompt(essay_data.prompt_id)

    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail="Proposta vinculada à redação não encontrada."
        )

    current_time = now_utc()
    essay_id = str(uuid4())
    version_id = str(uuid4())

    essay = EssayDB(
        id=essay_id,
        prompt_id=essay_data.prompt_id,
        student_alias=essay_data.student_alias,
        status="draft",
        created_at=current_time,
        updated_at=current_time,
    )

    first_version = EssayVersionDB(
        id=version_id,
        essay_id=essay_id,
        version_number=1,
        content=essay_data.content,
        created_at=current_time,
    )

    session.add(essay)
    session.add(first_version)
    session.commit()
    session.refresh(essay)

    versions = get_essay_versions(
        session=session,
        essay_id=essay.id,
    )

    return essay_db_to_response(
        essay=essay,
        versions=versions,
    )

@router.get("/", response_model=list[EssayResponse])
def list_essays(session: Session = Depends(get_session)):
    essays = session.exec(select(EssayDB)).all()

    result = []

    for essay in essays:
        versions = get_essay_versions(
            session=session,
            essay_id=essay.id,
        )

        result.append(
            essay_db_to_response(
                essay=essay,
                versions=versions,
            )
        )

    return result

@router.get("/{essay_id}", response_model=EssayResponse)
def get_essay(essay_id: str):
    essay = find_essay(essay_id)

    if essay is None:
        raise HTTPException(
            status_code=404,
            detail="Redação não encontrada."
        )

    return essay


@router.post("/{essay_id}/versions", response_model=EssayResponse)
def add_essay_version(
    essay_id: str,
    version_data: EssayVersionCreate,
    session: Session = Depends(get_session),
):
    essay = session.get(EssayDB, essay_id)

    if essay is None:
        raise HTTPException(
            status_code=404,
            detail="Redação não encontrada no banco."
        )

    existing_versions = get_essay_versions(
        session=session,
        essay_id=essay.id,
    )

    next_version_number = len(existing_versions) + 1
    current_time = now_utc()

    new_version = EssayVersionDB(
        id=str(uuid4()),
        essay_id=essay.id,
        version_number=next_version_number,
        content=version_data.content,
        created_at=current_time,
    )

    essay.updated_at = current_time

    session.add(new_version)
    session.add(essay)
    session.commit()
    session.refresh(essay)

    versions = get_essay_versions(
        session=session,
        essay_id=essay.id,
    )

    return essay_db_to_response(
        essay=essay,
        versions=versions,
    )

@router.get("/{essay_id}/dashboard", response_model=EssayDashboardResponse)
def get_essay_dashboard(
    essay_id: str,
    session: Session = Depends(get_session),
):
    essay = session.get(EssayDB, essay_id)

    if essay is None:
        raise HTTPException(
            status_code=404,
            detail="Redação não encontrada."
        )

    versions = get_essay_versions(
        session=session,
        essay_id=essay.id,
    )

    essay_response = essay_db_to_response(
        essay=essay,
        versions=versions,
    )

    prompt = find_prompt(essay.prompt_id)

    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail="Proposta vinculada à redação não encontrada."
        )

    latest_full_feedback_record = get_latest_feedback_record(
        session=session,
        essay_id=essay.id,
        feedback_type="full",
    )

    latest_comparison_record = get_latest_feedback_record(
        session=session,
        essay_id=essay.id,
        feedback_type="compare",
    )

    latest_full_feedback = None

    if latest_full_feedback_record is not None:
        latest_full_feedback = feedback_record_to_dashboard_summary(
            latest_full_feedback_record
        )

    latest_comparison = None

    if latest_comparison_record is not None:
        latest_comparison = feedback_record_to_dashboard_summary(
            latest_comparison_record
        )

    latest_version_number = None

    if versions:
        latest_version_number = versions[-1].version_number

    return EssayDashboardResponse(
        essay=essay_response,
        prompt_title=prompt.title,
        prompt_theme=prompt.theme,
        total_versions=len(versions),
        latest_version_number=latest_version_number,
        latest_full_feedback=latest_full_feedback,
        latest_comparison=latest_comparison,
    )