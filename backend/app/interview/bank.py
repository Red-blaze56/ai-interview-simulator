from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CandidateLevelEnum, ProgrammingLanguageEnum, References

# Controlled vocabulary — matches the seeded References.topic slugs. The LLM's `topic`
# output is locked to this list, and bank_context looks up rows by it.
KNOWN_TOPICS = [
    "mysql",
    "redis",
    "message_queues",
    "computer_networks",
    "operating_systems",
    "distributed_systems",
    "system_design",
    "performance_analysis_and_troubleshooting",
    "engineering_practices",
    "general",   # icebreaker — no bank material
]

# Every seeded topic is currently language-neutral (common-backend → NULL language),
# so none get language-filtered. Revisit when language-specific banks are added.
LANGUAGE_NEUTRAL_TOPICS = frozenset(KNOWN_TOPICS)

_LEVEL_BASE_DIFFICULTY = {
    CandidateLevelEnum.INTERN: 1,
    CandidateLevelEnum.FRESHER: 2,
    CandidateLevelEnum.JUNIOR: 3,
    CandidateLevelEnum.MID: 3,
    CandidateLevelEnum.SENIOR: 4,
}


def target_difficulty(level: CandidateLevelEnum, probe_depth: int) -> int:
    """Difficulty to aim for, given who they are and how deep we've drilled."""
    return min(5, _LEVEL_BASE_DIFFICULTY.get(level, 2) + probe_depth)


async def bank_context(
    db: AsyncSession,
    *,
    language: ProgrammingLanguageEnum,
    topic: str,
    difficulty: int,
    limit: int = 3,
) -> list[dict]:
    """Reference Q/A for a topic, nearest the target difficulty. Fed to the model as
    material to grade against and build on — never read out verbatim."""
    if not topic or topic == "general":
        return []
    stmt = select(References).where(References.topic == topic)
    if topic not in LANGUAGE_NEUTRAL_TOPICS:
        stmt = stmt.where(References.programming_language == language)
    items = list((await db.scalars(stmt)).all())
    items.sort(key=lambda i: (abs(i.difficulty - difficulty), i.difficulty))
    return [
        {
            "question": i.question,
            "reference_answer": i.reference_answer,
            "difficulty": i.difficulty,
            "key_points": i.key_points or [],
        }
        for i in items[:limit]
    ]