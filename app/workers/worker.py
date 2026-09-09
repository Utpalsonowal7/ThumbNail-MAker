from arq.connections import RedisSettings

from app.config import REDIS_URL
from app.workers.tasks.email import send_otp_emails


class WorkerSettings:
    functions = [
        send_otp_emails,
    ]

    redis_settings = RedisSettings.from_dsn(REDIS_URL)
