from arq import create_pool
from arq.connections import RedisSettings

from app.config import REDIS_URL

redis_pool = None


async def init_queue():
    global redis_pool

    redis_pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))


async def close_queue():
    if redis_pool:
        await redis_pool.close()
