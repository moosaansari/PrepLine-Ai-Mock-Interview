import logging

from fastapi import APIRouter, HTTPException, Request

from app.core.auth import get_optional_auth_user
from app.core.firebase import get_document
from app.schemas.answer import AnswerCreate
from app.services.interview_service import (
    save_answer_and_evaluate,
)

router = APIRouter(
    prefix="/api",
    tags=["Answers"],
)

logger = logging.getLogger(__name__)


@router.post("/answers")
def create_answer(
    payload: AnswerCreate,
    request: Request,
):
    try:
        auth_user = get_optional_auth_user(request)
        interview = get_document("interviews", payload.interview_id)
        if not interview:
            raise ValueError("Interview not found.")
        if auth_user and interview.get("user_id") != str(auth_user["uid"]):
            raise HTTPException(status_code=403, detail="You do not have access to this interview.")

        result = save_answer_and_evaluate(
            interview_id=payload.interview_id,
            question_id=payload.question_id,
            question_number=payload.question_number,
            transcript=payload.transcript,
            question_text=payload.question_text,
        )

        return {
            "success": True,
            "answer": result,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Answer submission failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to submit answer.",
        ) from exc
