import asyncio
import pickle

from loguru import logger

from app.celery import celery_app
from app.models import Backlink
from app.schemas.backlink import BacklinkRead, PickledBacklinkRead
from app.services.pbn import PBNService
from app.utils import UnitOfWorkNoPool


@celery_app.task
def pbn_run_backlink_publish_task() -> None:
    """
    Schedule the task to publish backlinks.
    """

    async def _run() -> None:
        async with UnitOfWorkNoPool() as uow:
            db_backlinks = await uow.backlink.get_relevant_to_enable()
            for backlink in db_backlinks:
                data = BacklinkRead.init(backlink)

                backlink_publish_task.apply_async(kwargs=dict(data=pickle.dumps(data)))

    with asyncio.Runner() as runner:
        runner.run(_run())


@celery_app.task
def backlink_publish_task(data: PickledBacklinkRead) -> None:
    """
    Publish a backlink.

    Args:
        data: The pickled data of the BacklinkRead.
    """

    backlink: BacklinkRead = pickle.loads(data)

    async def _run() -> None:
        if await PBNService.enable_hidden_backlinks(backlink):
            async with UnitOfWorkNoPool() as uow:
                db_obj: Backlink = await uow.backlink.get_one(id=backlink.id)
                db_obj.is_visible = True
            logger.success(f"Backlink = {backlink.id} enabled.")

    with asyncio.Runner() as runner:
        runner.run(_run())
