import json
from typing import Any
from uuid import UUID

from loguru import logger

from app.core import settings
from app.db.redis import redis_pool


async def enqueue_global_message(**kwargs: Any) -> None:
    """
    Enqueue a message to the global message queue.

    user_id: UUID of the user the message is intended for
    message: The message to be enqueued
    event: The event name
    """
    redis = await redis_pool.get_redis()
    queue_item = json.dumps(kwargs, default=lambda i: str(i) if isinstance(i, UUID) else i)
    logger.debug(f"Enqueueing message: {queue_item}")
    await redis.rpush(settings.message_queue.GLOBAL_QUEUE_NAME, queue_item)
