import asyncio

from loguru import logger
from pydantic import UUID4

from app.celery import celery_app
from app.services.generation.cluster_pages import ClusterGeneratorBuilder


@celery_app.task(name="cluster_generation_task", queue="clusters")
def cluster_generation_task(user_id: UUID4, user_email: str, cluster_id: UUID4) -> None:
    """
    Celery task for cluster generation that replaces the FastStream implementation.

    Args:
        user_id: The ID of the user.
        user_email: The email of the user.
        cluster_id: The ID of the cluster.
    """

    async def _run() -> None:
        instance = await ClusterGeneratorBuilder()._init()
        await instance.prepare_for_generation(user_id=user_id, user_email=user_email, cluster_id=cluster_id)

        try:
            await instance.generate()
            await instance.finalize_generation()

        except Exception as exception:
            logger.warning(exception)
            await instance.finalize_generation(exception=exception)

    with asyncio.Runner() as runner:
        runner.run(_run())
