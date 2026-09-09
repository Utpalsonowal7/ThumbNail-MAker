from fastapi import HTTPException
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import CreateUser
from app.schemas.user import VerifyOTP
from app.utils.jwt import create_auth_tokens
from app.core.redis import redis
from app.utils.otpKey import otp_key
from app.utils.response import success_response

password_hash = PasswordHash.recommended()


async def register_user(db: AsyncSession, user_data: CreateUser):

    result = await db.execute(select(User).where(User.email == user_data.email))

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    hash_pass = password_hash.hash(user_data.password)

    new_user = User(name=user_data.name, email=user_data.email, password=hash_pass)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return success_response(
        message="Registration successful. Please verify your email.",
        data={"id": new_user.id, "name": new_user.name, "email": new_user.email},
    )

async def verify_user(data: VerifyOTP, db: AsyncSession):
    key = otp_key(data.email)
    stored_otp = await redis.get(key)

    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP has expired or is invalid")
 
    if stored_otp.decode('utf-8') != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    await db.commit()

    return success_response(
        message="OTP verified successfully.",
    )
