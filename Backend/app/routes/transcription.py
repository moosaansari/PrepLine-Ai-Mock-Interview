import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.whisper_service import transcribe_audio

router = APIRouter(prefix="/api", tags=["Transcription"])

logger = logging.getLogger(__name__)


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    try:
        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty.",
            )

        transcript = transcribe_audio(
            audio_bytes,
            audio.filename or "answer.webm",
            audio.content_type or "audio/webm",
        )

        return {
            "success": True,
            "transcript": transcript,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Transcription failed: %s", exc)

        raise HTTPException(
            status_code=500,
            detail="Unable to transcribe audio.",
        ) from exc