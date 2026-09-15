import time
from urllib.parse import urlencode

from fastapi import HTTPException, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError
from httpx import request
import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
import secrets
import httpx
from hashlib import sha256
from secrets import token_urlsafe

from app.models.user import User
from app.models.sessions import Session
from app.schemas.user import CreateUser, VerifyOTP, LoginUser, Email, PsssToken
from app.utils.email_templates import send_reset_password_email
from app.utils.jwt import create_auth_tokens, create_access_token, decode_refresh_token
from app.core.redis import redis
from app.utils.key_maker import otp_key, password_reset
from app.utils.response import success_response
from app.utils.rate_limiter import rate_limit
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
    FRONT_END_URL,
)

password_hash = PasswordHash.recommended()


async def _set_auth_cookies(
    response: Response, req: Request, user_id: int, db: AsyncSession
):
    tokens = create_auth_tokens({"sub": str(user_id)})
    print(tokens)
    session = Session(
        userId=user_id,
        refreshToken=tokens["refresh_token"],
        expiresAt=datetime.now(timezone.utc) + timedelta(days=30),
        userAgent=req.headers.get("user-agent"),
        ipAddress=req.client.host if req.client else None,
    )

    db.add(session)
    try:
        await db.commit()
       
    except Exception as e:
         await db.rollback()
      
         raise
    
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


async def register_user(
    db: AsyncSession, user_data: CreateUser,  request: Request
):
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    hash_pass = password_hash.hash(user_data.password) if user_data.password else None

    new_user = User(name=user_data.name, email=user_data.email, password=hash_pass,  isEmailVerified=True)

    db.add(new_user)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="An error occurred while registering the user"
        )

    await db.refresh(new_user)
    response = JSONResponse(
    content=success_response(
        message="Registration successful. Please verify your email.",
        data={"id": new_user.id, "name": new_user.name, "email": new_user.email},
    )
)

    await _set_auth_cookies(response, request, new_user.id, db)

    return response


async def verify_user(data: VerifyOTP, db: AsyncSession):
    key = otp_key(data.email)
    stored_otp = await redis.get(key)

    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP has expired or is invalid")

    if stored_otp.decode("utf-8") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    return success_response(
        message="OTP verified successfully.",
        data=data.email,
    )


async def login_user(data: LoginUser, db: AsyncSession, response: Response, request: Request):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not password_hash.verify(data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not user.isEmailVerified:
        raise HTTPException(
            status_code=403, detail="Please verify your email before logging in"
        )

    await _set_auth_cookies(response, request, user.id, db)

    return success_response(
        message="Logged in successfully.",
        data={"id": user.id, "name": user.name, "email": user.email},
    )


async def refresh_access_token(request: Request, response: Response, db: AsyncSession):
    refresh_token = request.cookies.get("refresh_token")
    print(refresh_token)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    try:
        payload = decode_refresh_token(refresh_token)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=401, detail="Refresh token expired, please log in again"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(
        select(Session).where(Session.refreshToken == refresh_token)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=401, detail="Session not found, please log in again"
        )

    if session.expiresAt < datetime.now(timezone.utc):
        await db.delete(session)
        await db.commit()
        raise HTTPException(
            status_code=401, detail="Session expired, please log in again"
        )

    tokens = create_auth_tokens({"sub": str(user_id)})

    session.refreshToken = tokens["refresh_token"]
    session.expiresAt = datetime.now(timezone.utc) + timedelta(days=30)
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
            select(Session).where(Session.refreshToken == refresh_token)
        )
        session = result.scalar_one_or_none()
        if session:
            await db.delete(session)
            await db.commit()

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")

    return success_response(message="Logged out successfully.")


async def google_login_redirect() -> RedirectResponse:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }

    url = f"{GOOGLE_AUTH_URI}?{urlencode(params)}"

    return RedirectResponse(
        url=url,
        status_code=302,
    )


async def google_callback(
    code: str,
    response:Response,
    request: Request,
    db: AsyncSession,
) -> RedirectResponse:

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
        raise HTTPException(
            status_code=400,
            detail="Google token exchange failed",
        )

    google_access_token = token_resp.json().get("access_token")

    if not google_access_token:
        raise HTTPException(
            status_code=400,
            detail="Google access token missing",
        )

    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            GOOGLE_PROVIDER_URI,
            headers={"Authorization": f"Bearer {google_access_token}"},
        )

    if userinfo_resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail="Failed to get Google user",
        )

    profile = userinfo_resp.json()

    google_id = profile["id"]
    email = profile.get("email")
    name = profile.get("name")
    avatar = profile.get("picture")
    email_verified = profile.get("verified_email", False)

    if not email or not email_verified:
        raise HTTPException(
            status_code=400,
            detail="Google email is not verified",
        )

    result = await db.execute(select(User).where(User.email == email))

    user = result.scalar_one_or_none()

    if user:
        if user.provider == "EMAIL":
            raise HTTPException(
                status_code=400,
                detail="Account already exists with email/password",
            )
    else:
        user = User(
            name=name,
            email=email,
            password=None,
            isEmailVerified=True,
            provider="GOOGLE",
            providerId=google_id,
            avatar=avatar,
        )

        db.add(user)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Account creation failed",
            )

        await db.refresh(user)

    redirect_response = RedirectResponse(
        url=f"{FRONT_END_URL}dashboard",
        status_code=302,
    )

    await _set_auth_cookies(
        redirect_response,
        request,
        user.id,
        db,
    )


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
        return RedirectResponse(url=f"{FRONT_END_URL}invalid_state")

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
        return RedirectResponse(url=f"{FRONT_END_URL}token_exchange_failed")

    token_data = token_resp.json()
    github_access_token = token_data.get("access_token")

    if not github_access_token:
        return RedirectResponse(url=f"{FRONT_END_URL}token_exchange_failed")

    auth_headers = {
        "Authorization": f"Bearer {github_access_token}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(GITHUB_USER_URI, headers=auth_headers)

    if user_resp.status_code != 200:
        return RedirectResponse(url=f"{FRONT_END_URL}userinfo_failed")

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
        return RedirectResponse(url=f"{FRONT_END_URL}email_not_verified")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        if user.provider == "EMAIL":
            return RedirectResponse(
                url=f"{FRONT_END_URL}account_exists_use_email_login"
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
            return RedirectResponse(url=f"{FRONT_END_URL}account_conflict")

        await db.refresh(user)

    print(user)
    redirect_response = RedirectResponse(url=f"{FRONT_END_URL}dashboard")
    await _set_auth_cookies(redirect_response, request, user.id, db)

    return redirect_response


async def change_password(
    email: Email, background_task: BackgroundTasks, db: AsyncSession, req: Request
):

    await rate_limit(email.email, 1 , 600, "sent check email of not get try after 10 min")
    result = await db.execute(select(User).where(User.email == email.email))

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    token = token_urlsafe(32)
    hash_token = sha256(token.encode()).hexdigest()
    key = password_reset(hash_token)

    await redis.set(
        key,
        user.email,
        ex=600,
    )

    reset_url = (
        f"{req.url.scheme}://{req.url.netloc}" f"/api/auth/reset-password/{token}"
    )

    background_task.add_task(
        send_reset_password_email,
        email.email,
        reset_url,
    )

    return {
        "message": "Password reset link sent",
    }


async def verify_reset_password_token(user_token: str):
    hash_token = sha256(user_token.encode()).hexdigest()
    key = password_reset(hash_token)

    email = await redis.get(key)

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired password reset token",
        )

    if isinstance(email, bytes):
        email = email.decode()

    return email


async def reset_password(
    db: AsyncSession,
    token: str,
    password: str,
):

    email = await verify_reset_password_token(token)

    result = await db.execute(select(User).where(User.email == email))

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    user.password = password_hash.hash(password)

    await db.commit()

    hash_token = sha256(token.encode()).hexdigest()
    key = password_reset(hash_token)

    await redis.delete(key)

    return {
        "message": "Password reset successfully",
    }
