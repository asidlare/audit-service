from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.config import Config
from app.routers import router
from app.services.database import QuorumUnavailableError, db


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

    # Global exception handler for QuorumUnavailableError
    @server.exception_handler(QuorumUnavailableError)
    async def quorum_unavailable_handler(request: Request, exc: QuorumUnavailableError):
        """
        Global handler for QuorumUnavailableError.

        Returns HTTP 503 Service Unavailable when Cassandra QUORUM cannot be achieved.
        This typically occurs when too many nodes are down and consistency requirements
        cannot be satisfied.
        """
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Service temporarily unavailable",
                "detail": str(exc),
                "retry_after": 30
            },
            headers={"Retry-After": "30"}
        )

    server.include_router(router, prefix="/api_v1")
    return server


app = init_app()
