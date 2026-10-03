from uuid import UUID
from datetime import datetime, timezone

from fastapi import status, HTTPException

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Interview, Messages, SenderEnum, StageEnum, StatusEnum
from app.interview.schemas import InterviewCreate
from app.interview.llm import LLMUnavailable, ask_next, final_report
from app.interview.probe import apply_probe
from app.interview.bank import bank_context, target_difficulty

OPENING_QUESTION = "Hi! To get started, tell me about a backend project you're proud of and what your role was."

_LLM_ROLE = {SenderEnum.INTERVIEWER: "assistant", SenderEnum.CANDIDATE: "user"}

#--------------------------------------------------------------------------------------

async def _get_full(db: AsyncSession, interview_id: UUID) -> Interview | None :
    result = await db.scalar(
        select(Interview)
        .where(Interview.id == interview_id)
        .options(selectinload(Interview.messages))
    )
    return result

async def create_interview(db: AsyncSession, *, user_id: UUID, payload: InterviewCreate) -> Interview:
    interview = Interview(
        user_id=user_id,
        programming_language=payload.programming_language,
        candidate_level=payload.candidate_level,
        personality_type=payload.personality_type,
        correction_mode=payload.correction_mode,
        resume_text=payload.resume_text,
        jd_text=payload.jd_text,
        stage=StageEnum.ICE_BREAKER,
        next_question=OPENING_QUESTION,
        covered_topics=[],
        focus_topics=[],
    )
    interview.messages.append(
        Messages(sender=SenderEnum.INTERVIEWER, content=OPENING_QUESTION)
    )
    db.add(interview)
    await db.commit()
    x = await _get_full(db,interview.id)
    assert x is not None
    return x

#--------------------------------------------------------------------------------------

def _add_message(interview: Interview, sender: SenderEnum, content: str) -> None:
    interview.messages.append(
        Messages(sender=sender, content=content, created_at=datetime.now(timezone.utc))
    )

def _transcript(interview: Interview) -> list[dict]:
    return [{"role": _LLM_ROLE[m.sender], "content": m.content} for m in interview.messages]

def _system_args(interview: Interview) -> dict:
    return {
        "language": interview.programming_language.value,
        "style": interview.personality_type.value,
        "mode": interview.correction_mode.value, 
    }

async def _build_probe(db: AsyncSession, interview: Interview) -> dict:
    covered = list(interview.covered_topics or [])
    difficulty = target_difficulty(interview.candidate_level, interview.probe_depth)
    bank = await bank_context(
        db,
        language=interview.programming_language,
        topic=interview.current_topic,
        difficulty=difficulty
    )
    return {
        "topic": interview.current_topic,
        "depth": interview.probe_depth,
        "consecutive_wrongs": interview.consecutive_wrongs,
        "covered": covered,
        "planned": [t for t in (interview.focus_topics or []) if t not in covered],
        "resume_text": interview.resume_text,
        "jd_text": interview.jd_text,
        "bank": bank,
    }

async def submit_answer(db:AsyncSession, *, interview: Interview, content: str) -> tuple[Interview, dict, bool]:
    if interview.status != StatusEnum.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview already finished")

    pending = [*_transcript(interview), {"role": "user", "content": content}]
    try:
        result = await ask_next(
            system_args=_system_args(interview),
            transcript=pending,
            probe= await _build_probe(db, interview),
            stage=interview.stage.value,
        )
    except LLMUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    # Model replied → the turn is real, record the answer now.
    _add_message(interview, SenderEnum.CANDIDATE, content)

    evaluation = result.get("evaluation", {"score": 5, "feedback": ""})
    should_finish = bool(result.get("should_finish", False))

    if should_finish:
        interview.status = StatusEnum.FINISHED
        interview.next_question = ""
        try:
            interview.report = await final_report(
                system_args=_system_args(interview),
                transcript=_transcript(interview),
            )
        except LLMUnavailable:
            interview.report = None   # interview still ends; report recoverable later
    else:
        apply_probe(interview, result)
        interview.stage = StageEnum(result.get("stage", interview.stage.value))
        interview.next_question = result["next_question"]
        _add_message(interview, SenderEnum.INTERVIEWER, result["next_question"])

    await db.commit()
    full = await _get_full(db, interview.id)
    assert full is not None
    return full, evaluation, should_finish