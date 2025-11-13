from app.enums import GenerationStatus, PBNGenerationStatus
from app.utils import UnitOfWork


async def get_count_in_progress() -> int:
    async with UnitOfWork() as uow:
        num = await uow.cluster.get_count(status__in=GenerationStatus.unable_to_restart_statuses())

        if not num:
            num = await uow.pbn.get_count(status__not_in=PBNGenerationStatus.able_to_restart_statuses())

        return num
