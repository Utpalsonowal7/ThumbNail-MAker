import asyncio
import time
from app.core.redis import redis  # import your existing async client only


async def test_ping():
    for _ in range(5):
        start = time.perf_counter()
        await redis.ping()
        print(f"PING: {(time.perf_counter() - start) * 1000:.2f} ms")


if __name__ == "__main__":
    asyncio.run(test_ping())
