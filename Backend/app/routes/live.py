import asyncio
import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.rate_limit import live_connection_limiter
from app.services.gemini_live_service import (
    connect_live_session,
    send_audio,
    send_text,
)

router = APIRouter(prefix="/api", tags=["Gemini Live"])

logger = logging.getLogger(__name__)


@router.websocket("/live")
async def gemini_live(websocket: WebSocket):
    client_ip = websocket.client.host if websocket.client else "unknown"
    if not live_connection_limiter.allow(client_ip):
        await websocket.close(code=1013, reason="Too many live connections. Please wait a minute and try again.")
        return

    await websocket.accept()

    sender_task = None
    receiver_task = None
    browser_task = None

    audio_queue = asyncio.Queue(maxsize=200)
    stop_event = asyncio.Event()
    last_ping_time = asyncio.get_event_loop().time()
    heartbeat_task = None
    next_question_in_flight = False

    try:
                                                                   
                        
                                                                   

        initial_message = await websocket.receive_text()

        try:
            config = json.loads(initial_message)
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid interview configuration.",
            })
            return

        role = config.get(
            "role",
            "Software Engineer",
        )

        difficulty = config.get(
            "difficulty",
            "Intermediate",
        )

        try:
            total_questions = int(
                config.get(
                    "total_questions",
                    12,
                )
            )
        except (TypeError, ValueError):
            total_questions = 12

        # PREPLINE supports any interview length from 5 to 18 questions.
        total_questions = max(5, min(total_questions, 18))

        try:
            current_question_number = int(
                config.get("current_question_number", 1)
            )
        except (TypeError, ValueError):
            current_question_number = 1
        current_question_number = max(1, current_question_number)

        language = str(
            config.get("language", "English")
        ).strip() or "English"

        communication_context = str(
            config.get("communication_context", "neutral")
        ).strip() or "neutral"

        logger.info(
            "Starting Gemini Live interview: "
            "role=%s difficulty=%s questions=%s",
            role,
            difficulty,
            total_questions,
        )

                                                                   
                           
                                                                   

        async with connect_live_session(
            role=role,
            difficulty=difficulty,
            total_questions=total_questions,
            language=language,
            communication_context=communication_context,
        ) as (client, session):

            await websocket.send_json({
                "type": "connected",
                "message": "Gemini Live connected.",
            })

            logger.info(
                "Gemini Live session connected."
            )

                                                                   
                                 
                                                                   

            async def send_to_gemini_loop():

                audio_count = 0

                while not stop_event.is_set():

                    item = await audio_queue.get()

                    if item is None:
                        break

                    item_type = item[0]

                    try:

                                                                   
                               
                                                                   

                        if item_type == "audio":

                            audio_bytes = item[1]
                            sample_rate = item[2]

                            if not audio_bytes:
                                continue

                            await send_audio(
                                session,
                                audio_bytes,
                                sample_rate=sample_rate,
                            )

                            audio_count += 1

                            if audio_count % 20 == 0:

                                logger.info(
                                    "Sent %s audio chunks to Gemini.",
                                    audio_count,
                                )

                                                                   
                                        
                                                                   

                        elif item_type == "text":

                            text = item[1]

                            if text:

                                await send_text(
                                    session,
                                    text,
                                )

                    except asyncio.CancelledError:
                        raise

                    except Exception as exc:

                        logger.exception(
                            "Gemini input sender failed: %s",
                            exc,
                        )

                        try:

                            await websocket.send_json({
                                "type": "error",
                                "message": (
                                    "Audio connection to Gemini failed: "
                                    f"{exc}"
                                ),
                            })

                        except Exception:
                            pass

                        stop_event.set()
                        break

                                                                   
                               
                                                                   

            async def receive_from_gemini():
                nonlocal next_question_in_flight

                try:

                                                                             
                                                                         
                                                                             
                                                                         
                                
                    while not stop_event.is_set():
                        async for response in session.receive():

                            server_content = getattr(
                                response,
                                "server_content",
                                None,
                            )

                            if server_content is None:
                                continue

                                                                       
                                          
                                                                       

                            interrupted = getattr(
                                server_content,
                                "interrupted",
                                False,
                            )

                            if interrupted:

                                logger.info(
                                    "Gemini interrupted current response."
                                )

                                try:

                                    await websocket.send_json({
                                        "type": "interrupted",
                                    })

                                except Exception:

                                    stop_event.set()
                                    break

                                                                       
                                                     
                                                                       

                            input_transcription = getattr(
                                server_content,
                                "input_transcription",
                                None,
                            )

                            if input_transcription:

                                text = getattr(
                                    input_transcription,
                                    "text",
                                    "",
                                )

                                if text:

                                    logger.info(
                                        "Candidate: %s",
                                        text,
                                    )

                                    try:

                                        await websocket.send_json({
                                            "type": "input_transcription",
                                            "text": text,
                                        })

                                    except Exception:

                                        stop_event.set()
                                        break

                                                                       
                                              
                                                                       

                            output_transcription = getattr(
                                server_content,
                                "output_transcription",
                                None,
                            )

                            if output_transcription:

                                text = getattr(
                                    output_transcription,
                                    "text",
                                    "",
                                )

                                if text:

                                    logger.info(
                                        "AI: %s",
                                        text,
                                    )

                                    try:

                                        await websocket.send_json({
                                            "type": "output_transcription",
                                            "text": text,
                                        })

                                    except Exception:

                                        stop_event.set()
                                        break

                                                                       
                                      
                                                                       

                            model_turn = getattr(
                                server_content,
                                "model_turn",
                                None,
                            )

                            if model_turn:

                                parts = getattr(
                                    model_turn,
                                    "parts",
                                    [],
                                )

                                for part in parts:

                                    inline_data = getattr(
                                        part,
                                        "inline_data",
                                        None,
                                    )

                                    if inline_data is None:
                                        continue

                                    audio_data = getattr(
                                        inline_data,
                                        "data",
                                        None,
                                    )

                                    if not audio_data:
                                        continue

                                    if isinstance(
                                        audio_data,
                                        str,
                                    ):

                                        try:

                                            audio_data = (
                                                base64.b64decode(
                                                    audio_data
                                                )
                                            )

                                        except Exception:

                                            logger.exception(
                                                "Could not decode Gemini audio."
                                            )

                                            continue

                                    encoded_audio = (
                                        base64.b64encode(
                                            audio_data
                                        ).decode("ascii")
                                    )

                                    try:

                                        await websocket.send_json({
                                            "type": "audio",
                                            "data": encoded_audio,
                                            "sample_rate": 24000,
                                        })

                                    except Exception:

                                        stop_event.set()
                                        break

                                                                       
                                           
                                                                       

                            turn_complete = getattr(
                                server_content,
                                "turn_complete",
                                False,
                            )

                            if turn_complete:
                                next_question_in_flight = False
                                logger.info("Gemini turn complete.")

                                try:

                                    await websocket.send_json({
                                        "type": "turn_complete",
                                    })

                                except Exception:

                                    stop_event.set()
                                    break

                        if not stop_event.is_set():
                            logger.info(
                                "Gemini turn receive loop ended; keeping Live session open."
                            )

                except asyncio.CancelledError:
                    raise

                except Exception as exc:

                    logger.exception(
                        "Gemini receiver failed: %s",
                        exc,
                    )

                    try:

                        await websocket.send_json({
                            "type": "error",
                            "message": (
                                "Gemini response connection failed: "
                                f"{exc}"
                            ),
                        })

                    except Exception:
                        pass

                    stop_event.set()

                                                                   
                                   
                                                                   

            async def heartbeat_loop():
                """
                Send periodic ping messages to keep WebSocket alive
                and detect disconnections early.
                """
                nonlocal last_ping_time

                try:
                    while not stop_event.is_set():
                        await asyncio.sleep(15)                         

                        if stop_event.is_set():
                            break

                        try:
                            current_time = asyncio.get_event_loop().time()
                            await websocket.send_json({
                                "type": "ping",
                                "timestamp": current_time,
                            })
                            last_ping_time = current_time
                            logger.debug("Heartbeat ping sent")

                        except Exception as exc:
                            logger.warning("Heartbeat ping failed: %s", exc)
                            stop_event.set()
                            break

                except asyncio.CancelledError:
                    raise

                except Exception as exc:
                    logger.exception("Heartbeat loop failed: %s", exc)
                    stop_event.set()

                                                                   
                               
                                                                   

            async def receive_from_browser():

                try:

                    while not stop_event.is_set():

                        message = await websocket.receive()

                        if (
                            message.get("type")
                            == "websocket.disconnect"
                        ):

                            logger.info(
                                "Browser disconnected."
                            )

                            stop_event.set()
                            break

                        text_data = message.get(
                            "text"
                        )

                        if not text_data:
                            continue

                        try:

                            data = json.loads(
                                text_data
                            )

                        except json.JSONDecodeError:

                            logger.warning(
                                "Received invalid JSON from browser."
                            )

                            continue

                        message_type = data.get(
                            "type"
                        )

                                                                   
                               
                                                                   

                        if message_type == "audio":

                            audio_base64 = data.get(
                                "data",
                                "",
                            )

                            if not audio_base64:
                                continue

                            try:

                                audio_bytes = (
                                    base64.b64decode(
                                        audio_base64,
                                    )
                                )

                                if not audio_bytes:
                                    continue

                                sample_rate = int(
                                    data.get(
                                        "sample_rate",
                                        16000,
                                    )
                                )

                                if sample_rate <= 0:
                                    sample_rate = 16000

                                await audio_queue.put(
                                    (
                                        "audio",
                                        audio_bytes,
                                        sample_rate,
                                    )
                                )

                            except Exception as exc:

                                logger.warning(
                                    "Invalid audio packet: %s",
                                    exc,
                                )

                                                                   
                              
                                                                   

                        elif message_type == "text":

                            text = data.get(
                                "text",
                                "",
                            ).strip()

                            if text:

                                await audio_queue.put(
                                    (
                                        "text",
                                        text,
                                    )
                                )

                                                                   
                                       
                                                                   

                        elif message_type == "next_question":

                                                                             
                                                                             
                                                                             
                                                                
                            logger.warning(
                                "Ignoring legacy next_question command; Gemini Live advances automatically."
                            )

                        elif message_type == "manual_next_question":

                                                                                
                                                                                
                                                             
                            logger.info("Manual fallback requested the next question.")
                            await audio_queue.put((
                                "text",
                                f"""
The candidate has submitted a typed answer for the previous question.
Continue the interview with exactly ONE next question.
Selected role: {role}
Difficulty: {difficulty}
Maximum questions: {total_questions}
Base the next question on the candidate's answer and do not use a predefined question list.
Do not evaluate the candidate aloud. Ask the next question now, then stop and wait.
""",
                            ))

                                                                   
                                          
                                                                   

                        elif message_type == "submit":

                            logger.info(
                                "Interview submitted by browser."
                            )

                            await audio_queue.put(
                                (
                                    "text",
                                    """
The candidate has submitted the interview.

End the interview now.

Briefly say that the PREPLINE interview is complete.

Do not provide the detailed evaluation aloud.

Keep the closing short and professional.
""",
                                )
                            )

                                                                   
                            await asyncio.sleep(2)

                            stop_event.set()
                            break

                                                                   
                                                 
                                                                   

                        elif message_type == "pong":

                            logger.debug(
                                "Received pong from browser."
                            )
                                                        

                                                                   
                             
                                                                   

                        elif message_type == "end":

                            logger.info(
                                "Interview ended by browser."
                            )

                            stop_event.set()
                            break

                except WebSocketDisconnect:

                    logger.info(
                        "Browser WebSocket disconnected."
                    )

                    stop_event.set()

                except asyncio.CancelledError:
                    raise

                except Exception as exc:

                    logger.exception(
                        "Browser receiver failed: %s",
                        exc,
                    )

                    stop_event.set()

                                                                   
                         
                                                                   

            sender_task = asyncio.create_task(
                send_to_gemini_loop(),
                name="gemini-sender",
            )

            receiver_task = asyncio.create_task(
                receive_from_gemini(),
                name="gemini-receiver",
            )

            browser_task = asyncio.create_task(
                receive_from_browser(),
                name="browser-receiver",
            )

            heartbeat_task = asyncio.create_task(
                heartbeat_loop(),
                name="heartbeat",
            )

                                                                   
                                                     
                                                                   

            if current_question_number <= 1:
                await audio_queue.put(
                    (
                        "text",
                        (
                            f"""
Begin the interview now.

Selected role: {role}
Difficulty: {difficulty}
Maximum questions: {total_questions}

You MUST interview specifically for the selected role.

Speak first.

Briefly introduce yourself as the PREPLINE AI interviewer.

Then ask the first technical interview question.

Do not wait for the candidate to speak first.

Ask only ONE question.
"""
                        ),
                    )
                )
                logger.info("Initial interview instruction sent to Gemini.")
            else:
                await audio_queue.put(
                    (
                        "text",
                        (
                            f"""
This is a RECONNECT to an interview already in progress.

Selected role: {role}
Difficulty: {difficulty}
Maximum questions: {total_questions}
Current question number: {current_question_number}

Do NOT introduce yourself.
Do NOT say "Hello, I'm PREPLINE".
Do NOT restart the interview.
Do NOT ask question 1.

Continue the current interview naturally from question {current_question_number}.
If the current question has not yet been answered, repeat ONLY the current question clearly.
If the candidate has already answered and the application is moving forward, wait for the next instruction.
"""
                        ),
                    )
                )
                logger.info(
                    "Reconnect continuation instruction sent for question %s.",
                    current_question_number,
                )

                                                                   
                  
                                                                   

            tasks = [
                sender_task,
                receiver_task,
                browser_task,
                heartbeat_task,
            ]

            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            logger.warning(
                "Live task(s) ended: %s",
                ", ".join(task.get_name() for task in done),
            )

            for task in done:

                try:
                    await task

                except asyncio.CancelledError:
                    pass

                except Exception as exc:

                    logger.exception(
                        "Live task ended with error: %s",
                        exc,
                    )

            stop_event.set()

            for task in pending:
                task.cancel()

            for task in pending:

                try:
                    await task

                except asyncio.CancelledError:
                    pass

                except Exception:
                    pass

    except WebSocketDisconnect:

        logger.info(
            "Gemini Live WebSocket disconnected."
        )

    except Exception as exc:

        logger.exception(
            "Gemini Live WebSocket error: %s",
            exc,
        )

        try:

            await websocket.send_json({
                "type": "error",
                "message": str(exc),
            })

        except Exception:
            pass

    finally:

        stop_event.set()

        try:
            await audio_queue.put(None)
        except Exception:
            pass

        for task in (
            sender_task,
            receiver_task,
            browser_task,
            heartbeat_task,
        ):

            if task and not task.done():
                task.cancel()

        for task in (
            sender_task,
            receiver_task,
            browser_task,
            heartbeat_task,
        ):

            if task:

                try:
                    await task

                except asyncio.CancelledError:
                    pass

                except Exception:
                    pass

        try:
            await websocket.close()
        except Exception:
            pass

        logger.info(
            "Gemini Live session cleaned up."
        )