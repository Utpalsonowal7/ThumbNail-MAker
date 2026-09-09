from pydantic import BaseModel, EmailStr


class CreateUser(BaseModel):
    name: str
    email: EmailStr
    password: str | None = None

class Email(BaseModel):
    email: EmailStr

class VerifyOTP(BaseModel):
    email: EmailStr
    otp: str