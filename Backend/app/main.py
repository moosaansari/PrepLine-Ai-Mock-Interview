import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.routes import (
    answers,
    interviews,
    reports,
    transcription,
    users,
    gemini,
    live,
    auth,
    diagnostics,
    sessions,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PREPLINE API",
    description="AI-powered mock interview backend",
    version="1.0.0",
)


allowed_origins = list(
    {
        settings.FRONTEND_URL,
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
                                                                        
                                                                    
                                                                       
                                                                       
                                                                  
    try:
        initialize_firebase()
        logger.info("PREPLINE backend started with Firebase connected.")
    except Exception as exc:
        logger.warning(
            "PREPLINE backend started WITHOUT Firebase (will retry lazily "
            "on first use). Set FIREBASE_PROJECT_ID / FIREBASE_CLIENT_EMAIL "
            "/ FIREBASE_PRIVATE_KEY in .env to enable persistence. "
            "Reason: %s",
            exc,
        )


@app.get("/api/health")
def health():
    return {
        "success": True,
        "message": "Prepline backend is running",
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "message": "Invalid request data.",
                "details": [
                    {
                        "field": ".".join(
                            str(item)
                            for item in error.get("loc", [])
                            if item != "body"
                        ),
                        "message": error.get(
                            "msg",
                            "Invalid value.",
                        ),
                    }
                    for error in exc.errors()
                ],
            },
        },
    )


@app.exception_handler(404)
async def not_found_handler(
    request: Request,
    exc,
):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {
                "message": "Resource not found.",
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled server error: %s",
        exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "message": "Internal server error.",
            },
        },
    )


logger.info("Registering API routers...")
app.include_router(auth.router)
logger.info("  ✓ auth")
app.include_router(users.router)
logger.info("  ✓ users")
app.include_router(interviews.router)
logger.info("  ✓ interviews")
app.include_router(transcription.router)
logger.info("  ✓ transcription")
app.include_router(answers.router)
logger.info("  ✓ answers")
app.include_router(reports.router)
logger.info("  ✓ reports")
app.include_router(gemini.router)
logger.info("  ✓ gemini")
app.include_router(live.router)
logger.info("  ✓ live")
app.include_router(diagnostics.router)
logger.info("  ✓ diagnostics")
app.include_router(sessions.router)
logger.info("  ✓ sessions")
logger.info("All routers registered successfully.")