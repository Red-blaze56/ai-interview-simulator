"""Automated "candidate agent" that plays through the interview API.

Run from backend/:
    uv run python scripts/fake_candidate.py --persona confidently_wrong

NOTE ON QUOTA: by default the candidate LLM uses the SAME key/model/base URL as
the app (settings.llm_*), so interviewer AND candidate both hit Gemini and your
quota use roughly doubles. Point the candidate elsewhere with --candidate-model /
--candidate-api-key / --candidate-base-url (or CANDIDATE_LLM_MODEL /
CANDIDATE_LLM_API_KEY / CANDIDATE_LLM_BASE_URL env vars).
"""
import argparse
import asyncio
import json
import os
import random
import secrets
import sys

import httpx
from openai import AsyncOpenAI

# make `app` importable when run as `python scripts/fake_candidate.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PERSONAS = {
    "strong_senior": (
        "You are a strong senior engineer. Answer accurately and in depth, name "
        "trade-offs and failure modes, and give concrete mechanisms and numbers."
    ),
    "nervous_intern": (
        "You are a nervous intern. You know the correct basics but answer briefly "
        "(1-2 short sentences), hesitantly, and admit gaps in your knowledge."
    ),
    "confidently_wrong": (
        "You state plausible-sounding but factually WRONG things with total "
        "confidence. Never hedge, never admit doubt. Sound authoritative."
    ),
    "vague_handwaver": (
        "You answer with buzzwords and generalities. Never give concrete "
        "mechanisms, specifics, or numbers. Hand-wave everything."
    ),
}
COMMON = (
    "You are a job candidate in a live spoken technical interview for a {level} "
    "{language} role. Reply as you would speak: plain text, no markdown, no lists, "
    "under 120 words. Never mention being an AI or playing a persona.\n\nPersona: "
)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--persona", default="mixed", choices=[*PERSONAS, "mixed"])
    p.add_argument("--level", default="mid", choices=["intern", "fresher", "junior", "mid", "senior"])
    p.add_argument("--interviewer-style", default="engineering",
                   choices=["strict", "warm", "engineering", "academic", "sarcasm", "coaching"])
    p.add_argument("--correction-mode", default="guided", choices=["strict", "guided"])
    p.add_argument("--max-turns", type=int, default=12)
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--seed", type=int, default=None, help="seed for 'mixed' persona picking")
    p.add_argument("--json-out", default=None, help="dump raw per-turn records to this path")
    p.add_argument("--candidate-model", default=os.getenv("CANDIDATE_LLM_MODEL"))
    p.add_argument("--candidate-api-key", default=os.getenv("CANDIDATE_LLM_API_KEY"))
    p.add_argument("--candidate-base-url", default=os.getenv("CANDIDATE_LLM_BASE_URL"))
    return p.parse_args()


def candidate_client(args) -> tuple[AsyncOpenAI, str]:
    key, url, model = args.candidate_api_key, args.candidate_base_url, args.candidate_model
    if not (key and url and model):
        from app.core.config import settings  # lazy: needs backend/.env
        key, url, model = key or settings.llm_api_key, url or settings.llm_base_url, model or settings.llm_model
    return AsyncOpenAI(api_key=key, base_url=url), model


async def candidate_answer(client, model, persona, level, question, history) -> str:
    system = COMMON.format(level=level, language="python") + PERSONAS[persona]
    messages = [{"role": "system", "content": system}]
    for q, a in history[-4:]:
        messages += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
    messages.append({"role": "user", "content": question})
    resp = await client.chat.completions.create(model=model, messages=messages, temperature=0.9)
    return (resp.choices[0].message.content or "").strip() or "I'm not sure."


def last_question(interview: dict) -> str:
    msgs = [m for m in interview["messages"] if m["sender"] == "interviewer"]
    return msgs[-1]["content"] if msgs else ""


def check(resp: httpx.Response) -> httpx.Response:
    if resp.is_error:
        print(f"HTTP {resp.status_code} from {resp.request.method} {resp.request.url}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    return resp


def fmt_eval(ev: dict | None) -> tuple:
    ev = ev or {}
    return ev.get("score"), ev.get("correct"), ev.get("confident"), ev.get("feedback") or ""


def print_summary(records, report):
    print("\n" + "=" * 78 + "\nTRANSCRIPT\n" + "=" * 78)
    for r in records:
        print(f"\n[Turn {r['turn']}] ({r['persona']}, topic: {r['topic']})\nInterviewer: {r['question']}\nCandidate:   {r['answer']}")

    print("\n" + "=" * 78 + "\nEVALUATIONS\n" + "=" * 78)
    print(f"{'Turn':<5} {'Persona':<18} {'Score':<6} {'Correct':<8} {'Confident':<10} {'Finish':<7} Feedback")
    for r in records:
        s, c, cf, fb = fmt_eval(r["evaluation"])
        print(f"{r['turn']:<5} {r['persona']:<18} {str(s):<6} {str(c):<8} {str(cf):<10} {str(r['should_finish']):<7} {fb}")

    scores = [fmt_eval(r["evaluation"])[0] for r in records if isinstance(fmt_eval(r["evaluation"])[0], (int, float))]
    n_correct = sum(1 for r in records if fmt_eval(r["evaluation"])[1])
    fin = next((r["turn"] for r in records if r["should_finish"]), None)
    mean = f"{sum(scores) / len(scores):.1f}" if scores else "n/a"
    print(f"\nMean score {mean} | correct {n_correct}/{len(records)} | "
          f"finished: {'yes (should_finish on turn %d)' % fin if fin else 'no (turn cap reached)'}")
    if report:
        print("\nFINAL REPORT\n" + json.dumps(report, indent=2))


async def main():
    args = parse_args()
    rng = random.Random(args.seed)
    client, model = candidate_client(args)
    records, report = [], None

    async with httpx.AsyncClient(base_url=args.base_url, timeout=120) as http:
        email, password = f"fake_{secrets.token_hex(4)}@candidatebot.dev", secrets.token_urlsafe(12)
        r = await http.post("/auth/register", json={"email": email, "password": password})
        if r.status_code != 409:
            check(r)
        tok = check(await http.post("/auth/login", data={"username": email, "password": password})).json()
        http.headers["Authorization"] = f"Bearer {tok['access_token']}"

        interview = check(await http.post("/interviews", json={
            "programming_language": "python",
            "candidate_level": args.level,
            "personality_type": args.interviewer_style,
            "correction_mode": args.correction_mode,
        })).json()
        iid = interview["id"]
        print(f"Interview {iid} | persona={args.persona} level={args.level} "
              f"style={args.interviewer_style} mode={args.correction_mode} | candidate model={model}")

        history = []
        try:
            for turn in range(1, args.max_turns + 1):
                question = last_question(interview)
                persona = rng.choice(list(PERSONAS)) if args.persona == "mixed" else args.persona
                answer = await candidate_answer(client, model, persona, args.level, question, history)
                data = check(await http.post(f"/interviews/{iid}/answer", json={"content": answer})).json()

                ev, finish = data["evaluation"], data["should_finish"]
                interview = data["interview"]
                topic = interview.get("current_topic")
                records.append({"turn": turn, "persona": persona, "topic": topic, "question": question,
                                "answer": answer, "evaluation": ev, "should_finish": finish})
                history.append((question, answer))

                s, c, cf, fb = fmt_eval(ev)
                print(f"\n--- Turn {turn} [{persona}] next topic: {topic} ---\nQ: {question}\nA: {answer}\n"
                      f"   score={s}  correct={c}  confident={cf}  should_finish={finish}\n   feedback: {fb}", flush=True)
                if finish:
                    report = interview.get("report")
                    break
        except Exception as exc:  # still show what we collected
            print(f"\n!! Aborted on turn {len(records) + 1}: {type(exc).__name__}: {exc}", file=sys.stderr)
        finally:
            print_summary(records, report)
            if args.json_out:
                with open(args.json_out, "w", encoding="utf-8") as f:
                    json.dump({"interview_id": iid, "records": records, "report": report}, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
