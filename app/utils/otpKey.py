from pydantic import EmailStr


def otp_key(email: EmailStr):
    return f"otp:{email}"
