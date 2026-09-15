from fastapi import FastAPI, Request, APIRouter, HTTPException, status
import time
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    print(
        f"HTTP ERROR | "
        f"{request.method} {request.url.path} | "
        f"{exc.status_code} | "
        f"{exc.detail}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
        },
        headers=exc.headers,
    )


origins = [
    "http://localhost:3000",
    "https://yourdomain.com",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
    "https://thu-phi.vercel.app",
]

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


api_router = APIRouter(prefix="/api")

api_router.include_router(auth_route)
api_router.include_router(thumbnail_router)

app.include_router(api_router)


@app.get("/", status_code=status.HTTP_200_OK)
def health_check():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "uptime_seconds": round(time.time() - START_TIME, 2),
        },
    )
