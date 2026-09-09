from fastapi import HTTPException, Request, Response
import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import CreateUser, VerifyOTP, LoginUser
from app.utils.jwt import create_auth_tokens, create_access_token, decode_refresh_token
from app.core.redis import redis
from app.utils.otpKey import otp_key
from app.utils.response import success_response
from app.utils.cookie_options import (
    ACCESS_TOKEN_COOKIE_OPTIONS,
    REFRESH_TOKEN_COOKIE_OPTIONS,
)

password_hash = PasswordHash.recommended()


def _set_auth_cookies(response: Response, user_id: str):
    """Creates access + refresh tokens for a user and sets them as cookies."""
    tokens = create_auth_tokens({"sub": str(user_id)})

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


async def register_user(db: AsyncSession, user_data: CreateUser, response: Response):
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    hash_pass = password_hash.hash(user_data.password)

    new_user = User(name=user_data.name, email=user_data.email, password=hash_pass)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # TODO: enqueue OTP email job here via arq, same as your send_otp flow

    _set_auth_cookies(response, new_user.id)

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

    await redis.delete(key)  # OTP used, remove so it can't be replayed

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

    _set_auth_cookies(response, user.id)

    return success_response(
        message="Logged in successfully.",
        data={"id": user.id, "name": user.name, "email": user.email},
    )


async def refresh_access_token(request: Request, response: Response):
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

    new_access_token = create_access_token({"sub": user_id})

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        **ACCESS_TOKEN_COOKIE_OPTIONS,
    )

    return success_response(message="Access token refreshed.")


async def logout_user(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")
    return success_response(message="Logged out successfully.")
