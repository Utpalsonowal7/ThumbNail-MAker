from fastapi import APIRouter, Depends, Request, Response, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import CreateUser, PsssToken, ResetPassword, VerifyOTP, LoginUser
from app.services.auth import (
    change_password,
    github_callback,
    github_login_redirect,
    google_callback,
    google_login_redirect,
    register_user,
    reset_password,
    verify_reset_password_token,
    verify_user,
    login_user,
    logout_user,
    refresh_access_token,
)
from app.services.send_otp import send_otp
from app.schemas.user import Email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    user_data: CreateUser,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    return await register_user(db, user_data, request)


@router.post("/verify-otp")
async def verify_otp(data: VerifyOTP, db: AsyncSession = Depends(get_session)):
    return await verify_user(data, db)


@router.post("/login")
async def login(
    data: LoginUser,
    response: Response,
    rqe: Request,
    db: AsyncSession = Depends(get_session),
):
    return await login_user(data, db, response, rqe)


@router.post("/refresh")
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_session)
):
    return await refresh_access_token(request, response, db)


@router.post("/logout")
async def logout(
    response: Response, req: Request, db: AsyncSession = Depends(get_session)
):
    return await logout_user(req, response, db)


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "avataar": current_user.avatar or "https://placehold.net/avatar-2.svg",
        "is_verified": current_user.isEmailVerified,
    }


@router.get("/google")
async def google_login():
    return await google_login_redirect()


@router.get("/google/callback")
async def google_auth_callback(
    code: str,
    res:Response,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    return await google_callback(
        code,
        res,
        request,
        db,
    )


@router.get("/github")
async def github_login():
    return await github_login_redirect()


@router.get("/github/callback")
async def github_auth_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    return await github_callback(code, state, request, db)


@router.post("/send-otp")
async def send_otp_route(email: Email, background_tasks: BackgroundTasks):
    return await send_otp(str(email.email), background_tasks)


@router.post("/forgot-password")
async def forgot_password(
    req: Request,
    email: Email,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    return await change_password(
        email=email, background_task=background_tasks, db=db, req=req
    )


@router.get("/reset-password/{token}")
async def verify_reset_password(token: str):
    await verify_reset_password_token(token)

    return RedirectResponse(url=f"http://127.0.0.1:5500/t.html?token={token}")


@router.post("/reset-password")
async def reset_password_route(
    data: ResetPassword,
    db: AsyncSession = Depends(get_session),
):
    return await reset_password(
        db=db,
        token=data.token,
        password=data.password,
    )
