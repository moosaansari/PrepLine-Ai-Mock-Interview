import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.firebase import get_db
from app.services.ai_service import evaluate_answer
from app.data.question_bank import get_questions

logger = logging.getLogger(__name__)


MIN_INTERVIEW_QUESTIONS = 10
MAX_INTERVIEW_QUESTIONS = 18
DEFAULT_INTERVIEW_QUESTIONS = 12


def _now():
    return datetime.now(timezone.utc)


def _get_interview(
    interview_id: str,
) -> Optional[Dict[str, Any]]:

    db = get_db()

    doc = (
        db.collection("interviews")
        .document(interview_id)
        .get()
    )

    if not doc.exists:
        return None

    data = doc.to_dict() or {}
    data["id"] = doc.id

    return data


def get_interview(
    interview_id: str,
) -> Optional[Dict[str, Any]]:

    return _get_interview(
        interview_id
    )


def _update_interview(
    interview_id: str,
    updates: Dict[str, Any],
) -> Dict[str, Any]:

    db = get_db()

    ref = (
        db.collection("interviews")
        .document(interview_id)
    )

    ref.update(updates)

    interview = _get_interview(
        interview_id
    )

    if interview is None:
        raise ValueError(
            "Interview not found."
        )

    return interview


def _get_answers(
    interview_id: str,
) -> List[Dict[str, Any]]:

    db = get_db()

    docs = (
        db.collection("answers")
        .where(
            "interview_id",
            "==",
            interview_id,
        )
        .stream()
    )

    answers = []

    for doc in docs:

        data = doc.to_dict() or {}
        data["id"] = doc.id

        answers.append(data)

    answers.sort(
        key=lambda item: item.get(
            "question_number",
            0,
        )
    )

    return answers


def _get_previous_answers(
    interview_id: str,
) -> List[Dict[str, Any]]:

    return _get_answers(
        interview_id
    )


def create_interview(
    data: Dict[str, Any],
) -> Dict[str, Any]:

    db = get_db()

    user_id = data.get("user_id")

    if not user_id:
        raise ValueError(
            "user_id is required."
        )

    user_doc = (
        db.collection("users")
        .document(user_id)
        .get()
    )

    if not user_doc.exists:
        raise ValueError(
            "User not found."
        )

    interview_ref = (
        db.collection("interviews")
        .document()
    )

    interview_id = interview_ref.id

                                                                              
                                                                                  
    user_data = user_doc.to_dict() or {}

    role = data.get("role") or user_data.get("target_role") or "Software Engineer"
    experience = (
        data.get("experience")
        or user_data.get("experience_level")
        or "Fresher"
    )

    interview_type = data.get(
        "interview_type",
        "Technical",
    )

    difficulty = str(
        data.get(
            "difficulty",
            "medium",
        )
    ).lower()

    if difficulty == "balanced":
        difficulty = "medium"

    if difficulty not in {
        "easy",
        "medium",
        "hard",
    }:
        difficulty = "medium"

    total_questions = data.get(
        "total_questions",
        data.get(
            "number_of_questions",
            DEFAULT_INTERVIEW_QUESTIONS,
        ),
    )

    try:
        total_questions = int(
            total_questions
        )
    except (
        TypeError,
        ValueError,
    ):
        total_questions = DEFAULT_INTERVIEW_QUESTIONS

    if not MIN_INTERVIEW_QUESTIONS <= total_questions <= MAX_INTERVIEW_QUESTIONS:
        raise ValueError(
            f"total_questions must be between {MIN_INTERVIEW_QUESTIONS} and "
            f"{MAX_INTERVIEW_QUESTIONS}."
        )

    now = _now()

    interview = {
        "id": interview_id,
        "user_id": user_id,
        "role": role,
        "experience": experience,
        "interview_type": interview_type,
        "difficulty": difficulty,
        "total_questions": total_questions,
        "current_question_number": 0,
        "current_question_id": None,
        "current_question_text": None,
        "status": "active",
        "language": data.get(
            "language",
            "English",
        ),
        "interviewer_style": data.get(
            "interviewer_style",
            "Professional",
        ),
        "communication_context": data.get(
            "communication_context",
            "neutral",
        ),
        "created_at": now,
        "updated_at": now,
    }

    interview_ref.set(
        interview
    )

    logger.info(
        "Interview created: %s",
        interview_id,
    )

    return interview


def _difficulty_for_interview(
    difficulty: str,
    question_number: int,
) -> str:

    difficulty = (
        difficulty or "medium"
    ).lower()

    if difficulty in {
        "easy",
        "beginner",
    }:
        return "beginner"

    if difficulty in {
        "hard",
        "advanced",
    }:
        return "advanced"

    if difficulty == "medium":

        if question_number <= 2:
            return "beginner"

        if question_number <= 5:
            return "intermediate"

        return "advanced"

    return "intermediate"


def _select_question(
    role: str,
    difficulty: str,
    question_number: int,
) -> Dict[str, Any]:

    all_questions = get_questions(
        role,
        "balanced",
    )

    if not all_questions:
        raise ValueError(
            f"No questions found for role: {role}"
        )

    target_level = (
        _difficulty_for_interview(
            difficulty,
            question_number,
        )
    )

    matching = [
        item
        for item in all_questions
        if item.get(
            "difficulty",
            "",
        ).lower()
        == target_level
    ]

    if not matching:
        matching = all_questions

    index = (
        question_number - 1
    ) % len(matching)

    return matching[index]


def generate_question(
    interview_id: str,
) -> Dict[str, Any]:

    db = get_db()

    interview = _get_interview(
        interview_id
    )

    if interview is None:
        raise ValueError(
            "Interview not found."
        )

    if interview.get("status") == "completed":
        raise ValueError(
            "Interview is already completed."
        )

    current_number = int(
        interview.get(
            "current_question_number",
            0,
        )
    )

    total_questions = int(
        interview.get(
            "total_questions",
            DEFAULT_INTERVIEW_QUESTIONS,
        )
    )

    if current_number >= total_questions:

        complete_interview(
            interview_id
        )

        raise ValueError(
            "Interview has reached the maximum number of questions."
        )

    question_number = (
        current_number + 1
    )

    role = interview.get(
        "role",
        "Software Engineer",
    )

    difficulty = interview.get(
        "difficulty",
        "medium",
    )

    selected = _select_question(
        role=role,
        difficulty=difficulty,
        question_number=question_number,
    )

    question_text = selected.get(
        "question",
        "",
    )

    if not question_text:
        raise ValueError(
            "Question text is empty."
        )

    question_id = (
        f"{interview_id}-q{question_number}"
    )

    question_data = {
        "id": question_id,
        "interview_id": interview_id,
        "number": question_number,
        "text": question_text,
        "type": interview.get(
            "interview_type",
            "Technical",
        ),
        "difficulty": selected.get(
            "difficulty",
            "Intermediate",
        ),
        "role": role,
        "created_at": _now(),
    }

    (
        db.collection("questions")
        .document(question_id)
        .set(question_data)
    )

    _update_interview(
        interview_id,
        {
            "current_question_number":
                question_number,
            "current_question_id":
                question_id,
            "current_question_text":
                question_text,
            "updated_at":
                _now(),
        },
    )

    logger.info(
        "Question generated: %s",
        question_id,
    )

    return question_data


def _find_existing_answer(
    interview_id: str,
    question_id: str,
) -> Optional[Dict[str, Any]]:

    db = get_db()

    existing = (
        db.collection("answers")
        .where(
            "interview_id",
            "==",
            interview_id,
        )
        .stream()
    )

    for doc in existing:
        data = doc.to_dict() or {}
        if data.get("question_id") == question_id:
            data["id"] = doc.id
            return data

    return None


def save_answer_and_evaluate(
    interview_id: str,
    question_id: str,
    question_number: Optional[int],
    transcript: str,
    question_text: Optional[str] = None,
) -> Dict[str, Any]:

    db = get_db()

    interview = _get_interview(
        interview_id
    )

    if interview is None:
        raise ValueError(
            "Interview not found."
        )

    if interview.get("status") == "completed":

                                          
                                                
        existing_answer = (
            _find_existing_answer(
                interview_id,
                question_id,
            )
        )

        if existing_answer:
            return existing_answer

        raise ValueError(
            "Interview is already completed."
        )

    total_questions = int(interview.get("total_questions", DEFAULT_INTERVIEW_QUESTIONS))
    current_number = int(interview.get("current_question_number", 0))

    if question_number is not None and question_number > total_questions:
        raise ValueError("Question number exceeds the interview limit.")

    question_ref = (
        db.collection("questions")
        .document(question_id)
    )

    question_doc = question_ref.get()

    if question_doc.exists:
        question = question_doc.to_dict() or {}
    else:
                                                           
                          
                                                          
                                                             
                                                      
                                                            
                                                               
         
                                                            
                                                           
                                                       
                                                        
                                                           
                                                          
                                                           
                    
                                                           

                                                                            
                                                                            
                                                                   
        resolved_question_number = question_number or current_number or 1

        resolved_text = (
            (question_text or "").strip()
            or (interview.get("current_question_text") or "").strip()
        )

        if not resolved_text:
            raise ValueError(
                "Question not found and no question text was provided."
            )

        question = {
            "id": question_id,
            "interview_id": interview_id,
            "number": resolved_question_number,
            "text": resolved_text,
            "type": interview.get("interview_type", "Technical"),
            "difficulty": interview.get("difficulty", "Intermediate"),
            "role": interview.get("role", "Software Engineer"),
            "source": "gemini_live",
            "created_at": _now(),
        }

        question_ref.set(question)

                                                                  
                                                                   
                                                               
        if resolved_question_number > current_number:
            interview = _update_interview(
                interview_id,
                {
                    "current_question_number": resolved_question_number,
                    "current_question_id": question_id,
                    "current_question_text": resolved_text,
                    "updated_at": _now(),
                },
            )
            current_number = resolved_question_number

    transcript = (
        transcript or ""
    ).strip()

    if not transcript:
        raise ValueError(
            "Answer transcript cannot be empty."
        )

                                                       
                
                                                  
                                                
                                                       

    existing_answer = (
        _find_existing_answer(
            interview_id,
            question_id,
        )
    )

    if existing_answer:

        logger.info(
            "Returning existing answer for question: %s",
            question_id,
        )

        return existing_answer

    evaluation = evaluate_answer(
        question=question.get(
            "text",
            "",
        ),
        answer=transcript,
        role=interview.get(
            "role",
            "Software Engineer",
        ),
        language=interview.get(
            "language",
            "English",
        ),
        communication_context=interview.get(
            "communication_context",
            "neutral",
        ),
    )

    answer_ref = (
        db.collection("answers")
        .document()
    )

    answer_data = {
        "id": answer_ref.id,
        "interview_id": interview_id,
        "question_id": question_id,
        "question_number": question.get(
            "number",
            1,
        ),
        "question_text": question.get(
            "text",
            "",
        ),
        "transcript": transcript,
        "evaluation": evaluation,
        "created_at": _now(),
    }

    answer_ref.set(
        answer_data
    )

                                                                          
                                                                        
                            
    current_number = max(
        current_number,
        int(question.get("number", 0) or 0),
    )

                                                       
                                                    
                                                       

    if current_number >= total_questions:

        try:
            complete_interview(
                interview_id
            )
        except Exception as exc:

            logger.exception(
                "Final report generation failed after final answer: %s",
                exc,
            )

    return answer_data


def complete_interview(
    interview_id: str,
) -> Dict[str, Any]:

    db = get_db()

    interview = get_interview(
        interview_id
    )

    if interview is None:
        raise ValueError(
            "Interview not found."
        )

                                                       
                        
                                                    
                                                       

    if interview.get("status") == "completed":

        logger.info(
            "Interview already completed: %s",
            interview_id,
        )

        return interview

    answers = _get_previous_answers(
        interview_id
    )

    role = interview.get(
        "role",
        "Software Engineer",
    )

                                                       
                              
                                                       

    try:
        from app.services.ai_service import generate_final_report
        final_report = generate_final_report(
            role=role,
            interview_answers=answers,
            language=interview.get("language", "English"),
            communication_context=interview.get("communication_context", "neutral"),
        )
    except Exception as exc:
        logger.exception("Final interview report generation failed: %s", exc)
                                                                                   
        final_report = {}

                                                       
                                                         
                                                         
                                                       

    completed = _update_interview(
        interview_id,
        {
            "status": "completed",
            "completed_at": _now(),
            "final_report": final_report,
            "updated_at": _now(),
        },
    )

                                                                             
                                                                    
                                                                            
    if final_report:
        try:
            report_payload = {
                "interview_id": interview_id,
                **final_report,
                "created_at": _now(),
                "updated_at": _now(),
            }
            report_ref = db.collection("reports").document(interview_id)
            report_ref.set(report_payload, merge=True)
        except Exception:
            logger.exception("Could not persist final report document: %s", interview_id)

    return completed


def get_user_interviews(
    user_id: str,
) -> List[Dict[str, Any]]:

    db = get_db()

    user_doc = (
        db.collection("users")
        .document(user_id)
        .get()
    )

    if not user_doc.exists:
        raise ValueError(
            "User not found."
        )

    docs = (
        db.collection("interviews")
        .where(
            "user_id",
            "==",
            user_id,
        )
        .stream()
    )

    interviews = []

    for doc in docs:

        data = doc.to_dict() or {}
        data["id"] = doc.id

        interviews.append(
            data
        )

    interviews.sort(
        key=lambda item: item.get(
            "created_at",
            datetime.min.replace(
                tzinfo=timezone.utc
            ),
        ),
        reverse=True,
    )

    return interviews
