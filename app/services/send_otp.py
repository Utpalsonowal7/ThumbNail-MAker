from app.utils.otp import generate_otp
from app.utils.otpKey import otp_key
from app.utils.response import success_response
from app.workers import queue
from fastapi import BackgroundTasks
from app.core.redis import redis
from app.utils.email_templates import send_otp_email
from app.utils.rate_limiter import rate_limit
from fastapi import HTTPException
# from app.schemas.user import Email

import time


async def send_otp(email: str, background_tasks: BackgroundTasks):
    start = time.perf_counter()

    await rate_limit(
        key=f"rate:otp:{email}",
        limit=3,
        window=300,
    )

    key = otp_key(email)

    existOtp = redis.get(otp_key(email))
    
    if existOtp:
        raise HTTPException(status_code=400, detail="Email already sent, check your email")
    
    otp = generate_otp()

    # await queue.redis_pool.enqueue_job("send_otp_emails", email, otp)
    background_tasks.add_task(send_otp_email, email, otp)
    await redis.set(key, otp, ex=300)

    print(f"ARQ enqueue: {(time.perf_counter() - start) * 1000:.2f} ms")
    return success_response(message="✅ Otp send successfully")
