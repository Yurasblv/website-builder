import functools

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core import settings

engine = create_async_engine(
    url=settings.db.url,
    pool_recycle=settings.db.POOL_RECYCLE,
    pool_pre_ping=True,
    pool_size=settings.db.POOL_SIZE,
    max_overflow=settings.db.MAX_OVERFLOW,
    echo=settings.is_test_mode,
    echo_pool=settings.is_test_mode,
)

async_session = async_sessionmaker(engine, expire_on_commit=False)


def create_null_pool_engine() -> AsyncEngine:
    return create_async_engine(url=settings.db.url, poolclass=NullPool, echo=settings.is_test_mode)


@functools.lru_cache
def get_sessionmaker_without_pool() -> async_sessionmaker:
    null_pool_engine = create_null_pool_engine()
    return async_sessionmaker(bind=null_pool_engine, autoflush=False, expire_on_commit=False)
