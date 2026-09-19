# PREPLINE Backend

FastAPI backend for PREPLINE, an AI-powered mock interview platform. The
candidate has a real-time spoken conversation with an AI interviewer
(Gemini Live), and receives a scored report at the end.

## 1. Architecture (how it actually works)

```
Browser microphone
  -> raw PCM audio (16kHz, captured via AudioContext, NOT MediaRecorder/WebM)
  -> WebSocket  ws(s)://<backend>/api/live
  -> FastAPI (app/routes/live.py)
  -> Gemini Live session (app/services/gemini_live_service.py)
  -> spoken question + live transcript, streamed back over the same socket
  -> candidate's spoken answer is transcribed by Gemini Live and
     accumulated client-side into a transcript string
  -> POST /api/answers  { interview_id, question_id, transcript, question_text }
  -> app/services/interview_service.py:save_answer_and_evaluate()
       - creates a Firestore "questions" doc for this question if one
         doesn't exist yet (the live flow never calls the separate
         question-bank endpoint below, so this is normal)
       - evaluates the answer (app/services/ai_service.py, Gemini or
         MOCK_AI fallback)
       - saves the answer + evaluation to Firestore
       - auto-completes the interview and generates the final report
         once the last question has been answered
  -> GET /api/reports/{interview_id}  (report.html)
  -> GET /api/users/{user_id}/interviews  (history.html)
```

There is a second, older REST-only path still present for reference /
fallback use (`GET /api/interviews/{id}/question`, `POST /api/transcribe`
+ Whisper) — it works and is exercised by `app/services/whisper_service.py`
+ `question_bank.py`, but the current frontend (`interview.html`) drives
the interview exclusively through the Gemini Live WebSocket described
above. If you want a non-voice / typed-answer mode, the REST path is
already there to build on.

## 2. Requirements

- Python 3.10+
- pip
- A Firebase project with Firestore enabled (see "Firebase setup" below —
  this is required; there is no in-memory database in the current code)
- A Gemini API key for real AI interviews/evaluation (optional if you only
  want MOCK_AI mode, but Gemini Live itself — the voice conversation —
  always requires GEMINI_API_KEY; MOCK_AI only controls answer
  evaluation and report generation, not the live voice session)

## 3. Setup

```
cd Backend
python -m venv venv
```

Activate it:

- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

```
pip install -r requirements.txt
```

## 4. Environment variables

Copy `.env.example` to `.env` and fill in what you need:

```
OPENAI_API_KEY=            # only needed if MOCK_WHISPER=false
GEMINI_API_KEY=            # needed for Gemini Live voice + real AI evaluation

FIREBASE_PROJECT_ID=
FIREBASE_CLIENT_EMAIL=
FIREBASE_PRIVATE_KEY=
FIREBASE_CREDENTIALS_PATH= # alternative to the 3 fields above: path to a
                            # service-account JSON file

MOCK_AI=true                # true = deterministic mock scoring, no Gemini text calls
MOCK_WHISPER=true           # true = mock transcript for the /api/transcribe REST path

FRONTEND_URL=http://127.0.0.1:5500
```

Firebase is always required — the app will start without it (so
`/api/health` and `/docs` still come up), but every route that touches
users/interviews/answers/reports will fail with a clear error until
Firestore credentials are configured.

Gemini Live (the actual spoken interview) requires `GEMINI_API_KEY`
regardless of `MOCK_AI`. `MOCK_AI` only affects *scoring/evaluation*
(the text the AI evaluator sends back), not whether the browser can
have a voice conversation. If `GEMINI_API_KEY` is missing, the
WebSocket will connect but the backend will immediately send back a
`{"type": "error", ...}` message and the frontend shows a clear error
with a retry button rather than hanging.

## 5. Start the backend

```
uvicorn app.main:app --reload
```

or

```
python run.py
```

- API: http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

## 6. Firebase setup

1. Open the Firebase Console and create a project.
2. Enable Firestore Database.
3. Project Settings -> Service accounts -> Generate new private key.
4. Either:
   - paste `project_id` / `client_email` / `private_key` into
     `FIREBASE_PROJECT_ID` / `FIREBASE_CLIENT_EMAIL` / `FIREBASE_PRIVATE_KEY`
     (keep the `\n` escapes in the private key as a single-line env value), or
   - save the downloaded JSON file somewhere on disk and set
     `FIREBASE_CREDENTIALS_PATH` to its path.

Collections used: `users`, `interviews`, `questions`, `answers`, `reports`.

## 7. Frontend

The frontend is static HTML/CSS/JS in `../Frontend`. It reads the backend
URL from `Frontend/config.js`, which auto-detects local development
(`127.0.0.1` / `localhost` -> `http://127.0.0.1:8000`) vs. production
(same-origin by default, or set `PRODUCTION_API_BASE_URL` in that file).
You should not need to hardcode a backend URL anywhere else.

Serve it with any static file server (it needs real HTTP, not `file://`,
for microphone permissions, WebSocket connections, and CORS to work):

```
cd Frontend
python -m http.server 5500
```

Then open http://127.0.0.1:5500.

## 8. CORS

`app/main.py` allows `FRONTEND_URL` plus `http://127.0.0.1:5500` and
`http://localhost:5500` by default. Update `FRONTEND_URL` in `.env` for
other local ports or your production frontend origin.

## 9. Endpoints

```
GET  /api/health
GET  /api/diagnostics/{interview_id}    # no secrets returned

POST /api/users
POST /api/interviews
GET  /api/interviews/{interview_id}
GET  /api/interviews/{interview_id}/question   # REST question-bank flow (not used by the live voice UI)
POST /api/interviews/{interview_id}/complete
GET  /api/users/{user_id}/interviews

WS   /api/live                          # Gemini Live voice interview (primary flow)
POST /api/answers                       # used by both flows
POST /api/transcribe                    # Whisper/mock transcription, for the REST flow

GET  /api/reports/{interview_id}
GET  /api/gemini/test                   # quick Gemini text-API connectivity check
```

## 10. MOCK mode

With `MOCK_AI=true` (the default), answer evaluation and final report
generation use a deterministic local evaluator instead of calling
Gemini's text API — no billing, same JSON shape as the real thing. This
does **not** disable the Gemini Live voice session itself; if you want to
test the UI without any Gemini usage at all, use the REST flow
(`GET /api/interviews/{id}/question` + `POST /api/transcribe` with
`MOCK_WHISPER=true` + `POST /api/answers`) instead of opening
`interview.html`'s live voice mode.

## 11. Security

- Never put `OPENAI_API_KEY`, `GEMINI_API_KEY`, `FIREBASE_PRIVATE_KEY`, or
  `FIREBASE_CLIENT_EMAIL` in frontend code. They only exist in the
  backend's `.env`, which is git-ignored.
- The backend does not return internal exception details to clients for
  unexpected (500) errors.
- There is currently no authentication layer — every interview is
  identified only by the generated `user_id`/`interview_id` stored in the
  browser's `localStorage`. Anyone with an interview ID can read that
  interview's report. Do not use this as-is for data you need to keep
  private between users; add real auth before doing so.

## 12. Error format

```
{ "success": true, ... }
```

```
{ "success": false, "error": { "message": "..." } }
```
or, for validation errors, the FastAPI `detail` field on a 4xx response.
