import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

from app.database.models import RoleEnum


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: RoleEnum
    is_verified: bool


class TokenPair(BaseModel):
    access_token: str
    #refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str