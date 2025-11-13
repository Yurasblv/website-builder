import asyncio
import time
from collections import deque
from typing import Any, Coroutine

from loguru import logger
from sentry_sdk import capture_exception


class RPMSemaphore:
    def __init__(self, max_requests_per_minute: int) -> None:
        self.max_requests = max_requests_per_minute
        self.request_times: deque = deque()
        self.semaphore = asyncio.Semaphore(max_requests_per_minute)

    async def acquire(self) -> None:
        await self.semaphore.acquire()

        current_time = time.time()
        # Remove requests older than 1 minute
        while self.request_times and current_time - self.request_times[0] > 60:
            self.request_times.popleft()

        # If we're at the limit, wait until the oldest request is 1 minute old
        if len(self.request_times) >= self.max_requests:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self.request_times.append(current_time)

    def release(self) -> None:
        self.semaphore.release()


async def gather_concurrently(n: int, *coros: Any) -> Any:
    """
    Function for executing coroutines concurrently with a limit of n coroutines.

    Raises:
        Exception: if coroutine result had error
    Returns:
        result of all coroutines
    """
    semaphore = asyncio.Semaphore(n)

    async def call(coro: Coroutine) -> Any:
        async with semaphore:
            try:
                return await coro
            except Exception as e:
                logger.error(f"Exception occurred: {e}")
                capture_exception(e)

    return await asyncio.gather(*(call(coro) for coro in coros))
