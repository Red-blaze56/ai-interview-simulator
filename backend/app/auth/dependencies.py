import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.security import decode_access_token
from app.database.models import User
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

DBSession = Annotated[AsyncSession, Depends(get_db)]

async def get_current_user( token: Annotated[str, Depends(oauth2_scheme)], db: DBSession) -> User :
    claims = decode_access_token(token)
    if claims is None:
        raise HTTPException( status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError):
        raise HTTPException( status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException( status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user 

CurrentUser = Annotated[User,Depends(get_current_user)]
    