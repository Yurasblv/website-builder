from logging import LogRecord

import sentry_sdk
from loguru import logger
from loguru._defaults import LOGURU_FORMAT
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.langchain import LangchainIntegration
from sentry_sdk.integrations.logging import _IGNORED_LOGGERS, EventHandler
from sentry_sdk.integrations.loguru import Integration, LoggingLevels
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration

from app.core import settings
from app.enums import ExecutionMode


class CustomLoguruEventHandler(EventHandler):
    def _can_record(self, record: LogRecord) -> bool:
        if record.name in _IGNORED_LOGGERS:
            return False

        if record.exc_info is None:
            return True

        exc_type, *_ = record.exc_info

        if not exc_type:
            return True

        # filter sending exceptions into sentry
        if not getattr(exc_type, "sentry_record", True):
            return False

        if issubclass(exc_type, RuntimeError):
            logger.error("RuntimeError: {exc_type}", exc_type=exc_type)
            return False

        return True


class CustomLoguruIntegration(Integration):
    identifier = "custom_loguru_integration"

    @staticmethod
    def setup_once() -> None:
        logger.add(
            CustomLoguruEventHandler(),
            level=LoggingLevels.ERROR.value,
            format=LOGURU_FORMAT,
        )


def init_sentry() -> None:
    if settings.EXECUTION_MODE == ExecutionMode.PRODUCTION:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.STAGE,
            integrations=[
                AioHttpIntegration(),
                AsyncPGIntegration(record_params=settings.include_in_schema),
                CustomLoguruIntegration(),
                FastApiIntegration(),
                HttpxIntegration(),
                LangchainIntegration(),
                RedisIntegration(),
                ThreadingIntegration(),
            ],
            release=settings.VERSION,
        )


def init_sentry_worker() -> None:
    if settings.EXECUTION_MODE == ExecutionMode.PRODUCTION:
        sentry_sdk.init(
            dsn=settings.SENTRY_WORKER_DSN,
            environment=settings.STAGE,
            integrations=[
                AioHttpIntegration(),
                AsyncPGIntegration(record_params=settings.include_in_schema),
                CeleryIntegration(),
                CustomLoguruIntegration(),
                HttpxIntegration(),
                LangchainIntegration(),
                RedisIntegration(),
                ThreadingIntegration(),
            ],
            release=settings.VERSION,
        )
