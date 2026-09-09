from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from app.core.db import get_session
from app.schemas.user import CreateUser
from app.services.auth import register_user
from app.services.send_otp import send_otp

router = APIRouter(prefix='/auth', tags=["Auth"])

@router.post("/register", status_code=201)
async def register(
     user_data: CreateUser,
     db: AsyncSession = Depends(get_session)
):
     return await register_user(db, user_data)

@router.post("/send-otp", status_code=200)
async def send(email: EmailStr):
    return await send_otp(email)
