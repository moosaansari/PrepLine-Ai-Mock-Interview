from fastapi import APIRouter, HTTPException

from app.services.gemini_live_service import test_gemini_connection

router = APIRouter(prefix="/api", tags=["Gemini"])


@router.get("/gemini/test")
def gemini_test():
    try:
        result = test_gemini_connection()
        return {
            "success": True,
            "result": result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc