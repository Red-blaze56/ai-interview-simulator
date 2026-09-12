import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, new_refresh_token, verify_password
from app.database.models import User, RoleEnum
from app.auth.schemas import TokenPair, UserCreate

async def get_user_by_email(db: AsyncSession, email:str) -> User | None :
    return await db.scalar(select(User).where(User.email==email))

async def create_user(db: AsyncSession, * , email:str, password:str, role: RoleEnum = RoleEnum.USER) -> User:
    user = User(
        email = email,
        hashed_password = hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate(db:AsyncSession, * , email:str, password:str) -> User | None :
    user = await get_user_by_email(db,email)
    if not user:
        hash_password(password)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user
