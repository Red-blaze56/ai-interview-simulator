from uuid import UUID
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import CurrentUser, DBSession
from app.database.models import Interview
from app.interview.service import _get_full

async def get_owned_interview(interview_id: UUID, user: CurrentUser, db:DBSession) -> Interview :
    interview = await _get_full(db, interview_id)
    if interview is None or interview.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview Not found")
    return interview

OwnedInterview = Annotated[Interview, Depends(get_owned_interview)]