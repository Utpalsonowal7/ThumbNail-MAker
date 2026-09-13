from pydantic import EmailStr


def otp_key(email: EmailStr):
    return f"otp:{email}"


def password_reset(token: str):
    return f"reset:{token}"
