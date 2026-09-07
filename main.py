from fastapi import FastAPI
from contextlib import asynccontextmanager

from db import engine, Base
from models.user import User
from models.sessions import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield


app = FastAPI(lifespan=lifespan)
