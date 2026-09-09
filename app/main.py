from fastapi import FastAPI, Request
import time
from contextlib import asynccontextmanager

from app.core.db import engine, Base
from app.models.user import User
from app.models.sessions import Session
from app.models.otp import OTP

from app.core.redis import redis
from app.workers.queue import init_queue, close_queue

from app.routes.auth import router as auth_route


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


    await init_queue()

    yield

    await close_queue()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def measure_request_time(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start

    print(f"{request.method} {request.url.path} " f"took {elapsed * 1000:.2f} ms")

    return response


app.include_router(auth_route)


@app.get("/")
def jjjsj():
   
    return (f"dsalajdkakdnk")
