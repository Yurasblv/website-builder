import pickle
from typing import Any

from celery import group
from loguru import logger
from pydantic import UUID4

from app.enums import PBNGenerationStatus, TransactionStatus
from app.schemas.pbn import PBNRefresh
from app.schemas.user_info import UserInfoRead
from app.services.ai.base import AIBase
from app.services.generation.base import GeneratorBase
from app.services.page.page_cluster import ClusterPageService
from app.services.pbn import PBNService
from app.services.transaction import TransactionRefundService, TransactionSpendService
from app.utils import UnitOfWorkNoPool


class PBNRefreshGenerator(PBNService, GeneratorBase):
    def __init__(self) -> None:
        super().__init__()

        self.obj: PBNRefresh = None
        self.tx_id: str = None
        self.ai: AIBase = None
        self.request_key = "request_refreshing_pbns_{user_id}"

    @staticmethod
    async def _init() -> "PBNRefreshGenerator":
        self = PBNRefreshGenerator()
        await super(PBNRefreshGenerator, self)._init()
        self.ai = AIBase()

        return self

    async def prepare_for_generation(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def _set_generation_params(self, tx_id: UUID4, obj: PBNRefresh) -> None:
        self.tx_id = tx_id
        self.obj = obj

    async def rollback_changes(self) -> None:
        await self.set_pbn_status(id_=self.obj.id, status=self.obj.status)

        async with UnitOfWorkNoPool() as uow:
            spend_tx = await TransactionSpendService.cancel(
                uow, transaction_id=self.tx_id, info="Error during PBN refresh."
            )

            await TransactionRefundService.create(
                uow,
                user_id=self.obj.user_id,
                spend_tx_id=spend_tx.id,
                amount=spend_tx.amount,
                object_type=spend_tx.object_type,
                info="Refund for PBN refreshing.",
            )
        logger.exception(f"PBN {self.obj.id} was refresh failed.")

    async def finalize_generation(self) -> None:
        async with UnitOfWorkNoPool() as uow:
            tx = await uow.transaction.get_one(id=self.tx_id)
            tx.status = TransactionStatus.COMPLETED

        logger.success(f"PBN {self.obj.id} was successfully refreshed.")

    async def refresh_pbn_pages(self) -> None:
        await self.set_pbn_status(id_=self.obj.id, status=PBNGenerationStatus.GENERATING)

        for cluster in self.obj.clusters:
            await ClusterPageService.upgrade_cluster_version(
                user_id=str(self.obj.user_id), user_email=self.obj.user_email, cluster_id=str(cluster.id)
            )

    async def generate(self) -> None:
        await self.refresh_pbn_pages()
        await self.rebuild_pbn_clusters(obj=self.obj)
        await self.redeploy_pbn_cluster(obj=self.obj)

    async def _run_test_generation(self, user: UserInfoRead, pbn_list: list[UUID4]) -> None:
        raise NotImplementedError

    async def run_dev_generation(self, user: UserInfoRead, data: list[PBNRefresh]) -> None:
        from app.celery.tasks.pbns import pbn_refresh_finish_task, pbn_refresh_task

        key = self.request_key.format(user_id=user.id)
        await self.redis.set(name=key, value=1)

        tasks_group = group([pbn_refresh_task.s(data=pickle.dumps(pbn)) for pbn in data])
        callback = pbn_refresh_finish_task.s(user_id=str(user.id), key=key)
        tasks_group.apply_async(link=callback, queue="pbn")
