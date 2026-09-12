from urllib.parse import urlencode

from fastapi import HTTPException, Request, Response, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from httpx import request
import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
import secrets
import httpx
from hashlib import  sha256
from secrets import token_urlsafe

from app.models.user import User
from app.models.sessions import Session
from app.schemas.user import CreateUser, VerifyOTP, LoginUser, Email
from app.utils.email_templates import send_reset_password_email
from app.utils.jwt import create_auth_tokens, create_access_token, decode_refresh_token
from app.core.redis import redis
from app.utils.otpKey import otp_key
from app.utils.response import success_response
from app.utils.cookie_options import (
    ACCESS_TOKEN_COOKIE_OPTIONS,
    REFRESH_TOKEN_COOKIE_OPTIONS,
)
from app.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    GOOGLE_PROVIDER_URI,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GITHUB_REDIRECT_URI,
    GITHUB_AUTH_URI,
    GITHUB_TOKEN_URI,
    GITHUB_USER_URI,
    GITHUB_USER_EMAILS_URI,
)


FRONTEND_LOGIN_ERROR_URL="https://thumbnail-maker-frontend.vercel.app/login?error="
FRONTEND_DASHBOARD_URL = "http://127.0.0.1:5500/t.html"
password_hash = PasswordHash.recommended()


async def _set_auth_cookies(
    response: Response, req: Request, user_id: str, db: AsyncSession
):
    tokens = create_auth_tokens({"sub": str(user_id)})

    session = Session(
        userId=user_id,
        refreshToken=tokens["refresh_token"],
        expiresAt=datetime.now(timezone.utc) + timedelta(days=30),
        userAgent=req.headers.get("user-agent"),
        ipAddress=req.client.host if req.client else None,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        **ACCESS_TOKEN_COOKIE_OPTIONS,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        **REFRESH_TOKEN_COOKIE_OPTIONS,
    )


async def register_user(db: AsyncSession, user_data: CreateUser, response: Response, request: Request):
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    hash_pass = password_hash.hash(user_data.password) if user_data.password else None

    new_user = User(name=user_data.name, email=user_data.email, password=hash_pass)

    db.add(new_user)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while registering the user")
    
    await db.refresh(new_user)

    await _set_auth_cookies(response, request, new_user.id, db)

    return success_response(
        message="Registration successful. Please verify your email.",
        data={"id": new_user.id, "name": new_user.name, "email": new_user.email},
    )


async def verify_user(data: VerifyOTP, db: AsyncSession):
    key = otp_key(data.email)
    stored_otp = await redis.get(key)

    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP has expired or is invalid")

    if stored_otp.decode("utf-8") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    await db.commit()
    await db.refresh(user)

    await redis.delete(key) 

    return success_response(
        message="OTP verified successfully.",
        data={"id": user.id, "name": user.name, "email": user.email},
    )


async def login_user(data: LoginUser, db: AsyncSession, response: Response):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not password_hash.verify(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(
            status_code=403, detail="Please verify your email before logging in"
        )

    await _set_auth_cookies(response, request, user.id, db, request)

    return success_response(
        message="Logged in successfully.",
        data={"id": user.id, "name": user.name, "email": user.email},
    )


async def refresh_access_token(request: Request, response: Response, db: AsyncSession):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    try:
        payload = decode_refresh_token(refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, detail="Refresh token expired, please log in again"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(
        select(Session).where(Session.refresh_token == refresh_token)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=401, detail="Session not found, please log in again"
        )

    if session.expires_at < datetime.now(timezone.utc):
        await db.delete(session)
        await db.commit()
        raise HTTPException(
            status_code=401, detail="Session expired, please log in again"
        )

    tokens = create_auth_tokens({"sub": str(user_id)})

    session.refresh_token = tokens["refresh_token"]
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    await db.commit()

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        **ACCESS_TOKEN_COOKIE_OPTIONS,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        **REFRESH_TOKEN_COOKIE_OPTIONS,
    )

    return success_response(message="Access token refreshed.")


async def logout_user(request: Request, response: Response, db: AsyncSession):
    refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        result = await db.execute(
            select(Session).where(Session.refresh_token == refresh_token)
        )
        session = result.scalar_one_or_none()
        if session:
            await db.delete(session)
            await db.commit()

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")

    return success_response(message="Logged out successfully.")


async def google_login_redirect(
    request: Request, response: Response
) -> RedirectResponse:
    state = secrets.token_urlsafe(32)

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    query = urlencode(params)
    url = f"{GOOGLE_AUTH_URI}?{query}"

    redirect_response = RedirectResponse(url=url)
    redirect_response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    return redirect_response


async def google_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: AsyncSession,
) -> RedirectResponse:
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or cookie_state != state:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}invalid_state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URI,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}token_exchange_failed")

    google_access_token = token_resp.json().get("access_token")

    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            GOOGLE_PROVIDER_URI,
            headers={"Authorization": f"Bearer {google_access_token}"},
        )

    if userinfo_resp.status_code != 200:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}userinfo_failed")

    profile = userinfo_resp.json()

    google_id = profile["id"]
    email = profile.get("email")
    name = profile.get("name") 
    avatar = profile.get("picture")
    email_verified = profile.get("verified_email", False)

    if not email or not email_verified:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}email_not_verified")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        if user.provider == "EMAIL":
            return RedirectResponse(
                url=f"{FRONTEND_LOGIN_ERROR_URL}account_exists_use_email_login"
            )
    else:
        user = User(
            name=name,
            email=email,
            password=None,
            isEmailVerified=email_verified,
            provider="GOOGLE",
            providerId=google_id,
            avatar=avatar,
        )
        db.add(user)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}account_conflict")

        await db.refresh(user)

    redirect_response = RedirectResponse(url=FRONTEND_DASHBOARD_URL)
    await _set_auth_cookies(redirect_response, request, user.id, db)

    return redirect_response


async def github_login_redirect() -> RedirectResponse:
    state = secrets.token_urlsafe(32)

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": state,
    }
    query = urlencode(params)
    url = f"{GITHUB_AUTH_URI}?{query}"

    redirect_response = RedirectResponse(url=url)
    redirect_response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    return redirect_response


async def github_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession,
) -> RedirectResponse:
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or cookie_state != state:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}invalid_state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URI,
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
        )

    if token_resp.status_code != 200:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}token_exchange_failed")

    token_data = token_resp.json()
    github_access_token = token_data.get("access_token")

    if not github_access_token:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}token_exchange_failed")

    auth_headers = {
        "Authorization": f"Bearer {github_access_token}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(GITHUB_USER_URI, headers=auth_headers)

    if user_resp.status_code != 200:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}userinfo_failed")

    profile = user_resp.json()
    print(f"GitHub profile: {profile}")
    github_id = str(profile["id"])
    name = profile.get("name") or profile.get("login")
    avatar = profile.get("avatar_url")
    email = profile.get("email")

    if not email:
        async with httpx.AsyncClient() as client:
            emails_resp = await client.get(GITHUB_USER_EMAILS_URI, headers=auth_headers)

        if emails_resp.status_code == 200:
            emails = emails_resp.json()
            primary = next(
                (e for e in emails if e.get("primary") and e.get("verified")), None
            )
            if not primary:
                primary = next((e for e in emails if e.get("verified")), None)
            if primary:
                email = primary.get("email")

    if not email:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}email_not_verified")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        if user.provider == "EMAIL":
            return RedirectResponse(
                url=f"{FRONTEND_LOGIN_ERROR_URL}account_exists_use_email_login"
            )
    else:
        user = User(
            name=name,
            email=email,
            password=None,
            isEmailVerified=True,
            provider="GITHUB",
            providerId=github_id,
            avatar=avatar,
        )
        db.add(user)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return RedirectResponse(url=f"{FRONTEND_LOGIN_ERROR_URL}account_conflict")

        await db.refresh(user)

    print(user)
    redirect_response = RedirectResponse(url=FRONTEND_DASHBOARD_URL)
    await _set_auth_cookies(redirect_response, request, user.id, db)

    return redirect_response


async def change_password(
    email: Email,
    background_task: BackgroundTasks,
    db: AsyncSession,
    req:Request
):
    result = await db.execute(select(User).where(User.email == email.email))

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

  
    token = token_urlsafe(32)

  
    hash_token = sha256(token.encode()).hexdigest()

  
    key = f"password-reset:{email.email}"

    await redis.set(
        key,
        hash_token,
        ex=600,  # 10 minutes
    )

   
    reset_url = (
    f"{req.url.scheme}://{req.url.netloc}"
    f"/api/auth/reset-password/{token}"
   )

    background_task.add_task(
        send_reset_password_email,
        email.email,
        reset_url,
    )

    return {
        "message": "Password reset link sent",
    }
