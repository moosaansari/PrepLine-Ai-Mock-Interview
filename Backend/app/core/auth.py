import logging
from typing import Any, Dict, Optional

from fastapi import Request

from app.core.firebase import initialize_firebase

logger = logging.getLogger(__name__)


def get_optional_auth_user(request: Request) -> Optional[Dict[str, Any]]:
    """Return the Firebase user from a bearer token when available.

    Auth is deliberately optional so the existing anonymous demo flow keeps
    working if Firebase Auth is not configured or a token cannot be verified.
    """
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None

    token = header[7:].strip()
    if not token:
        return None

    try:
        initialize_firebase()
        from firebase_admin import auth
        return auth.verify_id_token(token)
    except Exception as exc:
        logger.warning("Optional Firebase Auth verification failed: %s", exc)
        return None
