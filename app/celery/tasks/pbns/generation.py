import asyncio
import pickle
import time

from celery import Task
from celery.result import GroupResult

from app.celery import celery_app
from app.schemas.pbn import PBNGenerate
from app.services.generation.pbn import PBNPagesGenerator


@celery_app.task(name="pbn_generate_task", queue="pbn")
def pbn_generate_task(total_plan_pages: int, spend_tx_id: str, data: bytes) -> None:
    """
    Generate a PBN (Private Blog Network) site.

    Args:
        total_plan_pages: The total number of planned pages.
        spend_tx_id: The transaction ID for spending.
        data: The pickled metadata for PBN generation (PBNGenerate).
    """

    time.sleep(3)  # wait for task registration
    metadata: PBNGenerate = pickle.loads(data)

    async def _run() -> None:
        instance = await PBNPagesGenerator._init()
        await instance._set_generation_params(total_plan_pages=total_plan_pages, metadata=metadata)

        try:
            await instance.generate()

        except Exception as e:
            await instance.rollback_pbn_generation(e, spend_tx_id)

    with asyncio.Runner() as runner:
        runner.run(_run())


@celery_app.task
def pbn_finalize_generation_handler_task(
    generation_key: str, user_id: str, money_site_id: str, money_site_url: str, tx_id: str
) -> None:
    """
    Finalize the PBN generation process.

    Args:
        generation_key: The key for the PBN generation.
        user_id: The ID of the user.
        money_site_id: The ID of the money site.
        money_site_url: The URL of the money site.
        tx_id: The transaction ID.
    """

    coro = PBNPagesGenerator.finalize_generation(
        generation_key=generation_key,
        user_id=user_id,
        money_site_id=money_site_id,
        money_site_url=money_site_url,
        tx_id=tx_id,
    )

    with asyncio.Runner() as runner:
        runner.run(coro)


# TODO: Deprecated
def pbn_cancel_tasks(task: Task) -> None:
    group_result: GroupResult = GroupResult.restore(task.request.group)

    if not getattr(group_result, "children", None):
        return

    for task in group_result.children:
        if task.id != task.request.id:
            task.revoke(terminate=True, signal="SIGKILL")
