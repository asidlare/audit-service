from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import Config
from app.routers import router
from app.services.database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    hosts = Config.CASSANDRA_HOSTS
    db.connect(hosts)
    yield
    db.close()


def init_app():
    server = FastAPI(
        title="Audit Service",
        description="Async event logging system based on Cassandra",
        lifespan=lifespan
    )
    server.include_router(router, prefix="/api_v1")
    return server


app = init_app()
