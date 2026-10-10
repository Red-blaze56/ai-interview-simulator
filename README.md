# AI Interview Simulator

A hybrid **database + LLM** mock-interview platform for backend engineering roles. The
database *grounds* the interview — it owns the flow, picks topics, sets difficulty, and
anchors scoring against a curated reference bank — while the LLM owns the *language*,
phrasing each question and grading each answer. The interviewer probes deeper when you're
solid, backs off when you're not, and produces a final report.

- **Auth** — register / login (JWT access tokens).
- **Grounded interview loop** — an adaptive probe state machine (deepen / switch / correct-and-stay) backed by a seeded reference bank, so the grader checks answers against known-good material instead of rewarding confident nonsense.
- **Report** — per-answer evaluation plus an end-of-interview summary.
- **History** — list and reopen your past interviews.

## Tech stack

| Layer | Stack |
|---|---|
| Backend | FastAPI (async), SQLAlchemy 2.0 + asyncpg, Alembic, PyJWT, pydantic-settings |
| Database | PostgreSQL 16 (via Docker) |
| LLM | Gemini |
| Frontend | React 19 + Vite + React Router |
| Tooling | `uv` (Python), `npm` (Node) |

## Prerequisites

- **Docker** (for PostgreSQL)
- **Python 3.13** + [`uv`](https://docs.astral.sh/uv/)
- **Node.js 18+** + npm
- A **Google AI Studio (Gemini) API key** 

## Setup & run

### 1. Clone

```bash
git clone <repo-url>
cd AI-Interview-Simulator
```

### 2. Backend environment

Create `backend/.env` from the template and fill in your values:

```bash
cp backend/.env.example backend/.env
```

```env
DATABASE_URL=postgresql+asyncpg://user:8asdf1ispass@localhost:5433/interview
SECRET_KEY=<generate one — see below>
LLM_API_KEY=<your Gemini API key>
```

Generate a `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Database (Docker → migrate → seed)

Start PostgreSQL (from the project root):
```bash
docker compose up -d
```

Create the tables and seed the reference bank (from `backend/`):
```bash
cd backend
uv run alembic upgrade head
uv run python scripts/seed_references.py
```
The seeder should report `Seeded 99 references.`

### 4. Backend server

From `backend/`:
```bash
uv run uvicorn app.main:app --reload
```
API runs at **http://localhost:8000** — interactive docs at **http://localhost:8000/docs**.

### 5. Frontend

From `frontend/` (in a second terminal):
```bash
cd frontend
npm install
npm run dev
```
App runs at **http://localhost:5173** (pinned — the backend's CORS only allows this origin).

## Usage

1. Open **http://localhost:5173**.
2. **Register** an account, then **log in**.
3. **New Interview** → pick a language, candidate level, interviewer style, and correction mode (optionally paste a résumé / JD).
4. Answer the questions; the interviewer grades and probes each one.
5. **Finish** to generate the report, or reopen any past interview from **History**.

## Project structure

```
AI-Interview-Simulator/
├── backend/
│   ├── app/
│   │   ├── auth/          # register / login / me
│   │   ├── interview/     # the interview engine (probe, bank, llm, service, router)
│   │   ├── core/          # config, security
│   │   ├── database/      # models, session
│   │   └── main.py
│   ├── alembic/           # migrations
│   └── scripts/           # seed_references.py (reference-bank importer)
├── frontend/              # React + Vite app
├── data/                  # reference-bank source files
└── docker-compose.yml     # PostgreSQL
```

## Notes

- **Gemini free-tier limits:** the free tier allows ~5 requests/minute per model. Each interview turn is one LLM call, so answer at a natural pace — rapid-fire answers can hit a temporary rate limit (the app returns a 503 and no data is lost; just retry).
- **Ports:** Postgres `5433`, backend `8000`, frontend `5173`. Start order: Docker → backend → frontend.
- **Reset the database:** `docker compose down -v` wipes the volume; re-run the migrate + seed steps afterward.
