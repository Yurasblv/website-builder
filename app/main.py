from contextlib import asynccontextmanager
from typing import AsyncGenerator

import nest_asyncio
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk import capture_exception

from app.api import api_router
from app.core import init_sentry, settings, swagger_router
from app.db.redis import redis_pool

nest_asyncio.apply()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    init_sentry()
    await redis_pool.get_redis()

    yield

    await redis_pool.aclose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=None,
    debug=settings.DEBUG,
    docs_url=None,
    redoc_url=None,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Prometheus metrics
Instrumentator().instrument(app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    capture_exception(exc)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )


app.include_router(swagger_router, tags=["Swagger"])
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        forwarded_allow_ips="*",
    )
