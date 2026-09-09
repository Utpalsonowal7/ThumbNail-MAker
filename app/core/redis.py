from redis.asyncio import Redis
from app.config import REDIS_URL

redis = Redis.from_url(
    REDIS_URL
)

