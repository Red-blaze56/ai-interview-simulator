from fastapi import FastAPI, APIRouter
from sqlalchemy import text

from app.auth.dependencies import DBSession
from app.auth.router import auth_router
from app.interview.router import interview_router

app = FastAPI(
    title="AI Interview Simulator",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(interview_router)

@app.get("/health", tags=["ops"])
async def health(db: DBSession):
    """Checks its dependencies rather than just returning 200 — a health check
    that cannot fail tells your load balancer nothing."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}