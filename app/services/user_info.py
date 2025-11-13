from pydantic import UUID4, EmailStr

from app.models import UserInfo
from app.schemas.user_info import UserInfoUpdate
from app.utils import ABCUnitOfWork


class UserInfoService:
    @staticmethod
    async def _check_user_exists(unit_of_work: ABCUnitOfWork, email: EmailStr | str) -> bool:
        async with unit_of_work:
            return bool(await unit_of_work.user.get_one_or_none(email=email))

    @staticmethod
    async def get(unit_of_work: ABCUnitOfWork, *, user_id: UUID4) -> UserInfo:
        """
        Get user by id

        Args:
            unit_of_work
            user_id: User id to get

        Returns:
            User info
        """

        async with unit_of_work:
            return await unit_of_work.user.get_one(id=user_id)

    @staticmethod
    async def delete(unit_of_work: ABCUnitOfWork, *, user_id: UUID4) -> None:
        """
        Delete current user account

        Args:
            unit_of_work
            user_id: Current user id
        """

        async with unit_of_work:
            await unit_of_work.user.deactivate(user_id=user_id)

    @staticmethod
    async def update(unit_of_work: ABCUnitOfWork, *, user_id: UUID4, obj_in: UserInfoUpdate) -> UserInfo:
        """
        Update user

        Args:
            unit_of_work
            user_id: User id to update
            obj_in: User data

        Returns:
            Updated user
        """

        data: dict = obj_in.model_dump(exclude_none=True)
        async with unit_of_work:
            user = await unit_of_work.user.get_one(id=user_id)

            if data:
                for k, v in data.items():
                    setattr(user, k, v)

                await unit_of_work.session.commit()
                await unit_of_work.session.refresh(user)
            return user
