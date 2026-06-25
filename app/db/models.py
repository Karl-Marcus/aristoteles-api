from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class PromptDB(SQLModel, table=True):
    __tablename__ = "prompts"

    id: str = Field(primary_key=True)
    title: str
    theme: str
    instructions: str


class EssayDB(SQLModel, table=True):
    __tablename__ = "essays"

    id: str = Field(primary_key=True)
    prompt_id: str = Field(foreign_key="prompts.id")
    student_alias: str
    status: str
    created_at: datetime
    updated_at: datetime


class EssayVersionDB(SQLModel, table=True):
    __tablename__ = "essay_versions"

    id: str = Field(primary_key=True)
    essay_id: str = Field(foreign_key="essays.id")
    version_number: int
    content: str
    created_at: datetime


class PromptSupportTextDB(SQLModel, table=True):
    __tablename__ = "prompt_support_texts"

    id: Optional[int] = Field(default=None, primary_key=True)
    prompt_id: str = Field(foreign_key="prompts.id")
    content: str

{
  "essay_id": "essay-demo-rewrite",
  "previous_version_number": 1,
  "current_version_number": 2
}

class FeedbackRecordDB(SQLModel, table=True):
    __tablename__ = "feedback_records"

    id: str = Field(primary_key=True)
    essay_id: str = Field(foreign_key="essays.id")
    feedback_type: str
    version_number: Optional[int] = Field(default=None)
    previous_version_number: Optional[int] = Field(default=None)
    current_version_number: Optional[int] = Field(default=None)
    payload_json: str
    created_at: datetime