from app.utils.email_templates import send_otp_email

async def send_otp_emails(ctx, email: str, otp: str):
    print(f"Sending OTP {otp} to {email}")

    await send_otp_email(email, otp)
