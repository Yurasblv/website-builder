import asyncio

from app.celery import celery_app
from app.enums import ClusterEventEnum, GenerationStatus, WebsocketEventEnum
from app.services.cluster import ClusterStaticBuilder
from app.utils import UnitOfWorkNoPool, enqueue_global_message


async def _rollback(user_id: str, cluster_id: str) -> None:
    async with UnitOfWorkNoPool() as uow:
        cluster = await uow.cluster.get_one(id=cluster_id)
        cluster.status = GenerationStatus.GENERATED

    await enqueue_global_message(
        event=ClusterEventEnum.STATUS_CHANGED,
        object_id=cluster_id,
        object_type="cluster",
        status=GenerationStatus.BUILD_FAILED,
        user_id=user_id,
    )

    await enqueue_global_message(
        event=WebsocketEventEnum.ERROR, user_id=user_id, message=f"Cluster {cluster_id} building failed."
    )


async def _finalize(link: str, user_id: str, cluster_id: str) -> None:
    async with UnitOfWorkNoPool() as uow:
        cluster = await uow.cluster.get_one(id=cluster_id)
        cluster.link = link
        cluster.status = GenerationStatus.BUILT

    await enqueue_global_message(
        event=ClusterEventEnum.STATUS_CHANGED,
        object_id=cluster_id,
        object_type="cluster",
        status=GenerationStatus.BUILT,
        user_id=user_id,
    )

    await enqueue_global_message(
        event=ClusterEventEnum.BUILT,
        user_id=user_id,
        keyword=cluster.keyword,
        cluster_id=cluster_id,
        message=f"Cluster {cluster_id} built successfully.",
    )


async def _prepare(user_id: str, cluster_id: str) -> None:
    async with UnitOfWorkNoPool() as uow:
        cluster = await uow.cluster.get_one(id=cluster_id)
        cluster.status = GenerationStatus.BUILDING

    await enqueue_global_message(
        event=ClusterEventEnum.STATUS_CHANGED,
        object_id=cluster_id,
        object_type="cluster",
        status=GenerationStatus.BUILDING,
        user_id=user_id,
    )


@celery_app.task(name="cluster_building_task", queue="clusters")
def cluster_building_task(user_id: str, cluster_id: str) -> None:
    """
    Celery task for cluster building that replaces the FastStream implementation.

    Args:
        user_id: The ID of the user who initiated the task.
        cluster_id: The ID of the cluster to be built.
    """

    async def _run() -> None:
        try:
            await _prepare(user_id=user_id, cluster_id=cluster_id)
            builder = ClusterStaticBuilder(cluster_id=cluster_id, user_id=user_id)
            link = await builder.build()

            await _finalize(link=link, user_id=user_id, cluster_id=cluster_id)

        except Exception as e:
            await _rollback(user_id=user_id, cluster_id=cluster_id)
            raise e

    with asyncio.Runner() as runner:
        runner.run(_run())
