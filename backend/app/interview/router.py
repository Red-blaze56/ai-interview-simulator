from fastapi import APIRouter,status

from app.auth.dependencies import CurrentUser, DBSession
from app.interview import service
from app.interview.schemas import AnswerIn, AnswerResponse, InterviewCreate, InterviewOut
from app.interview.dependencies import OwnedInterview

interview_router = APIRouter(prefix="/interviews", tags=["interview"])

@interview_router.post("", response_model = InterviewOut, status_code = status.HTTP_201_CREATED)
async def create_interview(payload: InterviewCreate, user:CurrentUser, db:DBSession):
    return await service.create_interview(db, user_id=user.id, payload=payload)

@interview_router.post("/{interview_id}/answer", response_model=AnswerResponse)
async def submit_answer(payload: AnswerIn, interview: OwnedInterview, db: DBSession):
    full, evaluation, should_finish = await service.submit_answer(db, interview=interview, content=payload.content)
    return AnswerResponse(
        interview=InterviewOut.model_validate(full),
        evaluation=evaluation,
        should_finish=should_finish
    )