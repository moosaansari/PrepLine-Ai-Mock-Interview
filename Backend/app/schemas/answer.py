
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


CommunicationStyle = Literal[
    "confident",
    "calm",
    "professional",
    "nervous",
    "hesitant",
    "aggressive",
    "neutral",
]


class AnswerCreate(BaseModel):
    interview_id: str = Field(..., min_length=1)
    question_id: str = Field(..., min_length=1)
                                                                       
                                                                       
    question_number: Optional[int] = Field(default=None, ge=1, le=18)
    transcript: str = Field(..., min_length=1, max_length=10000)
                                                                         
                                                                         
                                                                           
                                                                          
                                                                       
                                           
    question_text: Optional[str] = Field(default=None, max_length=2000)


class AnswerResult(BaseModel):
    id: str
    score: int
    technical_score: int
    communication_score: int
    confidence_score: int
    clarity_score: int

    communication_style: CommunicationStyle
    communication_label: str
    communication_feedback: str

    feedback: str
    strengths: List[str]
    improvements: List[str]
