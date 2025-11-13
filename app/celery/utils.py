import json
from typing import Any

from asgiref.sync import async_to_sync
from celery import Celery, Task, result
from loguru import logger
from sentry_sdk import capture_exception

# from app.core import settings
from app.core.exc import BaseWebSocketException
from app.db.redis import redis_pool
from app.enums import ExceptionAlias, QueueEventEnum, WebsocketEventEnum
from app.utils import enqueue_global_message


class CustomCelery(Celery):
    def task(self, *args: Any, **opts: Any) -> Task:
        """Custom task decorator that sets the queue name based on the task name.

        Args:
            *args: Positional arguments for the task.
            **opts: Keyword arguments for the task.

        Returns:
            Task: The decorated task.
        """
        if "name" not in opts and args:
            if getattr(args[0], "__name__", None):
                opts["name"] = args[0].__name__

        return super().task(*args, **opts)

    def send_task(self, *args: Any, **kwargs: Any) -> Any:
        res: result.AsyncResult = super().send_task(*args, **kwargs)

        self._print_result_info(res)

        return result

    @staticmethod
    def _print_result_info(res: result.AsyncResult) -> None:
        """Prints the result information of a task.

        Args:
            res (AsyncResult): The result object of the task.

        Returns:
            None
        """

        # if not settings.is_test_mode:
        #     return

        logger.debug(f"Task {res.name=}")
        logger.debug(f"Task {res.task_id=}")
        logger.debug(f"Task {res.status=}")
        logger.debug(f"Task {res.args=}")
        logger.debug(f"Task {res.kwargs=}")
        logger.debug(f"Task {res.queue=}")
        logger.debug(f"Task {res.worker=}")


class CeleryTask(Task):
    """Custom Celery task class that provides error handling and logging."""

    priority = 2  # Default priority for tasks from 0 to 9 where 0 is the highest priority.

    def on_failure(self, exc: Any, task_id: Any, args: Any, kwargs: Any, einfo: Any) -> None:
        """Error handler.

        This is run by the worker when the task fails.

        Args:
            exc (Exception): The exception raised by the task.
            task_id (str): Unique id of the failed task.
            args (Tuple): Original arguments for the task that failed.
            kwargs (Dict): Original keyword arguments for the task that failed.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """

        if isinstance(exc, BaseWebSocketException):
            logger.warning(repr(exc))
            return

        capture_exception(exc)

        if user_id := kwargs.get("user_id", None):
            func = async_to_sync(enqueue_global_message)
            func(event=WebsocketEventEnum.ERROR, user_id=user_id, msg=str(exc), alias=ExceptionAlias.UndefinedError)

    def on_retry(self, exc: Any, task_id: Any, args: Any, kwargs: Any, einfo: Any) -> None:
        """Retry handler.

        This is run by the worker when the task is to be retried.

        Arguments:
            exc (Exception): The exception sent to :meth:`retry`.
            task_id (str): Unique id of the retried task.
            args (Tuple): Original arguments for the retried task.
            kwargs (Dict): Original keyword arguments for the retried task.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """

        capture_exception(exc)


async def get_incoming_tasks(queue: str) -> dict[int, dict]:
    """
    Get incoming tasks from the queue

    Args:
        queue: Queue name

    Returns:
        Position and task data
    """

    redis = await redis_pool.get_redis()
    encoded_data: list[bytes] = await redis.lrange(queue, 0, -1)

    temp = [json.loads(data) for data in encoded_data]
    logger.debug(f"Current task count: {len(temp)}")

    return {position: json.loads(data.get("data", "{}")) for position, data in enumerate(temp, start=1)}


async def send_notification(tasks: dict) -> None:
    """
    Send notification to the user about his queue

    Args:
        tasks: Incoming tasks
    """

    for position, data in tasks.items():
        user_id = data.get("user_id", None)

        if user_id:
            continue

        await enqueue_global_message(
            event=QueueEventEnum.CHANGED,
            user_id=user_id,
            cluster_id=data.get("cluster_id", None),
            position=position,
        )
