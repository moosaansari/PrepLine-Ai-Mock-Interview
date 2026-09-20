import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.core.firebase import get_db, get_document

router = APIRouter(prefix="/api/auth", tags=["Auth"])

TOKEN_PREFIX = "prepline-demo."


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    remember: bool = False


class RegisterPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 120_000
    ).hex()


def _make_token(uid: str) -> str:
    return TOKEN_PREFIX + uid + "." + secrets.token_urlsafe(18)


def _verify_demo_token(token: str) -> Optional[dict]:
    if not token.startswith(TOKEN_PREFIX):
        return None
    parts = token.split(".")
    if len(parts) < 2:
        return None
    uid = parts[1]
    if not uid:
        return None
    try:
        user = get_document("users", uid)
    except Exception:
        return None
    if not user:
        return None
    return {"uid": uid, "email": user.get("email"), "name": user.get("name")}


def _public_user(user: dict) -> dict:
    return {
        "uid": user.get("id") or user.get("uid"),
        "id": user.get("id") or user.get("uid"),
        "name": user.get("name", "Candidate"),
        "email": user.get("email"),
    }


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
        return {"enabled": False, "mode": "demo"}
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


@router.post("/register")
def register(payload: RegisterPayload):
    db = get_db()
    email = str(payload.email).lower()
    existing = list(db.collection("users").where("email", "==", email).limit(1).stream())
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    uid = secrets.token_hex(16)
    salt = secrets.token_urlsafe(16)
    user = {
        "id": uid,
        "name": payload.name.strip() or "Candidate",
        "email": email,
        "password_hash": _hash_password(payload.password, salt),
        "password_salt": salt,
        "target_role": "Software Engineer",
        "experience_level": "Fresher",
        "created_at": datetime.now(timezone.utc),
    }
    db.collection("users").document(uid).set(user)
    return {"success": True, "token": _make_token(uid), "user": _public_user(user)}


@router.post("/login")
def login(payload: LoginPayload):
    db = get_db()
    email = str(payload.email).lower()
    docs = list(db.collection("users").where("email", "==", email).limit(1).stream())
    if not docs:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user = docs[0].to_dict() or {}
    uid = docs[0].id
    salt = user.get("password_salt")
    stored = user.get("password_hash")
    if not salt or not stored or not hmac.compare_digest(_hash_password(payload.password, salt), stored):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user["id"] = uid
    return {"success": True, "token": _make_token(uid), "user": _public_user(user)}


@router.get("/me")
def me(request: Request):
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user = _verify_demo_token(header[7:].strip())
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    return {"success": True, "user": user}


@router.post("/logout")
def logout():
    return {"success": True, "message": "Signed out successfully."}


@router.post("/google")
def google_login():
    raise HTTPException(status_code=400, detail="Use the Google sign-in button when Firebase Auth is configured.")


@router.post("/github")
def github_login():
    raise HTTPException(status_code=400, detail="Use the GitHub sign-in button when Firebase Auth is configured.")
