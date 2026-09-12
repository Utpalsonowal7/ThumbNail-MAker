# import asyncio

# asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


from arq.connections import RedisSettings

from app.config import REDIS_URL
from app.workers.tasks.email import send_otp_emails
from app.workers.tasks.thumbnail import generate_thumbnail


class WorkerSettings:
    functions = [
        send_otp_emails,
        generate_thumbnail,
    ]

    redis_settings = RedisSettings.from_dsn(REDIS_URL)
