from typing import Any

from pydantic import UUID4
from sqlalchemy.sql.functions import concat, func

from app.models import UserInfo
from app.repository.base import PaginateRepositoryMixin, SQLAlchemyRepository
from app.schemas.utils.paginator import PaginatedOutput


class UserRepository(PaginateRepositoryMixin, SQLAlchemyRepository):
    model = UserInfo

    async def deactivate(self, user_id: UUID4) -> UserInfo:
        user = await self.get_one(id=user_id)
        user.is_active = False

        return user

    async def paged_list(self, **filters: Any) -> PaginatedOutput:
        search_fields = [
            self.model.email,
            func.TRIM(concat(self.model.first_name, " ", self.model.last_name)),
            func.TRIM(concat(self.model.last_name, " ", self.model.first_name)),
        ]

        return await super().paged_list(search_fields=search_fields, **filters)
