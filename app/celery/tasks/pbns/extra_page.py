import asyncio
import pickle
from uuid import UUID

from loguru import logger
from sentry_sdk import capture_exception

from app.celery import celery_app
from app.db.redis import redis_pool
from app.schemas import UserInfoRead
from app.services.generation.pbn import PBNExtraPageGenerator


@celery_app.task
def pbn_extra_page_generate_task(user_info_bytes: bytes, pbn_id: str) -> None:
    """
    Generate extra pages for a PBN (Private Blog Network) site.

    Args:
        user_info_bytes: Serialized bytes of the UserInfo object.
        pbn_id: The ID of the PBN site.
    """

    user: UserInfoRead = pickle.loads(user_info_bytes)

    async def _run() -> None:
        instance = await PBNExtraPageGenerator._init()

        try:
            await instance.prepare_for_generation(user, pbn_id=UUID(pbn_id, version=4))
            await instance.generate()
            await instance.finalize_generation()

        except Exception as e:
            capture_exception(e)
            await instance.rollback_changes()
            logger.info(f"Revoked extra page generation task. PBN ID = {pbn_id}")

    with asyncio.Runner() as runner:
        runner.run(_run())


@celery_app.task
def pbn_extra_page_finalize_task(key: str, user_id: str) -> None:
    """
    Finalize the extra page generation process.

    Args:
        key: The key for the extra page generation.
        user_id: The ID of the user.
    """

    async def _run() -> None:
        redis = await redis_pool.get_redis()
        await redis.delete(key)

        logger.info(f"Finish extra page generation request for {user_id=}")

    with asyncio.Runner() as runner:
        runner.run(_run())
