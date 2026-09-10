from fastapi import FastAPI, Request
import time
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import engine, Base
from app.models.user import User
from app.models.sessions import Session
from app.models.otp import OTP
from app.models.jobs import Job
from app.models.thumbnails import Thumbnail

from app.core.redis import redis
from app.workers.queue import init_queue, close_queue

from app.routes.auth import router as auth_route
from app.routes.thumbnail import router as thumbnail_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


    await init_queue()

    yield

    await close_queue()


app = FastAPI(lifespan=lifespan)

origins = ["http://localhost:3000", "https://yourdomain.com", "http://127.0.0.1:5500"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def measure_request_time(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start

    print(f"{request.method} {request.url.path} " f"took {elapsed * 1000:.2f} ms")

    return response


app.include_router(auth_route)
app.include_router(thumbnail_router)


@app.get("/")
def jjjsj():
   
    return (f"dsalajdkakdnk")
