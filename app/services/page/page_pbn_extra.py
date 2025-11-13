from pydantic import UUID4

from app.models import PagePBNExtra
from app.schemas.page.pbn_page import PBNExtraPageCommon
from app.schemas.user_info import UserInfoRead
from app.utils import ABCUnitOfWork

from .base import PageServiceBase


class PBNExtraPageService(PageServiceBase):
    @staticmethod
    async def convert_pbn_extra_page_common(page: PagePBNExtra) -> PBNExtraPageCommon:
        """
        Transform db PageCluster object into BlogPageCommon schema
            and downloading content from OVH S3 storage.

        Args:
            page: db page record

        Returns:
            BlogPageCommon schema
        """

        return PBNExtraPageCommon.model_validate(page)

    async def get_page_json(
        self, unit_of_work: ABCUnitOfWork, *, page_id: UUID4, pbn_id: UUID4, user_id: UUID4
    ) -> PBNExtraPageCommon:
        """
        Get single page by identifier.

        Args:
            unit_of_work
            page_id: page id
            pbn_id: pbn id
            user_id: user id

        Returns:
            BlogPageCommon schema with db PageBlog data
        """

        async with unit_of_work:
            await unit_of_work.pbn.get_one(id=pbn_id, user_id=user_id)

            page: PagePBNExtra = await unit_of_work.page_pbn_extra.get_one(
                join_load_list=[unit_of_work.page_pbn_extra.pbn_load],
                id=page_id,
                pbn_id=pbn_id,
            )
        return await self.convert_pbn_extra_page_common(page)

    @staticmethod
    async def create_snapshot(
        unit_of_work: ABCUnitOfWork, *, pbn_id: UUID4, user: UserInfoRead = None, user_id: UUID4 = None
    ) -> None:
        raise NotImplementedError
