from typing import List

from pydantic import BaseModel


class ReportResponse(BaseModel):
    interview_id: str
    overall_score: int
    technical_score: int
    communication_score: int
    confidence_score: int
    clarity_score: int
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    summary: str