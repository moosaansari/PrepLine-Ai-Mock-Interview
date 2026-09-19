from datetime import datetime, timezone
from typing import Any, Dict

from app.core.firebase import create_document, get_document, list_documents, update_document
from app.services.ai_service import generate_final_report


def _now():
    return datetime.now(timezone.utc)


def generate_report(interview_id: str) -> Dict[str, Any]:
    interview = get_document("interviews", interview_id)
    if not interview:
        raise ValueError("Interview not found.")

    answers = list_documents(
        "answers",
        filters=[{"field": "interview_id", "operator": "==", "value": interview_id}],
    )
    answers.sort(key=lambda item: item.get("question_number", 0))

    final = generate_final_report(
        role=interview.get("role", "Software Engineer"),
        interview_answers=answers,
        language=interview.get("language", "English"),
        communication_context=interview.get(
            "communication_context",
            "neutral",
        ),
    )

    report = {
        "interview_id": interview_id,
        **final,
        "created_at": _now(),
    }

    existing = get_document("reports", interview_id)
    if existing:
        update_document("reports", interview_id, report)
        return get_document("reports", interview_id)

    return create_document("reports", report, document_id=interview_id)
