from brevo import AsyncBrevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)

from app.config import BREVO_KEY

client = AsyncBrevo(api_key=BREVO_KEY)


async def send_otp_email(email: str, otp: str):
    result = await client.transactional_emails.send_transac_email(
        subject="Verify your email",
        html_content=f"""
        <html>
            <body>
                <h2>Email Verification</h2>

                <p>Your OTP is:</p>

                <h1>{otp}</h1>

                <p>This OTP will expire in 10 minutes.</p>

                <p>If you did not request this, please ignore this email.</p>
            </body>
        </html>
        """,
        sender=SendTransacEmailRequestSender(
            name="Utpal Sonowal", email="utpal@utpal.utpx.in"
        ),
        to=[
            SendTransacEmailRequestToItem(
                email=email,
            )
        ],
    )

    return result
