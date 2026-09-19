import logging

from fastapi import APIRouter, HTTPException, Request

from app.schemas.interview import InterviewCreate
from app.core.auth import get_optional_auth_user
from app.core.rate_limit import interview_creation_limiter
from app.services.interview_service import (
    complete_interview,
    create_interview,
    generate_question,
    get_interview,
    get_user_interviews,
)

router = APIRouter(prefix="/api", tags=["Interviews"])

logger = logging.getLogger(__name__)


@router.post("/interviews")
def create_interview_route(payload: InterviewCreate, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not interview_creation_limiter.allow(client_ip):
        raise HTTPException(429, detail="Too many interview starts. Please wait a minute and try again.")

    try:
        interview_data = payload.model_dump()
        auth_user = get_optional_auth_user(request)
        if auth_user:
            interview_data["user_id"] = str(auth_user["uid"])

        logger.info("Creating interview with payload: %s", interview_data)

        interview = create_interview(interview_data)

        logger.info("Interview created: %s", interview["id"])

        return {
            "success": True,
            "interview": interview,
        }

    except ValueError as exc:
        logger.exception("Interview validation error")

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Interview creation failed")

        raise HTTPException(
            status_code=500,
            detail=f"Unable to create interview: {str(exc)}",
        ) from exc


@router.get("/interviews/{interview_id}")
def get_interview_route(interview_id: str, request: Request):
    try:
        interview = get_interview(interview_id)
        auth_user = get_optional_auth_user(request)
        if auth_user and interview and interview.get("user_id") != str(auth_user["uid"]):
            raise HTTPException(status_code=403, detail="You do not have access to this interview.")

        if not interview:
            raise HTTPException(
                status_code=404,
                detail="Interview not found.",
            )

        return {
            "success": True,
            "interview": interview,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Failed to retrieve interview: %s",
            interview_id,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Unable to retrieve interview: {str(exc)}",
        ) from exc


@router.get("/interviews/{interview_id}/question")
def get_question(interview_id: str, request: Request):
    try:
        interview = get_interview(interview_id)
        auth_user = get_optional_auth_user(request)
        if auth_user and interview and interview.get("user_id") != str(auth_user["uid"]):
            raise HTTPException(status_code=403, detail="You do not have access to this interview.")
        question = generate_question(interview_id)

        logger.info(
            "Question generated: %s",
            question["id"],
        )

        return {
            "success": True,
            "question": {
                "id": question["id"],
                "number": question["number"],
                "text": question["text"],
                "type": question["type"],
            },
        }

    except ValueError as exc:
        message = str(exc)

        logger.warning(
            "Question generation validation error for %s: %s",
            interview_id,
            message,
        )

        raise HTTPException(
            status_code=404 if "not found" in message.lower() else 400,
            detail=message,
        ) from exc

    except Exception as exc:
        logger.exception(
            "Question generation failed for interview: %s",
            interview_id,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Unable to generate question: {str(exc)}",
        ) from exc


@router.post("/interviews/{interview_id}/complete")
def complete_interview_route(interview_id: str, request: Request):
    try:
        existing = get_interview(interview_id)
        auth_user = get_optional_auth_user(request)
        if auth_user and existing and existing.get("user_id") != str(auth_user["uid"]):
            raise HTTPException(status_code=403, detail="You do not have access to this interview.")
        interview = complete_interview(interview_id)

        logger.info(
            "Interview completed: %s",
            interview_id,
        )

        return {
            "success": True,
            "interview": interview,
        }

    except ValueError as exc:
        logger.warning(
            "Interview completion validation error for %s: %s",
            interview_id,
            str(exc),
        )

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Interview completion failed for %s",
            interview_id,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Unable to complete interview: {str(exc)}",
        ) from exc


@router.get("/users/{user_id}/interviews")
def user_interviews(user_id: str, request: Request):
    try:
        auth_user = get_optional_auth_user(request)
        if auth_user and str(auth_user["uid"]) != user_id:
            raise HTTPException(status_code=403, detail="You do not have access to this history.")
        interviews = get_user_interviews(user_id)

        return {
            "success": True,
            "interviews": interviews,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Failed to retrieve interview history for user: %s",
            user_id,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Unable to retrieve interview history: {str(exc)}",
        ) from exc