from datetime import datetime, timedelta, timezone
import jwt

from app.config import JWT_ALGORITHM, JWT_ACCESS_TOKEN_SECRECT, JWT_REFRESH_TOKEN_SECRET,JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS

def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=int(JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, JWT_ACCESS_TOKEN_SECRECT, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        days=int(JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, JWT_REFRESH_TOKEN_SECRET, algorithm=JWT_ALGORITHM
    )
    return encoded_jwt


def create_auth_tokens(data: dict) -> dict:
   
    return {
        "access_token": create_access_token(data),
        "refresh_token": create_refresh_token(data),
    }
