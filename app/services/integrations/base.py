from typing import Any

from pydantic import BaseModel

from app.models import Integration
from app.utils import ABCUnitOfWork


class IntegrationBaseService:
    repository: str = "integration"
    default_filter: dict = {}

    async def get_one_or_none(self, unit_of_work: ABCUnitOfWork, **filters: Any) -> Integration | None:
        filters = {**self.default_filter, **filters}

        async with unit_of_work:
            repository = getattr(unit_of_work, self.repository)
            return await repository.get_one_or_none(**filters)

    async def delete(self, unit_of_work: ABCUnitOfWork, **filters: Any) -> None:
        filters = {**self.default_filter, **filters}

        async with unit_of_work:
            repository = getattr(unit_of_work, self.repository)
            await repository.delete(**filters)

    async def get_multi(self, unit_of_work: ABCUnitOfWork, **filters: Any) -> list[Integration]:
        filters = {**self.default_filter, **filters}

        async with unit_of_work:
            repository = getattr(unit_of_work, self.repository)
            return await repository.get_multi(**filters)

    async def update(self, unit_of_work: ABCUnitOfWork, data: BaseModel | dict, **filters: Any) -> Integration:
        filters = {**self.default_filter, **filters}

        async with unit_of_work:
            repository = getattr(unit_of_work, self.repository)
            db_obj = await repository.get_one_or_none(**filters)

            await self.prepare_update(db_obj, data)

            data = data.model_dump() if isinstance(data, BaseModel) else data

            for key, value in data.items():
                setattr(db_obj, key, value)

            await unit_of_work.session.commit()
            await unit_of_work.session.refresh(db_obj)

        return db_obj

    async def prepare_update(self, obj: Integration, data: BaseModel | dict) -> None:
        """Do some preparation before updating the object."""
        pass
