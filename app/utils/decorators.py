import asyncio
import functools
from functools import partial, wraps
from typing import Any, Callable

from langsmith import traceable
from loguru import logger
from openai import OpenAIError

from app.core import settings


def retry_image_request(max_retries: int = 5, retry_delay: int = 5) -> Any:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            retry_count = max_retries

            while True:
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    retry_count -= 1

                    if retry_count < 0:
                        raise e

                    logger.warning(
                        f"Image generation failed (attempt {max_retries - retry_count}): {str(e)}. "
                        f"Retrying in {retry_delay} seconds..."
                    )
                    await asyncio.sleep(retry_delay)

        return wrapper

    return decorator


def retry_gpt_request(times: int = settings.ai.OPENAI_RETRY_ATTEMPTS, exc: tuple = ()) -> Any:
    """
    Decorator to retry GPT API requests in case of specified exceptions.

    Args:
        times: Number of times to retry.
        exc: exceptions to retry.

    Raises:
        Any exceptions that are not handled by retries.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while attempt < times:
                try:
                    return await func(*args, **kwargs)

                except exc as e:
                    logger.exception(f"An OpenAI API error occurred: {e}\nkwargs: {kwargs}")
                    await asyncio.sleep(attempt * settings.ai.OPENAI_RETRY_WAIT_SECONDS)
                    attempt += 1

                except OpenAIError as e:
                    logger.exception(f"OpenAIError error occurred: {e}\nkwargs: {kwargs}")

        return wrapper

    return decorator


def retry_element_processing(func: Callable[..., Any] | None = None, *, max_attempts: int = 3) -> Any:
    """
    Decorator to retry data creation for specified element if previous data not correctly generated.
    """
    from app.schemas.elements.cluster_pages.base import ElementContent

    if func is None:
        return partial(retry_element_processing, max_attempts=max_attempts)

    @wraps(func)
    async def wrapper(self, element_content: "ElementContent", *args, **kwargs) -> Any:  # type:ignore[no-untyped-def]
        attempt = 0
        while attempt < max_attempts:
            content: "ElementContent" = await func(self, element_content=element_content, *args, **kwargs)
            # TODO: retry only with error ( by adding ElementProcessingException)
            if isinstance(content, ElementContent) and content.processed:
                return content
            if isinstance(content, list) and content:
                return content
            attempt += 1
        return element_content

    return wrapper


def traceable_generate(tags: list[str]) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            metadata = {
                "cluster_id": str(self.page_metadata.cluster_id),
                "page_name": self.page_metadata.topic_name,
                "language": self.language,
                "target_country": self.target_country,
                "user_email": self.user_email,
            }
            decorated_func = traceable(tags=tags, metadata=metadata)(func)
            return decorated_func(self, *args, **kwargs)

        return wrapper

    return decorator
