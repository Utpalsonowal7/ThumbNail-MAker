from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import CreateUser, VerifyOTP, LoginUser
from app.services.auth import (
    register_user,
    verify_user,
    login_user,
    logout_user,
    refresh_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    user_data: CreateUser,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    return await register_user(db, user_data, response)


@router.post("/verify-otp")
async def verify_otp(data: VerifyOTP, db: AsyncSession = Depends(get_session)):
    return await verify_user(data, db)


@router.post("/login")
async def login(
    data: LoginUser,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    return await login_user(data, db, response)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    return await refresh_access_token(request, response)


@router.post("/logout")
async def logout(response: Response):
    return await logout_user(response)


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "is_verified": current_user.is_verified,
    }
