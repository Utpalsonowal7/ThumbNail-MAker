from app.utils.otp import generate_otp
from app.utils.otpKey import otp_key
from app.utils.response import success_response
from app.workers import queue

from app.core.redis import redis
from app.schemas.user import Email

import time


async def send_otp(email: Email):
    start = time.perf_counter()
    key = otp_key(email)
    otp = generate_otp()

    await queue.redis_pool.enqueue_job("send_otp_emails", email, otp)
    await redis.set(key, otp, ex=300)

    print(f"ARQ enqueue: {(time.perf_counter() - start) * 1000:.2f} ms")
    return success_response(message="✅ Otp send successfully")
