import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import CurrentUser, DBSession
from app.auth.schemas import TokenPair, UserCreate, UserOut
from app.auth.service import authenticate, get_user_by_email, create_user
from app.core.security import create_access_token
from app.database.models import RoleEnum


auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DBSession):
    if await get_user_by_email(db,payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already Registered")
    user = await create_user(db, email = payload.email, password=payload.password, role=RoleEnum.USER)
    return user

@auth_router.post("/login", response_model=TokenPair)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db:DBSession):
    user = await authenticate(db, email=form.username, password=form.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Email or Password")
    return TokenPair(access_token=create_access_token(user.id))
    
@auth_router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user

    