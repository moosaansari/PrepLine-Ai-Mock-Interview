from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.get("/config")
def auth_config():
    configured = all(
        [
            settings.FIREBASE_WEB_API_KEY,
            settings.FIREBASE_AUTH_DOMAIN,
            settings.FIREBASE_PROJECT_ID,
            settings.FIREBASE_APP_ID,
        ]
    )

    if not configured:
        return {"enabled": False}

    return {
        "enabled": True,
        "config": {
            "apiKey": settings.FIREBASE_WEB_API_KEY,
            "authDomain": settings.FIREBASE_AUTH_DOMAIN,
            "projectId": settings.FIREBASE_PROJECT_ID,
            "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
            "messagingSenderId": settings.FIREBASE_MESSAGING_SENDER_ID,
            "appId": settings.FIREBASE_APP_ID,
        },
    }
