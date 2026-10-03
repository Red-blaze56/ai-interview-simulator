"""
One-off importer: parse a translated knowledge-base file into References rows.
"""
import asyncio
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent      # .../backend
sys.path.insert(0, str(BACKEND))                      # make `app` importable
DATA_DIR = BACKEND.parent / "data"                    # project-root/data

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.database.models import References

DEFAULT_FILE = DATA_DIR / "common-backend-knowledge-base.txt"
DEFAULT_DIFFICULTY = 3

_H2 = re.compile(r"^##\s+(.*)")
_H3 = re.compile(r"^###\s+(.*)")
_BOLD_LINE = re.compile(r"^\*\*(.+?)\*\*$")
_QA = re.compile(r"^-\s+\*\*(.+?)\*\*\s*[—–]\s*(.+)$")   # - **question** — answer
_NUM_PREFIX = re.compile(r"^\d+\.\s*")


def _slug(title: str) -> str:
    title = _NUM_PREFIX.sub("", title.strip())
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def parse(md: str) -> list[dict]:
    topic: str | None = None
    sub_topic: str | None = None
    rows: list[dict] = []
    for raw in md.splitlines():
        line = raw.strip()
        if m := _H3.match(line):
            sub_topic = m.group(1).strip()
        elif m := _H2.match(line):
            topic = _slug(m.group(1))
            sub_topic = None
        elif m := _BOLD_LINE.match(line):
            sub_topic = m.group(1).strip()
        elif (m := _QA.match(line)) and topic:
            rows.append({
                "topic": topic,
                "sub_topic": sub_topic,
                "question": m.group(1).strip(),
                "reference_answer": m.group(2).strip(),
            })
    return rows


async def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    rows = parse(path.read_text(encoding="utf-8"))

    topics = sorted({r["topic"] for r in rows})
    print(f"Parsed {len(rows)} Q&A rows across {len(topics)} topics:")
    for t in topics:
        print(f"  {t}: {sum(1 for r in rows if r['topic'] == t)}")

    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        await db.execute(delete(References).where(References.programming_language.is_(None)))
        db.add_all([
            References(
                programming_language=None,
                topic=r["topic"],
                sub_topic=r["sub_topic"],
                question=r["question"],
                reference_answer=r["reference_answer"],
                key_points=[],
                difficulty=DEFAULT_DIFFICULTY,
            )
            for r in rows
        ])
        await db.commit()
    await engine.dispose()
    print(f"Seeded {len(rows)} references.")


if __name__ == "__main__":
    asyncio.run(main())