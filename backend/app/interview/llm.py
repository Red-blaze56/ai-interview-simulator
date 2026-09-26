import json
import logging
import re

from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.core.config import settings
from app.database.models import StageEnum

logger = logging.getLogger(__name__)

PROBE_ACTIONS = ["deepen", "switch", "correct_and_stay", "wrap"]
STAGE_VALUES = [s.value for s in StageEnum]

SYSTEM_PROMPT = """You are a senior backend engineering interviewer running one live interview.

Persona:
- language: {language}
- interviewer_style: {style}
- correction_mode: {mode}

Rules:
- Ask exactly ONE question per turn, in natural spoken phrasing. Never read a reference verbatim.
- For a brand-new interview, open with a short icebreaker before technical questions.
- Use the transcript and the resume/JD to stay coherent and never repeat a question.

How to probe (the core of the interview):
- Drill ONE topic at a time, going deeper each turn the candidate holds up.
- "deepen" = the SAME topic, one layer harder. Changing topic is "switch", never "deepen".
- Correct & confident -> deepen. Correct but vague -> deepen at the hand-wave.
- Wrong in guided mode -> "correct_and_stay": briefly give the answer, re-ask the same layer.
  Wrong in strict mode -> "switch" and move on.
- Bottom of a topic, or ~5 layers deep, or clearly broken -> "switch" to a new topic.
- Label every question with a short lowercase topic. Use "general" only for the icebreaker.

Grading:
- Judge CORRECT (a score below 5 means correct=false) and CONFIDENT (specific mechanisms,
  numbers, tradeoffs) separately.
- If given reference material, grade against it and use it to find the next layer down.
  Do NOT recite it."""


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


class LLMUnavailable(RuntimeError):
    """The model could not be reached. Message is safe to show a user."""


def _build_system(*, language: str, style: str, mode: str) -> str:
    return SYSTEM_PROMPT.format(language=language, style=style, mode=mode)


def _safe_json(content: str, fallback: dict) -> dict:
    """Parse model JSON, tolerating code fences / stray text."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"```(?:json)?\s*", "", text).removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        logger.warning("LLM returned non-JSON; using fallback. %s", content[:300])
        return fallback


async def _chat(messages: list[dict], schema: dict) -> str:
    try:
        resp = await _client().chat.completions.create(
            model=settings.llm_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.7,
            response_format={"type": "json_schema", "json_schema": schema},  # type: ignore[arg-type]
        )
    except AuthenticationError as exc:
        raise LLMUnavailable("Provider rejected the API key. Check LLM_API_KEY.") from exc
    except RateLimitError as exc:
        raise LLMUnavailable(
            f"Out of quota for '{settings.llm_model}'. Free-tier Gemini caps daily "
            "requests per model — wait for the reset or switch LLM_MODEL."
        ) from exc
    except (APIStatusError, APIConnectionError) as exc:
        raise LLMUnavailable(f"LLM call failed: {exc}") from exc
    return resp.choices[0].message.content or ""


def _briefing(probe: dict) -> str:
    lines = [
        f"Current topic: {probe.get('topic') or '(opening — no topic yet)'}",
        f"Probe depth so far: {probe.get('depth', 0)}",
        f"Consecutive wrong answers: {probe.get('consecutive_wrongs', 0)}",
    ]
    if probe.get("covered"):
        lines.append(f"Already exhausted, do not revisit: {', '.join(probe['covered'])}")
    if probe.get("planned"):
        lines.append(f"Queued from their resume: {', '.join(probe['planned'][:5])}")
    if probe.get("resume_text"):
        lines.append(f"\nCandidate resume:\n{probe['resume_text'][:2000]}")
    if probe.get("jd_text"):
        lines.append(f"\nTarget JD:\n{probe['jd_text'][:1000]}")
    bank = probe.get("bank") or []
    if bank:
        lines.append("\nReference material (grade against it, build on it, do NOT read it out):")
        for item in bank:
            lines.append(
                f"- [difficulty {item['difficulty']}] {item['question']}\n"
                f"  known-good answer: {item['reference_answer']}"
            )
    else:
        lines.append("\nNo reference material for this topic — rely on your own expertise.")
    return "\n".join(lines)


_TURN_SCHEMA = {
    "name": "question_turn",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "stage": {"type": "string", "enum": STAGE_VALUES},
            "topic": {"type": "string"},
            "next_question": {"type": "string"},
            "evaluation": {
                "type": "object",
                "properties": {
                    "score": {"type": "number"},
                    "feedback": {"type": "string"},
                    "correct": {"type": "boolean"},
                    "confident": {"type": "boolean"},
                },
                "required": ["score", "feedback", "correct", "confident"],
            },
            "probe_action": {"type": "string", "enum": PROBE_ACTIONS},
            "should_finish": {"type": "boolean"},
        },
        "required": ["stage", "topic", "next_question", "evaluation", "probe_action", "should_finish"],
    },
}

_REPORT_SCHEMA = {
    "name": "interview_report",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "overall_score": {"type": "number"},
            "summary": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "weaknesses": {"type": "array", "items": {"type": "string"}},
            "suggestions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["overall_score", "summary", "strengths", "weaknesses", "suggestions"],
    },
}


async def ask_next(*, system_args: dict, transcript: list[dict], probe: dict, stage: str) -> dict:
    """One call: grade the last answer, pick the probe action, write the next question."""
    instruction = (
        f"Current stage: {stage}.\n\n{_briefing(probe)}\n\n"
        "Grade the last answer, decide whether to drill deeper or move on, and write the "
        "next question. Set 'topic' to what your NEXT question is about."
    )
    messages = [
        {"role": "system", "content": _build_system(**system_args)},
        *transcript,
        {"role": "user", "content": instruction},
    ]
    content = await _chat(messages, _TURN_SCHEMA)
    return _safe_json(content, fallback={
        "stage": stage,
        "topic": probe.get("topic", ""),
        "next_question": "Tell me more about that.",
        "evaluation": {"score": 5, "feedback": "Please continue.", "correct": True, "confident": False},
        "probe_action": "deepen",
        "should_finish": False,
    })


async def final_report(*, system_args: dict, transcript: list[dict]) -> dict:
    """End of interview: synthesize the whole transcript into a structured report."""
    messages = [
        {"role": "system", "content": _build_system(**system_args)},
        *transcript,
        {"role": "user", "content": "The interview is over. Produce the final structured report."},
    ]
    content = await _chat(messages, _REPORT_SCHEMA)
    return _safe_json(content, fallback={
        "overall_score": 0, "summary": "", "strengths": [], "weaknesses": [], "suggestions": [],
    })