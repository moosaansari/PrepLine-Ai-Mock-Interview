import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3.6-flash"

EVALUATION_SCHEMA = {
    "overall_score": 0,
    "communication_score": 0,
    "confidence_score": 0,
    "technical_score": 0,
    "clarity_score": 0,
    "professionalism_score": 0,
    "communication_style": "Professional",
    "confidence_level": "Limited evidence",
    "nervousness_level": "Limited evidence",
    "tone": "Professional",
    "aggression_level": "Low",
    "delivery_style": "Limited evidence",
    "filler_words": [],
    "strengths": [],
    "improvement_areas": [],
    "communication_feedback": "",
    "confidence_feedback": "",
    "technical_feedback": "",
    "interviewer_summary": "",
    "action_plan": [],
                                 
    "content_quality": {
        "score": 0,
        "technical_correctness": 0,
        "relevance": 0,
        "completeness": 0,
        "reasoning": 0,
        "examples": 0,
        "structure": 0,
        "feedback": "",
    },
    "communication": {
        "score": 0,
        "clarity": 0,
        "confidence": 0,
        "directness": 0,
        "professionalism": 0,
        "perceived_aggressiveness": 0,
        "verbosity": "",
        "assertiveness": "",
        "hesitation": "",
        "filler_words_count": 0,
        "politeness": "",
        "intensity": "",
        "observed_delivery": "",
    },
    "contextual_interpretation": {
        "selected_context": "",
        "possible_perception": "",
        "alternative_context_perception": "",
        "cross_cultural_tip": "",
    },
}

PROMPT = """
You are PREPLINE, an expert technical interview evaluator.
Evaluate ONLY the evidence in the supplied interview transcript.
The candidate's selected role is authoritative.

Do not diagnose personality, mental health, or emotions.
Confidence/nervousness are only observable communication estimates from text.
If evidence is insufficient, say "Limited evidence" rather than inventing certainty.
Do not invent skills, projects, achievements, or technical facts.

====================================================================
LAYER 1 — CONTENT QUALITY (what they said)
====================================================================
Evaluate the substance and correctness of the candidate's answer.
This layer is purely about WHAT was said — the technical content,
reasoning, examples, completeness, and structure.

Keys: content_quality.score (0-100), content_quality.technical_correctness (0-100),
content_quality.relevance (0-100), content_quality.completeness (0-100),
content_quality.reasoning (0-100), content_quality.examples (0-100),
content_quality.structure (0-100), content_quality.feedback (string).

====================================================================
LAYER 2 — DELIVERY / COMMUNICATION (how they said it)
====================================================================
Evaluate the observed delivery style from the transcript text only.
Describe directness, assertiveness, verbosity, hesitation, confidence,
politeness, intensity, filler words, and overall communication style.

Keys: communication.score (0-100), communication.clarity (0-100),
communication.confidence (0-100), communication.directness (0-100),
communication.professionalism (0-100),
communication.perceived_aggressiveness (0-100, how forceful the wording
may be read as — NOT a judgement about the person),
communication.verbosity (string),
communication.assertiveness (string), communication.hesitation (string),
communication.filler_words_count (integer), communication.politeness (string),
communication.intensity (string), communication.observed_delivery (string).

====================================================================
LAYER 3 — CONTEXTUAL INTERPRETATION (how delivery may be perceived)
====================================================================
Given the selected communication context, explain how the candidate's
delivery style might be perceived by interviewers from that context.

CRITICAL RULES:
- NEVER say the candidate IS aggressive, rude, or lacks confidence.
- Use probabilistic language: "may be perceived as", "could potentially
  be interpreted as", "in some interview settings".
- Always acknowledge that individual interviewers differ.
- Distinguish observed behavior from possible interviewer perception.
- The content_quality.score must NOT change based on delivery or context.
- The SAME answer must get the SAME content score regardless of context.

Keys: contextual_interpretation.selected_context (string),
contextual_interpretation.possible_perception (string),
contextual_interpretation.alternative_context_perception (string),
contextual_interpretation.cross_cultural_tip (string).

====================================================================
LEGACY KEYS (also return these for backward compatibility)
====================================================================
overall_score (average of content and communication scores),
communication_score, confidence_score, technical_score,
clarity_score, professionalism_score (all 0-100),
communication_style, confidence_level, nervousness_level, tone,
aggression_level, delivery_style, filler_words, strengths, improvement_areas,
communication_feedback, confidence_feedback, technical_feedback,
interviewer_summary, action_plan.

delivery_style: one of "confident", "assertive", "overly forceful / aggressive",
"mixed", or "limited evidence". Base it on the observed wording only.

Return ONLY valid JSON with exactly these keys.
Scores are integers 0-100.
strengths, improvement_areas, action_plan: 3-5 concise items.
filler_words: only words actually present in the transcript.
"""


def _score(value: Any) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()][:8]


def _parse_json(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.endswith("```"):
            raw = raw[:-3]
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Gemini did not return a JSON object.")
    return json.loads(raw[start:end + 1])


def _normalize(result: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(EVALUATION_SCHEMA)
    for key in (
        "communication_style", "confidence_level", "nervousness_level",
        "tone", "aggression_level", "delivery_style", "communication_feedback",
        "confidence_feedback", "technical_feedback", "interviewer_summary",
    ):
        value = result.get(key)
        if value is not None:
            out[key] = str(value).strip()
    for key in (
        "overall_score", "communication_score", "confidence_score",
        "technical_score", "clarity_score", "professionalism_score",
    ):
        out[key] = _score(result.get(key, 0))
    for key in ("filler_words", "strengths", "improvement_areas", "action_plan"):
        out[key] = _strings(result.get(key, []))

                                            
    cq = result.get("content_quality")
    if isinstance(cq, dict):
        out["content_quality"] = {
            "score": _score(cq.get("score", 0)),
            "technical_correctness": _score(cq.get("technical_correctness", 0)),
            "relevance": _score(cq.get("relevance", 0)),
            "completeness": _score(cq.get("completeness", 0)),
            "reasoning": _score(cq.get("reasoning", 0)),
            "examples": _score(cq.get("examples", 0)),
            "structure": _score(cq.get("structure", 0)),
            "feedback": str(cq.get("feedback", "")).strip(),
        }

                                          
    cm = result.get("communication")
    if isinstance(cm, dict):
        out["communication"] = {
            "score": _score(cm.get("score", 0)),
            "clarity": _score(cm.get("clarity", 0)),
            "confidence": _score(cm.get("confidence", 0)),
            "directness": _score(cm.get("directness", 0)),
            "professionalism": _score(cm.get("professionalism", 0)),
            "perceived_aggressiveness": _score(cm.get("perceived_aggressiveness", 0)),
            "verbosity": str(cm.get("verbosity", "")).strip(),
            "assertiveness": str(cm.get("assertiveness", "")).strip(),
            "hesitation": str(cm.get("hesitation", "")).strip(),
            "filler_words_count": _score(cm.get("filler_words_count", 0)),
            "politeness": str(cm.get("politeness", "")).strip(),
            "intensity": str(cm.get("intensity", "")).strip(),
            "observed_delivery": str(cm.get("observed_delivery", "")).strip(),
        }

                                                      
    ci = result.get("contextual_interpretation")
    if isinstance(ci, dict):
        out["contextual_interpretation"] = {
            "selected_context": str(ci.get("selected_context", "")).strip(),
            "possible_perception": str(ci.get("possible_perception", "")).strip(),
            "alternative_context_perception": str(ci.get("alternative_context_perception", "")).strip(),
            "cross_cultural_tip": str(ci.get("cross_cultural_tip", "")).strip(),
        }

    out["score"] = out["overall_score"]
    out["feedback"] = out["interviewer_summary"] or out["technical_feedback"]
    if not out.get("delivery_style"):
        out["delivery_style"] = _derive_delivery_style(out)
    return out


def _gemini_generate(prompt: str) -> str:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing in .env")
    from google import genai
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return text.strip()
    finally:
        try:
            client.close()
        except Exception:
            pass


def _mock_evaluation(
    question: str,
    answer: str,
    role: str,
    language: str = "English",
    communication_context: str = "neutral",
) -> Dict[str, Any]:
    words = answer.split()
    score = max(45, min(90, 50 + len(words) // 4))
    context_label = _context_label(communication_context)
    return _normalize({
        "overall_score": score,
        "communication_score": score,
        "confidence_score": max(45, score - 3),
        "technical_score": score,
        "clarity_score": score,
        "professionalism_score": min(100, score + 3),
        "communication_style": "Clear and professional",
        "confidence_level": "Moderately confident",
        "nervousness_level": "Limited evidence",
        "tone": "Professional",
        "aggression_level": "Low",
        "delivery_style": "confident and assertive" if score >= 65 else "mixed",
        "filler_words": [],
        "strengths": ["Relevant response", "Generally focused answer", "Useful understanding shown"],
        "improvement_areas": ["Add concrete examples", "Explain reasoning and trade-offs", "State your personal contribution clearly"],
        "action_plan": ["Use a structured answer format", "Practice technical explanations aloud", "Support claims with project examples"],
        "communication_feedback": "Transcript was understandable; improve structure and specificity.",
        "confidence_feedback": "Confidence estimate is limited because only transcript text is available.",
        "technical_feedback": "Add more technical depth, reasoning and trade-offs.",
        "interviewer_summary": f"Response showed a useful foundation for the {role} role.",
        "content_quality": {
            "score": score,
            "technical_correctness": score,
            "relevance": score,
            "completeness": max(40, score - 5),
            "reasoning": max(40, score - 5),
            "examples": max(40, score - 8),
            "structure": max(40, score - 3),
            "feedback": "Evaluation ran in demo mode. Add more technical depth, reasoning and concrete examples to improve the content score.",
        },
        "communication": {
            "score": score,
            "clarity": score,
            "confidence": max(45, score - 3),
            "directness": score,
            "professionalism": min(100, score + 3),
            "perceived_aggressiveness": max(10, score - 20),
            "verbosity": "Balanced",
            "assertiveness": "Moderate",
            "hesitation": "Limited evidence",
            "filler_words_count": 0,
            "politeness": "Professional",
            "intensity": "Moderate",
            "observed_delivery": "Demonstration mode is active. Delivery observations are estimated from the transcript text only.",
        },
        "contextual_interpretation": {
            "selected_context": context_label,
            "possible_perception": "In this demonstration, the selected communication context was "
                f"{context_label}. The delivery might generally be seen as appropriate, though individual "
                "interviewers can perceive the same delivery differently.",
            "alternative_context_perception": "Under a different communication context, the very same delivery "
                "could potentially be interpreted differently. The content and technical score are unchanged.",
            "cross_cultural_tip": "Observe the interviewer's communication norms and mirror them moderately. "
                "What matters most is that your technical content is correct and clear.",
        },
    })


def _derive_delivery_style(scores: Dict[str, Any]) -> str:
    """Observable delivery style label from the recorded delivery signals.

    Used when the model does not return delivery_style, and by the fallback
    report. Describes the wording only, never the person.
    """
    comm = scores.get("communication") if isinstance(scores.get("communication"), dict) else {}
    confidence = _score(comm.get("confidence", scores.get("confidence_score", 0)))
    directness = _score(comm.get("directness", 0))
    perceived = _score(comm.get("perceived_aggressiveness", 0))

    legacy = str(scores.get("aggression_level", "")).strip().lower()
    if legacy in ("high", "very high"):
        perceived = max(perceived, 70)
    elif legacy == "moderate":
        perceived = max(perceived, 50)

    if perceived >= 70:
        return "overly forceful / aggressive wording"
    if confidence >= 70 and directness >= 70:
        return "confident and assertive"
    if confidence >= 65:
        return "confident"
    if directness >= 65:
        return "assertive"
    if confidence or directness:
        return "mixed"
    return "Limited evidence"


def _context_label(communication_context: Optional[str]) -> str:
    """Human-readable label for a communication-style context value.

    Contexts describe communication norms/styles, never nationalities,
    ethnicities or religions. Unrecognised or legacy values fall back to the
    neutral label so old interview documents still render safely.
    """
    text = (communication_context or "").strip().lower()
    if text in ("direct", "direct_communication", "low_context"):
        return "Direct communication context"
    if text in (
        "indirect",
        "indirect_high_politeness",
        "high_politeness",
        "high_context",
    ):
        return "Indirect / high-politeness communication context"
    return "Neutral / balanced communication context"


def evaluate_answer(
    question: str,
    answer: str,
    role: str = "Software Engineer",
    language: str = "English",
    communication_context: str = "neutral",
) -> Dict[str, Any]:
    if not answer or not answer.strip():
        return _normalize({"overall_score": 0, "technical_score": 0,
                           "communication_score": 0, "confidence_score": 0,
                           "clarity_score": 0, "professionalism_score": 0,
                           "interviewer_summary": "No answer was detected."})
    prompt = f"""{PROMPT}

Selected role: {role}
Candidate language: {language}
Selected communication context: {communication_context}
Context label: {_context_label(communication_context)}

IMPORTANT:
- Language must NOT penalize the content / technical score. Evaluate the
  technical substance independently of fluency in English.
- If the answer is in the candidate's selected language, that is expected.

Interview question:
{question}

Candidate answer:
{answer}

Evaluate this answer now."""
    if settings.MOCK_AI:
        return _mock_evaluation(question, answer, role, language, communication_context)
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured for real answer evaluation.")
    try:
        return _normalize(_parse_json(_gemini_generate(prompt)))
    except Exception as exc:
        logger.exception("Gemini answer evaluation failed; using local fallback: %s", exc)
        fallback = _mock_evaluation(
            question,
            answer,
            role,
            language,
            communication_context,
        )
        fallback["interviewer_summary"] = (
            "The live AI evaluator was unavailable for this answer, so PREPLINE "
            "used its local evaluation fallback from the saved interview transcript."
        )
        return fallback


def _fallback_report(
    role: str,
    usable: List[Dict[str, Any]],
    communication_context: str,
) -> Dict[str, Any]:
    """Aggregate saved answer evaluations when final generation is unavailable."""
    evaluations = [item["evaluation"] for item in usable if isinstance(item.get("evaluation"), dict)]

    def average(path: tuple[str, ...]) -> int:
        values = []
        for evaluation in evaluations:
            value: Any = evaluation
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
            if isinstance(value, (int, float)):
                values.append(value)
        return round(sum(values) / len(values)) if values else 0

    content_keys = (
        "technical_correctness", "relevance", "completeness", "reasoning",
        "examples", "structure",
    )
    content = {key: average(("content_quality", key)) for key in content_keys}
    content["score"] = average(("content_quality", "score")) or average(("technical_score",))
    content["feedback"] = "Aggregated from the saved per-question content evaluations."

    communication = {
        "score": average(("communication", "score")) or average(("communication_score",)),
        "clarity": average(("communication", "clarity")) or average(("clarity_score",)),
        "confidence": average(("communication", "confidence")) or average(("confidence_score",)),
        "directness": average(("communication", "directness")),
        "professionalism": average(("communication", "professionalism")) or average(("professionalism_score",)),
        "perceived_aggressiveness": average(("communication", "perceived_aggressiveness")),
        "filler_words_count": average(("communication", "filler_words_count")),
        "verbosity": "See question-level observations.",
        "assertiveness": "See question-level observations.",
        "hesitation": "See question-level observations.",
        "politeness": "See question-level observations.",
        "intensity": "See question-level observations.",
        "observed_delivery": "Aggregated from the saved transcript-based delivery evaluations.",
    }
    delivery_styles = [str(e.get("delivery_style", "")).strip() for e in evaluations if e.get("delivery_style")]
    style = delivery_styles[0] if delivery_styles else _derive_delivery_style({"communication": communication})
    contexts = [e.get("contextual_interpretation") for e in evaluations if isinstance(e.get("contextual_interpretation"), dict)]
    selected = _context_label(communication_context)
    possible = next((str(c.get("possible_perception", "")).strip() for c in contexts if c.get("possible_perception")), "The same directness may be perceived differently by individual interviewers in different communication contexts.")
    alternative = next((str(c.get("alternative_context_perception", "")).strip() for c in contexts if c.get("alternative_context_perception")), "A different communication context could potentially read the same wording as more forceful; the content quality remains unchanged.")
    tip = next((str(c.get("cross_cultural_tip", "")).strip() for c in contexts if c.get("cross_cultural_tip")), "Treat this as a possible perception, not a judgement about personality or a group.")
    strengths = ["Every saved answer received an independent content evaluation.", "The report separates technical substance from delivery signals.", "The interview produced a complete question-by-question record."]
    improvements = ["Add concrete examples where the per-question feedback identifies gaps.", "Explain reasoning and trade-offs more explicitly.", "Adjust directness to the interviewer while preserving technical clarity."]
    action_plan = ["Use a clear situation, approach, and result structure.", "Support technical claims with a brief concrete example.", "Pause and soften wording when a direct statement could be read as forceful."]
    overall = round((content["score"] + communication["score"]) / 2)
    return _normalize({
        "overall_score": overall,
        "technical_score": content["score"],
        "communication_score": communication["score"],
        "confidence_score": communication["confidence"],
        "clarity_score": communication["clarity"],
        "professionalism_score": communication["professionalism"],
        "communication_style": style,
        "delivery_style": style,
        "confidence_level": "Based on saved transcript evidence",
        "nervousness_level": "Limited evidence",
        "tone": "See saved delivery observations",
        "aggression_level": "Possible perception varies by context",
        "strengths": strengths,
        "improvement_areas": improvements,
        "action_plan": action_plan,
        "communication_feedback": "Communication scores are aggregated independently from content quality.",
        "confidence_feedback": "Confidence is an observable transcript-based estimate, not a personality judgement.",
        "technical_feedback": content["feedback"],
        "interviewer_summary": f"Fallback report for {role}, based on all {len(usable)} saved answers.",
        "content_quality": content,
        "communication": communication,
        "contextual_interpretation": {
            "selected_context": selected,
            "possible_perception": possible,
            "alternative_context_perception": alternative,
            "cross_cultural_tip": tip,
        },
    })


def generate_final_report(    role: str,
    interview_answers: List[Dict[str, Any]],
    language: str = "English",
    communication_context: str = "neutral",
) -> Dict[str, Any]:
    usable = []
    for item in interview_answers:
        question = str(item.get("question_text") or item.get("question") or "").strip()
        answer = str(item.get("transcript") or item.get("answer") or "").strip()
        evaluation = item.get("evaluation") if isinstance(item.get("evaluation"), dict) else {}
        if question or answer:
            usable.append({"question": question, "answer": answer, "evaluation": evaluation})
    if not usable:
        raise ValueError("No saved interview answers are available for this report.")
    if settings.MOCK_AI:
        return _mock_evaluation(" ".join(x["question"] for x in usable), " ".join(x["answer"] for x in usable), role, language, communication_context)
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured for real report generation.")
    transcript=[]
    for i,item in enumerate(usable,1):
        transcript.append(f"Question {i}: {item['question']}\nCandidate answer {i}: {item['answer']}\nPer-answer evaluation: {json.dumps(item['evaluation'], ensure_ascii=False)}")
    prompt=f"""{PROMPT}

You are generating the FINAL report for one completed interview.
Selected role: {role}
Candidate language: {language}
Selected communication context: {communication_context}
Context label: {_context_label(communication_context)}

IMPORTANT:
- Language must NOT penalize scores.
- The content / technical assessment is independent of the selected communication context.
- Use ONLY the saved questions, candidate answers, and per-answer evaluations below.
- Do not fabricate missing evidence.

FULL INTERVIEW:
{"\n\n".join(transcript)}

Generate the final report JSON."""
    try:
        return _normalize(_parse_json(_gemini_generate(prompt)))
    except Exception as exc:
        logger.exception("Gemini final report failed; building saved-answer fallback: %s", exc)
        return _fallback_report(role, usable, communication_context)

