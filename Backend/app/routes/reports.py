from fastapi import APIRouter, HTTPException, Request

from app.core.auth import get_optional_auth_user
from app.core.firebase import get_document, list_documents
from app.services.report_service import generate_report

router = APIRouter(prefix="/api", tags=["Reports"])


def _public_report(report: dict, interview_id: str) -> dict:
    public = {
        "interview_id": interview_id,
        "role": report.get("role", ""),
        "overall_score": report.get("overall_score"),
        "technical_score": report.get("technical_score"),
        "communication_score": report.get("communication_score"),
        "confidence_score": report.get("confidence_score"),
        "clarity_score": report.get("clarity_score"),
        "professionalism_score": report.get("professionalism_score"),
        "communication_style": report.get("communication_style"),
        "delivery_style": report.get(
            "delivery_style",
            report.get("communication_style"),
        ),
        "confidence_level": report.get("confidence_level"),
        "nervousness_level": report.get("nervousness_level"),
        "tone": report.get("tone"),
        "aggression_level": report.get("aggression_level"),
        "filler_words": report.get("filler_words", []),
        "strengths": report.get("strengths", []),
        "weaknesses": report.get(
            "weaknesses",
            report.get("improvement_areas", []),
        ),
        "suggestions": report.get(
            "suggestions",
            report.get("action_plan", []),
        ),
        "summary": report.get("summary", report.get("interviewer_summary")),
        "communication_feedback": report.get(
            "communication_feedback",
            "",
        ),
        "confidence_feedback": report.get(
            "confidence_feedback",
            "",
        ),
        "technical_feedback": report.get(
            "technical_feedback",
            "",
        ),
        "interviewer_summary": report.get(
            "interviewer_summary",
            report.get("summary", ""),
        ),
        "action_plan": report.get(
            "action_plan",
            report.get("suggestions", []),
        ),
    }

                                                                                                          
    for v2_key in ("content_quality", "communication", "contextual_interpretation"):
        if isinstance(report.get(v2_key), dict):
            public[v2_key] = report[v2_key]

    return public


def _question_breakdown(interview_id: str) -> list[dict]:
    answers = list_documents(
        "answers",
        filters=[{"field": "interview_id", "operator": "==", "value": interview_id}],
    )
    answers.sort(key=lambda item: item.get("question_number", 0))

    breakdown = []
    for answer in answers:
        evaluation = answer.get("evaluation")
        evaluation = evaluation if isinstance(evaluation, dict) else {}
        cq = evaluation.get("content_quality") if isinstance(evaluation.get("content_quality"), dict) else {}
        cm = evaluation.get("communication") if isinstance(evaluation.get("communication"), dict) else {}
        ci = evaluation.get("contextual_interpretation") if isinstance(evaluation.get("contextual_interpretation"), dict) else {}

        breakdown.append({
            "question_number": answer.get("question_number", 0),
            "question": answer.get("question_text", ""),
            "answer": answer.get("transcript", ""),
            "score": evaluation.get("overall_score", evaluation.get("score")),
            "content_score": cq.get("score", evaluation.get("technical_score")),
            "communication_score": cm.get("score", evaluation.get("communication_score")),
            "confidence": cm.get("confidence", evaluation.get("confidence_score")),
            "clarity": cm.get("clarity", evaluation.get("clarity_score")),
            "delivery_style": evaluation.get("delivery_style", evaluation.get("communication_style")),
            "observed_delivery": cm.get("observed_delivery", ""),
            "contextual_interpretation": ci,
            "feedback": evaluation.get("feedback", evaluation.get("overall_feedback")),
        })

    return breakdown


@router.get("/reports/{interview_id}")
def get_report(interview_id: str, request: Request):
    try:
        interview = get_document("interviews", interview_id)
        auth_user = get_optional_auth_user(request)
        if auth_user and interview and interview.get("user_id") != str(auth_user["uid"]):
            raise HTTPException(status_code=403, detail="You do not have access to this report.")

        if not interview:
            raise HTTPException(
                status_code=404,
                detail="Interview not found.",
            )

        report = get_document("reports", interview_id)

        if not report:
                                                     
            report = generate_report(interview_id)

        public_report = _public_report(report, interview_id)
        public_report["role"] = interview.get("role", "Technical interview")
        public_report["question_breakdown"] = _question_breakdown(interview_id)
        public_report["summary_meta"] = {
            "role": interview.get("role", ""),
            "difficulty": interview.get("difficulty", ""),
            "interview_type": interview.get("interview_type", ""),
            "total_questions": interview.get("total_questions"),
            "completed_questions": len(public_report["question_breakdown"]),
            "communication_context": interview.get(
                "communication_context",
                "neutral",
            ),
        }

        return {
            "success": True,
            "report": public_report,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to generate report: {exc}",
        ) from exc
