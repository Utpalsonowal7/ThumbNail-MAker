from fastapi import Request, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.core.db import get_session
from app.models.user import User
from app.utils.jwt import decode_access_token


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get("access_token")
    print(type(token))
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_access_token(token)
        print("payload : ", payload)
    except jwt.ExpiredSignatureError as e:
        print("JWT EXPIRED 1:", repr(e))
        raise HTTPException(status_code=401, detail="Access token expired")
    except jwt.InvalidTokenError as e:
        print("JWT INVALID 2:", repr(e))
        raise HTTPException(
        status_code=401,
        detail=f"Invalid token",
    )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
