"""
PREPLINE Diagnostics & Health Check Endpoints

Provides health checks for external services and system status.
"""

import logging
import time

from fastapi import APIRouter, HTTPException

from app.core.config import settings

router = APIRouter(prefix="/api/diagnostics", tags=["Diagnostics"])

logger = logging.getLogger(__name__)


@router.get("/health")
async def health():
    """
    Basic health check endpoint.
    """
    return {
        "success": True,
        "message": "Prepline backend is running",
    }


@router.get("/health/gemini")
async def gemini_health():
    """
    Test Gemini API connectivity and response time.
    """
    if not settings.GEMINI_API_KEY:
        return {
            "status": "unavailable",
            "message": "GEMINI_API_KEY not configured",
            "configured": False,
        }

    try:
        from google import genai

        start_time = time.time()

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

                             
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents="Reply with: OK",
        )

        latency_ms = int((time.time() - start_time) * 1000)

        response_text = response.text.strip()

        return {
            "status": "healthy",
            "message": "Gemini API is responding",
            "latency_ms": latency_ms,
            "configured": True,
            "test_response": response_text[:50],
        }

    except Exception as exc:
        logger.exception("Gemini health check failed: %s", exc)

        return {
            "status": "unhealthy",
            "message": f"Gemini API error: {str(exc)[:100]}",
            "configured": True,
        }


@router.get("/health/elevenlabs")
async def elevenlabs_health():
    """
    Test ElevenLabs API connectivity.
    """
    if not settings.ELEVENLABS_API_KEY:
        return {
            "status": "unavailable",
            "message": "ELEVENLABS_API_KEY not configured",
            "configured": False,
        }

    try:
        import requests

        start_time = time.time()

                                                                  
                                                                        
                                                                      
                                                                        
                                                        
        response = requests.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            files={
                "file": (
                    "health-check.webm",
                    b"not-real-audio",
                    "audio/webm",
                ),
            },
            data={"model_id": settings.ELEVENLABS_STT_MODEL},
            timeout=15,
        )

        latency_ms = int((time.time() - start_time) * 1000)

                                                            
        if response.status_code == 400:
            return {
                "status": "healthy",
                "message": "ElevenLabs API key is valid (speech-to-text authorized)",
                "latency_ms": latency_ms,
                "configured": True,
            }

                                                            
        response.raise_for_status()

        return {
            "status": "healthy",
            "message": "ElevenLabs API is responding",
            "latency_ms": latency_ms,
            "configured": True,
        }

    except requests.RequestException as exc:
        logger.exception("ElevenLabs health check failed: %s", exc)

        return {
            "status": "unhealthy",
            "message": f"ElevenLabs API error: {str(exc)[:100]}",
            "configured": True,
        }

    except Exception as exc:
        logger.exception("ElevenLabs health check failed: %s", exc)

        return {
            "status": "unhealthy",
            "message": f"Unexpected error: {str(exc)[:100]}",
            "configured": True,
        }


@router.get("/health/firebase")
async def firebase_health():
    """
    Test Firebase Firestore connectivity.
    """
    try:
        from app.core.firebase import get_db

        db = get_db()

                           
        start_time = time.time()

                                          
        collections = list(db.collections())

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "status": "healthy",
            "message": "Firebase Firestore is accessible",
            "latency_ms": latency_ms,
            "configured": True,
        }

    except Exception as exc:
        logger.exception("Firebase health check failed: %s", exc)

        return {
            "status": "unhealthy",
            "message": f"Firebase error: {str(exc)[:100]}",
            "configured": False,
        }


@router.get("/diagnostics/{interview_id}")
async def interview_diagnostics(interview_id: str):
    """
    Get diagnostic information for a specific interview.
    Does not return sensitive user data.
    """
    try:
        from app.core.firebase import get_db

        db = get_db()

                       
        interview_doc = db.collection("interviews").document(interview_id).get()

        if not interview_doc.exists:
            raise HTTPException(status_code=404, detail="Interview not found")

        interview = interview_doc.to_dict()

                           
        answers_count = len(
            list(
                db.collection("answers")
                .where("interview_id", "==", interview_id)
                .stream()
            )
        )

                             
        questions_count = len(
            list(
                db.collection("questions")
                .where("interview_id", "==", interview_id)
                .stream()
            )
        )

        return {
            "success": True,
            "interview_id": interview_id,
            "status": interview.get("status"),
            "current_question_number": interview.get("current_question_number"),
            "total_questions": interview.get("total_questions"),
            "answers_saved": answers_count,
            "questions_created": questions_count,
            "created_at": interview.get("created_at"),
            "completed_at": interview.get("completed_at"),
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Interview diagnostics failed: %s", exc)

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve interview diagnostics",
        ) from exc
