import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.auth import get_optional_auth_user
from app.core.firebase import get_db, get_document

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])
logger = logging.getLogger(__name__)


def _jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _session(interview_id: str) -> Optional[dict]:
    interview = get_document("interviews", interview_id)
    if not interview:
        return None
    db = get_db()
    answers = list(db.collection("answers").where("interview_id", "==", interview_id).stream())
    report = get_document("reports", interview_id) or {}
    scores = [
        (a.to_dict() or {}).get("evaluation", {}).get("overall_score")
        for a in answers
    ]
    scores = [float(s) for s in scores if isinstance(s, (int, float))]
    overall = report.get("overall_score")
    if overall is None and scores:
        overall = round(sum(scores) / len(scores))
    total = int(interview.get("total_questions") or 0)
    answered = len(answers)
    created = interview.get("created_at")
    completed = interview.get("completed_at")
    start = created.timestamp() if isinstance(created, datetime) else None
    end = completed.timestamp() if isinstance(completed, datetime) else None
    duration = round((end - start) / 60, 1) if start and end and end >= start else None
    return _jsonable({
        **interview,
        "id": interview_id,
        "interview_id": interview_id,
        "type": interview.get("interview_type", "Mixed"),
        "overall_score": overall,
        "score": overall,
        "questions_answered": answered,
        "duration": duration,
        "date": created,
        "created_at": created,
        "updated_at": interview.get("updated_at"),
        "status": interview.get("status", "active"),
        "communication_context": interview.get("communication_context", "neutral"),
    })


@router.get("")
def list_sessions(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    interview_id: Optional[str] = None,
):
    try:
        auth_user = get_optional_auth_user(request)
        db = get_db()
        if interview_id:
            item = _session(interview_id)
            if not item:
                return {"success": True, "sessions": [], "items": [], "total": 0, "page": page, "page_size": page_size}
            if auth_user and item.get("user_id") != str(auth_user["uid"]):
                raise HTTPException(status_code=403, detail="You do not have access to this session.")
            return {"success": True, "sessions": [item], "items": [item], "total": 1, "page": 1, "page_size": page_size}

        query = db.collection("interviews")
        if auth_user:
            query = query.where("user_id", "==", str(auth_user["uid"]))
        docs = list(query.stream())
        items = []
        for doc in docs:
            item = _session(doc.id)
            if item:
                items.append(item)
        items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        start = (page - 1) * page_size
        page_items = items[start:start + page_size]
        return {"success": True, "sessions": page_items, "items": page_items, "total": len(items), "page": page, "page_size": page_size}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load sessions")
        raise HTTPException(status_code=500, detail=f"Unable to load sessions: {exc}") from exc


@router.get("/{interview_id}")
def get_session(interview_id: str, request: Request):
    item = _session(interview_id)
    if not item:
        raise HTTPException(status_code=404, detail="Session not found.")
    auth_user = get_optional_auth_user(request)
    if auth_user and item.get("user_id") != str(auth_user["uid"]):
        raise HTTPException(status_code=403, detail="You do not have access to this session.")
    return {"success": True, "session": item}


@router.delete("/{interview_id}")
def delete_session(interview_id: str, request: Request):
    item = _session(interview_id)
    if not item:
        raise HTTPException(status_code=404, detail="Session not found.")
    auth_user = get_optional_auth_user(request)
    if auth_user and item.get("user_id") != str(auth_user["uid"]):
        raise HTTPException(status_code=403, detail="You do not have access to this session.")
    db = get_db()
    for collection in ("answers", "questions"):
        docs = list(db.collection(collection).where("interview_id", "==", interview_id).stream())
        for doc in docs:
            doc.reference.delete()
    db.collection("reports").document(interview_id).delete()
    db.collection("interviews").document(interview_id).delete()
    return {"success": True}
