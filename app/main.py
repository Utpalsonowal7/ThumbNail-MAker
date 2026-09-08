from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.db import engine, Base
from app.models.user import User
from app.models.sessions import Session
from app.models.otp import OTP

from app.routes.auth import router as auth_route


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield


app = FastAPI(lifespan=lifespan)

app.include_router(auth_route)


@app.get("/")
def jjjsj():
    print(f"hello")
    return (f"dsalajdkakdnk")