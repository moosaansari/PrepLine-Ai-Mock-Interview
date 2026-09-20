import logging
from typing import Any, Dict, Optional

from fastapi import Request

from app.core.firebase import initialize_firebase, get_document

logger = logging.getLogger(__name__)


def get_optional_auth_user(request: Request) -> Optional[Dict[str, Any]]:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    if not token:
        return None

    if token.startswith("prepline-demo."):
        parts = token.split(".")
        uid = parts[1] if len(parts) > 1 else ""
        if uid:
            try:
                user = get_document("users", uid)
                if user:
                    return {"uid": uid, "email": user.get("email"), "name": user.get("name")}
            except Exception:
                logger.exception("Demo auth lookup failed")
        return None

    try:
        initialize_firebase()
        from firebase_admin import auth
        return auth.verify_id_token(token)
    except Exception as exc:
        logger.warning("Optional Firebase Auth verification failed: %s", exc)
        return None
