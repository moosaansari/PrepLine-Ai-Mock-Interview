import logging
import time

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/mp4",
    "video/webm",
}

                     
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.0                                   


def transcribe_audio(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
) -> str:
    """
    Transcribe audio using ElevenLabs or mock mode.

    Args:
        audio_bytes: Raw audio file bytes
        filename: Original filename for reference
        content_type: MIME type of audio (e.g., "audio/webm")

    Returns:
        Transcribed text

    Raises:
        RuntimeError: If transcription fails after retries
    """
    if settings.MOCK_WHISPER:
        logger.info("Transcription completed using MOCK_WHISPER.")
        return (
            "This is a demo interview answer. "
            "I would approach the problem by first understanding "
            "the requirements, then designing the API, validating "
            "the input, handling errors, and testing the solution."
        )

    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is required when MOCK_WHISPER=false."
        )

                                         
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                "ElevenLabs transcription attempt %d/%d",
                attempt + 1,
                MAX_RETRIES,
            )

            response = requests.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={
                    "xi-api-key": settings.ELEVENLABS_API_KEY,
                },
                files={
                    "file": (
                        filename or "answer.webm",
                        audio_bytes,
                        content_type or "audio/webm",
                    ),
                },
                data={
                    "model_id": settings.ELEVENLABS_STT_MODEL,
                },
                timeout=60,
            )

                                 
            if attempt > 0:
                logger.info("ElevenLabs retry succeeded on attempt %d", attempt + 1)

            response.raise_for_status()

            payload = response.json()
            transcript = (payload.get("text") or "").strip()

            if not transcript:
                raise RuntimeError("ElevenLabs returned an empty transcript.")

            logger.info(
                "Transcription completed using ElevenLabs %s.",
                settings.ELEVENLABS_STT_MODEL,
            )

            return transcript

        except requests.Timeout as exc:
            last_error = exc
            logger.warning(
                "ElevenLabs request timeout on attempt %d: %s",
                attempt + 1,
                exc,
            )

            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_SECONDS * (2 ** attempt)
                logger.info("Retrying after %f seconds...", wait_time)
                time.sleep(wait_time)

        except requests.ConnectionError as exc:
            last_error = exc
            logger.warning(
                "ElevenLabs connection error on attempt %d: %s",
                attempt + 1,
                exc,
            )

            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_SECONDS * (2 ** attempt)
                logger.info("Retrying after %f seconds...", wait_time)
                time.sleep(wait_time)

        except requests.HTTPError as exc:
                                                   
            if exc.response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                last_error = exc
                logger.warning(
                    "ElevenLabs server error (%d) on attempt %d: %s",
                    exc.response.status_code,
                    attempt + 1,
                    exc,
                )

                wait_time = RETRY_BACKOFF_SECONDS * (2 ** attempt)
                logger.info("Retrying after %f seconds...", wait_time)
                time.sleep(wait_time)
            else:
                                              
                logger.error(
                    "ElevenLabs HTTP error (%d) on attempt %d: %s",
                    exc.response.status_code,
                    attempt + 1,
                    exc,
                )
                raise RuntimeError(
                    f"ElevenLabs API error ({exc.response.status_code}): "
                    f"{exc.response.text[:100]}"
                ) from exc

        except Exception as exc:
            last_error = exc
            logger.error(
                "ElevenLabs transcription error on attempt %d: %s",
                attempt + 1,
                exc,
            )

                                           
            raise RuntimeError("Unable to transcribe audio with ElevenLabs.") from exc

                           
    logger.error(
        "ElevenLabs transcription failed after %d attempts",
        MAX_RETRIES,
    )

    raise RuntimeError(
        f"Unable to transcribe audio with ElevenLabs after {MAX_RETRIES} attempts: "
        f"{str(last_error)[:100]}"
    ) from last_error

