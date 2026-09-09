from datetime import datetime, timedelta

from fastapi import HTTPException
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.otp import OTP
from app.schemas.user import CreateUser
from app.utils.otp import generate_otp
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

    await db.flush()

    otp_code = generate_otp()

    new_otp = OTP(
        userId=new_user.id,
        code=otp_code,
        expiresAt=datetime.utcnow() + timedelta(minutes=10),
    )

    db.add(new_otp)

    await db.commit()

  
    # await send_otp_email(email=new_user.email, name=new_user.name, otp=otp_code)

    return success_response(
        message="Registration successful. Please verify your email.",
        data={"id": new_user.id, "name": new_user.name, "email": new_user.email},
    )
