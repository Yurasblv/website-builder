from abc import abstractmethod
from typing import Any

from redis import Redis

from app.db.redis import redis_pool


class GeneratorBase:
    def __init__(self) -> None:
        self.redis: Redis = None

    async def _init(self) -> "GeneratorBase":
        self.redis = await redis_pool.get_redis()
        return self

    @abstractmethod
    async def _set_generation_params(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def prepare_for_generation(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def generate(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def _run_test_generation(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def run_dev_generation(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def finalize_generation(self, *args: Any, **kwargs: Any) -> Any: ...
