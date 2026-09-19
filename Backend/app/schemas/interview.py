from typing import Optional

from pydantic import BaseModel, Field


class InterviewCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    interview_type: str = Field(..., min_length=2, max_length=50)
    difficulty: Optional[str] = None
    total_questions: int = Field(..., ge=10, le=18)
    language: str = Field(..., min_length=2, max_length=50)
    interviewer_style: str = Field(..., min_length=2, max_length=50)
    communication_context: Optional[str] = None


class QuestionResponse(BaseModel):
    id: str
    number: int
    text: str
    type: str


class InterviewResponse(BaseModel):
    id: str
    user_id: str
    status: str
    current_question: int
    total_questions: int