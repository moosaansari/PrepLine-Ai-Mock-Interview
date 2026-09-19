import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.core.auth import get_optional_auth_user
from app.core.firebase import create_document
from app.schemas.user import UserCreate

router = APIRouter(prefix="/api", tags=["Users"])
logger = logging.getLogger(__name__)


@router.post("/users")
def create_user(payload: UserCreate, request: Request):
    try:
        auth_user = get_optional_auth_user(request)
        user_id = str(auth_user.get("uid")) if auth_user else str(uuid.uuid4())
        auth_name = (auth_user or {}).get("name")
        auth_email = (auth_user or {}).get("email")

        user_data = {
            "id": user_id,
            "name": auth_name or payload.name or "Candidate",
            "email": auth_email or (str(payload.email) if payload.email else None),
            "target_role": payload.target_role or "Software Engineer",
            "experience_level": payload.experience_level or "Fresher",
            "created_at": datetime.now(timezone.utc),
        }

        user = create_document(
            collection_name="users",
            document_id=user_id,
            data=user_data,
        )

        logger.info("User created: %s | role=%s", user_id, user_data["target_role"])

        return {"success": True, "user": user}

    except Exception as exc:
        logger.exception("User creation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Unable to create user: {str(exc)}",
        ) from exc
