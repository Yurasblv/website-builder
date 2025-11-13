import asyncio
from typing import Any

from loguru import logger

from app.celery import celery_app
from app.enums import ClusterEventEnum, GenerationStatus, SpendType, TransactionStatus, WebsocketEventEnum
from app.schemas.transactions import TransactionRefundCreate
from app.services.page import ClusterPageService
from app.services.storages import storage
from app.utils import UnitOfWorkNoPool, enqueue_global_message


@celery_app.task(name="cluster-refreshing", queue="clusters")
def cluster_refreshing_task(user_id: str, user_email: str, cluster_id: str, **_: Any) -> list[str]:
    """
    Celery task for cluster refreshing.

    Args:
        user_id: The ID of the user who initiated the task.
        user_email: The email of the user who initiated the task.
        cluster_id: The ID of the cluster to be finalized.

        _: Additional keyword arguments, including:
            transaction_id: The ID of the transaction to be finalized.
            keyword: The keyword associated with the cluster.

    WSocket Event:
        - ClusterEventEnum.REFRESHING

    Returns:
        List of file paths to be deleted after refreshing.
    """

    async def _run() -> list[str]:
        await enqueue_global_message(
            event=ClusterEventEnum.STATUS_CHANGED,
            object_id=cluster_id,
            object_type="cluster",
            status=GenerationStatus.GENERATING,
            user_id=user_id,
        )
        return await ClusterPageService.upgrade_cluster_version(
            user_id=user_id, user_email=user_email, cluster_id=cluster_id
        )

    with asyncio.Runner() as runner:
        release_to_del = runner.run(_run())

    return release_to_del


@celery_app.task(name="cluster-refreshing-success", queue="clusters")
def cluster_refreshing_success_task(
    release_to_del: list[str], user_id: str, user_email: str, cluster_id: str, transaction_id: str, keyword: str
) -> None:
    """
    Celery task for finalizing cluster refreshing.

    Args:
        release_to_del: List of file paths to be deleted after refreshing.
        user_id: The ID of the user who initiated the task.
        user_email: The email of the user who initiated the task.
        cluster_id: The ID of the cluster to be finalized.
        transaction_id: The ID of the transaction to be finalized.
        keyword: The keyword associated with the cluster.

    WSocket Event:
        - ClusterEventEnum.REFRESHED
    """

    async def _run() -> None:
        await enqueue_global_message(
            event=ClusterEventEnum.GENERATING,
            user_id=user_id,
            cluster_id=cluster_id,
            generation_key=f"generating_cluster_{cluster_id}",
            progress=100,
            message=f"Cluster {cluster_id} refreshed successfully.",
        )

        if release_to_del:  # TODO: fix after checking
            if isinstance(release_to_del, list):
                logger.warning(f"Deleting files as list: {release_to_del}")
                await storage.delete_files(*release_to_del)

            elif isinstance(release_to_del, tuple):
                logger.warning(f"Deleting files as tuple: {release_to_del}")
                await storage.delete_files(*release_to_del[0])

        async with UnitOfWorkNoPool() as uow:
            await uow.transaction.update(dict(status=TransactionStatus.COMPLETED), id=transaction_id)

        await enqueue_global_message(
            event=ClusterEventEnum.STATUS_CHANGED,
            object_id=cluster_id,
            object_type="cluster",
            status=GenerationStatus.GENERATED,
            user_id=cluster_id,
        )

        await enqueue_global_message(
            event=ClusterEventEnum.GENERATED,
            user_id=user_id,
            cluster_id=cluster_id,
            keyword=keyword,
            message="Cluster refreshed successfully.",
        )

    with asyncio.Runner() as runner:
        runner.run(_run())


@celery_app.task(name="cluster-refreshing-failure", queue="clusters")
def cluster_refreshing_failure_task(
    user_id: str, user_email: str, cluster_id: str, transaction_id: str, keyword: str
) -> None:
    """
    Celery task for handling failure during cluster refreshing.

    Args:
        user_id: The ID of the user who initiated the task.
        user_email: The email of the user who initiated the task.
        cluster_id: The ID of the cluster to be finalized.
        transaction_id: The ID of the transaction to be finalized.
        keyword: The keyword associated with the cluster.

    WSocket Event:
        - WebsocketEventEnum.ERROR
    """

    async def _run() -> None:
        async with UnitOfWorkNoPool() as uow:
            transaction = await uow.transaction.get_one(id=transaction_id)
            transaction.status = TransactionStatus.CANCELLED

            refund = TransactionRefundCreate(
                user_id=transaction.user_id,
                spend_tx_id=transaction.id,
                amount=transaction.amount,
                object_type=SpendType.REFRESH_CLUSTER_PAGE,
                info="Refund for cluster upgrade.",
            )
            await uow.transaction_refund.create(refund)

        await enqueue_global_message(
            event=ClusterEventEnum.STATUS_CHANGED,
            object_id=cluster_id,
            object_type="cluster",
            status=GenerationStatus.GENERATED,
            user_id=user_id,
        )
        await enqueue_global_message(
            event=WebsocketEventEnum.ERROR,
            user_id=user_id,
            message="Cluster refresh failed.",
        )

    with asyncio.Runner() as runner:
        runner.run(_run())
