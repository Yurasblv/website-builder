import asyncio
from typing import Any, Callable

from fastapi import HTTPException, status
from loguru import logger
from pydantic import UUID4

from app.enums import ExceptionAlias, WebsocketEventEnum


class LoggerMixin:
    log_level: str | None = "info"
    log_message_pattern: tuple | None = None

    def log_exception(self, detail: str = None) -> None:
        if self.log_level in {"debug", "info", "warning", "error", "critical", "exception"}:
            logger.name = self.__class__.__name__
            logger_method: Callable = getattr(logger, self.log_level)

            if self.log_message_pattern:
                log_message, *args = self.log_message_pattern
                formatted_args = [getattr(self, arg) for arg in args]
                logger_method(log_message, *formatted_args)
            else:
                logger_method(detail)


class BaseHTTPException(LoggerMixin, HTTPException):
    """
    Base class for all custom exceptions.
    *_pattern is a tuple with a message and arguments to format it. Example: ('{0} not found!', 'class_name')
    """

    _exception_alias: ExceptionAlias = None
    status_code: int = 400
    message_pattern: tuple[str, ...] | None = None
    sentry_record: bool = False

    def __init__(self, detail: str | dict[str, str] = None, headers: dict[str, str] = None, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

        if detail is None and self.message_pattern:
            message, *args = self.message_pattern
            formatted_args = [getattr(self, arg) for arg in args]
            detail = message.format(*formatted_args)

        self.log_exception(str(detail))

        detail = {
            "msg": f"{detail}",
            "alias": getattr(self, "_exception_alias", "UnknownCode"),
        }
        super().__init__(status_code=self.status_code, detail=detail, headers=headers)


class BaseWebSocketException(LoggerMixin, Exception):
    """
    Base class for websocket exceptions.
    """

    _exception_alias: ExceptionAlias = None
    message_pattern: tuple[str, ...] | None = None
    sentry_record: bool = False

    def __init__(self, user_id: str | UUID4, detail: str | dict[str, str] = None, **kwargs: Any) -> None:
        from app.utils.message_queue import enqueue_global_message

        for key, value in kwargs.items():
            setattr(self, key, value)

        if detail is None and self.message_pattern:
            message, *args = self.message_pattern
            formatted_args = [getattr(self, arg) for arg in args]
            detail = message.format(*formatted_args)

        self.log_exception(str(detail))

        _detail = dict(msg=detail)

        if self._exception_alias:
            _detail.update(alias=getattr(self, "_exception_alias", "UnknownCode"))

        super().__init__(detail)

        task = enqueue_global_message(event=WebsocketEventEnum.ERROR, user_id=user_id, **_detail)

        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(task, loop)


class BadRequestException(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST


class ObjectNotFoundException(BaseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    message_pattern = ("{0} not found", "class_name")
    log_message_pattern = ("{0} not found, statement= {1} ", "class_name", "statement")
    _exception_alias = ExceptionAlias.DBObjectNotFound


class ForeignKeyViolationException(BaseHTTPException):
    status_code = status.HTTP_409_CONFLICT
    message_pattern = ("You can't delete this {0}", "class_name")
    log_message_pattern = ("You can't delete this {0}, statement= {1}", "class_name", "statement")


class ObjectExistsException(BaseHTTPException):
    status_code = status.HTTP_409_CONFLICT
    message_pattern = ("{0} with this {1} already exists.", "class_name", "obj")


class DBConnectionException(BaseHTTPException):
    log_level = "error"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message_pattern = ("Connection to db refused",)
    sentry_record = True
