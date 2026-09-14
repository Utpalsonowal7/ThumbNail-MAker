from pydantic import BaseModel, EmailStr, Field


class CreateUser(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(
        min_length=4,
        max_length=128,
    )


class Email(BaseModel):
    email: EmailStr


class VerifyOTP(BaseModel):
    email: EmailStr
    otp: str


class LoginUser(BaseModel):
    email: EmailStr
    password: str


class PsssToken(BaseModel):
    token: str


class ResetPassword(BaseModel):
    token: str
    password: str
