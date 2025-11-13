import asyncio
import json
from typing import Any
from uuid import uuid4

from redis.asyncio import Redis

from app.core import settings
from app.db.redis import redis_pool
from app.enums import MicroServiceType


class RequestService:
    def __init__(self, service_type: MicroServiceType) -> None:
        self.request_channel = f"{settings.microservices.request_channel}:{service_type}"
        self.response_channel = f"{settings.microservices.response_channel}:{service_type}"
        self.redis: Redis | None = None

    async def send(self, data: dict) -> Any:
        """
        Sends a request with the specified data to the Redis request channel, waits for a token, and processes
        the response once the request is completed.

        Args:
            data: The data to be sent in the request.

        Returns:
            The response data returned from the microservice.

        Raises:
            Exception: If no tokens are available even after waiting.
        """

        self.redis = await redis_pool.get_redis()

        task_id = str(uuid4())

        request_data = {"task_id": task_id, "data": data}
        await self.redis.publish(self.request_channel, json.dumps(request_data))

        try:
            return await asyncio.wait_for(self._wait_for_response(task_id), timeout=30)  # Set your desired timeout here
        except asyncio.TimeoutError:
            return {"status": "error", "message": "Request timed out"}

    async def _wait_for_response(self, task_id: str) -> Any:
        """
        Waits for a response to the request sent, by listening to the Redis response channel
        Args:
             task_id: The unique identifier of the request
        Returns:
            The response data associated with the task_id.
        """

        pubsub = self.redis.pubsub()  # type:ignore[union-attr]

        await pubsub.subscribe(self.response_channel)

        async for message in pubsub.listen():
            if message["type"] == "message":
                response_data = json.loads(message["data"])

                if response_data["task_id"] == task_id:
                    return response_data["data"]
