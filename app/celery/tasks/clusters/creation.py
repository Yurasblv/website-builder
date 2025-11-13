import asyncio
import pickle
from typing import Any

from pydantic import UUID4

from app.celery import celery_app
from app.enums import ClusterEventEnum, GenerationStatus
from app.models import Cluster
from app.schemas import XMindmapBase
from app.schemas.cluster.base import ClusterCreate
from app.services.next.xmind import XMindGeneratorService
from app.utils import UnitOfWorkNoPool, enqueue_global_message


@celery_app.task(name="cluster-creation", queue="clusters")
def cluster_creation_task(cluster_id: UUID4, user_id: UUID4, data_pickle: bytes, file_data_pickle: bytes) -> None:
    """
    Celery task for cluster creation that replaces the FastStream implementation.

    Args:
        cluster_id: The ID of the cluster to be created.
        user_id: The ID of the user creating the cluster.
        data_pickle: Pickled data for cluster creation.
        file_data_pickle: Pickled file data for cluster creation.
    """

    from app.services.generation.cluster.structure import ClusterStructureGenerator

    data: ClusterCreate = pickle.loads(data_pickle)
    file_data: list[XMindmapBase] = pickle.loads(file_data_pickle)
    Generator = ClusterStructureGenerator(user_id=user_id, cluster_id=cluster_id, data=data)

    async def _run() -> None:
        async with Generator as service:
            await service.build_cluster_structure(file_data=file_data)

    with asyncio.Runner() as runner:
        runner.run(_run())


@celery_app.task(name="cluster-creation-success", queue="clusters")
def cluster_creation_success_task(cluster_id: str, user_id: str) -> None:
    """
    Celery task for cluster creation success.

    Args:
        cluster_id: The ID of the cluster that was successfully created.
        user_id: The ID of the user who created the cluster.
    """

    async def _run() -> None:
        await enqueue_global_message(
            event=ClusterEventEnum.STATUS_CHANGED,
            object_id=cluster_id,
            object_type="cluster",
            status=GenerationStatus.STEP2,
            user_id=user_id,
        )
        await enqueue_global_message(event=ClusterEventEnum.CREATED, cluster_id=cluster_id, user_id=user_id)

        async with UnitOfWorkNoPool() as uow:
            cluster = await uow.cluster.get_one(id=cluster_id)

        if not cluster.xmind:
            await XMindGeneratorService.generate(cluster_id=cluster_id)

    with asyncio.Runner() as runner:
        runner.run(_run())


@celery_app.task(name="cluster-creation-failure", queue="clusters")
def cluster_creation_failure_task(request: Any, exc: Any, traceback: Any, cluster_id: str, user_id: str) -> None:
    """
    Celery task for cluster creation failure.

    Args:
        request: The request object containing task details.
        exc: The exception raised during the task.
        traceback: The traceback of the exception.
        cluster_id: The ID of the cluster that failed to create.
        user_id: The ID of the user who attempted to create the cluster.
    """

    from app.services.storages import storage

    async def _run() -> None:
        async with UnitOfWorkNoPool() as uow:
            cluster: Cluster = await uow.cluster.get_one(id=cluster_id)

        if cluster.xmind:
            await storage.delete_file(cluster.xmind)

        async with UnitOfWorkNoPool() as uow:
            await uow.cluster.delete(id=cluster_id)

        await enqueue_global_message(event=ClusterEventEnum.DELETED, cluster_id=cluster_id, user_id=user_id)

    with asyncio.Runner() as runner:
        runner.run(_run())
