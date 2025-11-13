import asyncio
import pickle
import time

from loguru import logger

from app.celery import celery_app
from app.core import settings
from app.db.redis import redis_pool
from app.enums import ExceptionAlias, SpendType, WebsocketEventEnum
from app.schemas.pbn import PBNRefresh
from app.services.generation.pbn import PBNRefreshGenerator
from app.services.transaction import TransactionSpendService
from app.utils import UnitOfWorkNoPool, enqueue_global_message


@celery_app.task
def pbn_refresh_task(data: bytes) -> None:
    """
    Refresh the PBN task.

    Args:
        data: The pickled PBNRefresh object.
    """

    time.sleep(3)  # wait for task registration TODO: user celery.signals.task_prerun

    async def _run() -> None:
        obj: PBNRefresh = pickle.loads(data)
        instance = await PBNRefreshGenerator._init()

        async with UnitOfWorkNoPool() as uow:
            tx = await TransactionSpendService.create(
                uow,
                user_id=obj.user_id,
                amount=settings.PAGE_REFRESH_PRICE * obj.pages_number,
                object_id=obj.id,
                object_type=SpendType.REFRESH_PBN,
            )

        await instance._set_generation_params(tx_id=tx.id, obj=obj)

        try:
            await instance.generate()
            await instance.finalize_generation()

            logger.success(f"PBN {instance.obj.id} was successfully refreshed.")

        except Exception as e:
            logger.exception(e)
            await instance.rollback_changes()

            await enqueue_global_message(
                event=WebsocketEventEnum.ERROR,
                user_id=obj.user_id,
                pbn_id=obj.id,
                alias=getattr(e, "_exception_alias", ExceptionAlias.UndefinedError),
            )

    with asyncio.Runner() as runner:
        runner.run(_run())


@celery_app.task
def pbn_refresh_finish_task(user_id: str, key: str) -> None:
    """
    Finish the PBN refresh task.

    Args:
        user_id: The ID of the user.
        key: The redis key of the refresh task.
    """

    async def _run() -> None:
        redis = await redis_pool.get_redis()
        await redis.delete(key)

        logger.info(f"Refresh PBN request for user {user_id} finished.")

    with asyncio.Runner() as runner:
        runner.run(_run())
