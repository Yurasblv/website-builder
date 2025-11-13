import asyncio

from redis.asyncio import Redis, connection
from redis.asyncio.client import PubSub

from app.core import settings


class RedisPool:
    def __init__(self) -> None:
        self.instances: dict[asyncio.AbstractEventLoop, Redis] = dict()
        self.url = settings.redis.url
        self.max_connections = settings.redis.MAX_CONNECTIONS

    async def get_redis(self) -> Redis:
        loop = asyncio.get_event_loop()

        if loop not in self.instances:
            pool = connection.ConnectionPool.from_url(self.url, max_connections=self.max_connections)
            self.instances[loop] = Redis(connection_pool=pool)

        return self.instances[loop]

    async def aclose(self) -> None:
        loop = asyncio.get_event_loop()

        if loop in self.instances:
            await self.instances[loop].aclose()
            _ = self.instances.pop(loop)

    async def config_pubsub(self) -> PubSub:
        redis = await self.get_redis()
        await redis.config_set("notify-keyspace-events", "Ex")

        pubsub = redis.pubsub()
        await pubsub.psubscribe("__keyevent@0__:expired")

        return pubsub

    async def collect_keys(self, key: str) -> list[bytes]:
        redis = await self.get_redis()
        cursor = "0"
        pattern = f"{key}*"
        keys_collected = []

        while cursor != 0:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=settings.redis.count_to_collect)
            keys_collected.extend(keys)

        return keys_collected

    async def remove_key_hard(self, key: str) -> None:
        loop = asyncio.get_event_loop()

        if loop in self.instances:
            keys = []
            redis = self.instances[loop]

            async for key in redis.scan_iter(f"{key}*"):
                keys.append(key)

            await redis.delete(*keys)


redis_pool = RedisPool()
