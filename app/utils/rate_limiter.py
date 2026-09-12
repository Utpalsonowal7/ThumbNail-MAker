import time

from fastapi import HTTPException

from app.core.redis import redis


async def rate_limit(
    key: str,
    limit: int,
    window: int,
):
    now = time.time()
    window_start = now - window

  
    await redis.zremrangebyscore(
        key,
        0,
        window_start,
    )

   
    count = await redis.zcard(key)

    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
        )

    
    await redis.zadd(
        key,
        {str(now): now},
    )

  
    await redis.expire(key, window)
