from decimal import Decimal
from typing import Any

from pydantic import UUID4

from app.core.exc import NotEnoughBalanceForSpend
from app.enums import SpendType, TransactionStatus
from app.models import (
    Transaction,
    TransactionRefund,
    TransactionSpend,
)
from app.schemas.transactions import (
    TransactionFilters,
    TransactionRefundCreate,
    TransactionSpendCreate,
)
from app.schemas.user_info import UserInfoRead
from app.schemas.utils import Ordering, PaginatedOutput, PaginationFilter, Search
from app.utils import ABCUnitOfWork, UnitOfWork


class TransactionService:
    repository = "transaction"

    async def get_by_filters(
        self,
        unit_of_work: ABCUnitOfWork,
        *,
        filters: TransactionFilters,
        pagination: PaginationFilter,
        ordering: Ordering,
        search: Search,
        user: UserInfoRead = None,
    ) -> dict[str, Any]:
        """
        Get current user transactions by filters

        Args:
            unit_of_work
            filters: filters
            pagination: pagination
            ordering: ordering
            search: search
            user: current user

        Returns:
            list of TransactionResponse objects
        """

        data = (
            filters.model_dump(exclude_none=True)
            | pagination.model_dump()
            | ordering.model_dump()
            | search.model_dump()
        )
        if user:
            data["user_id"] = user.id

        async with unit_of_work:
            repository = getattr(unit_of_work, self.repository)
            output: PaginatedOutput[Transaction] = await repository.paged_list(**data)
            return output.model_dump()

    async def get_by_id(
        self, unit_of_work: ABCUnitOfWork, *, transaction_id: UUID4, user: UserInfoRead = None
    ) -> Transaction:
        """
        Get transaction by id

        Args:
            unit_of_work
            user: current user
            transaction_id: transaction id

        Returns:
            Transaction object

        """
        filters = dict(id=transaction_id)
        if user:
            filters["user_id"] = user.id

        async with unit_of_work:
            repository = getattr(unit_of_work, self.repository)
            return await repository.get_one(**filters)

    async def get_amount(
        self, unit_of_work: ABCUnitOfWork, *, filters: TransactionFilters, user: UserInfoRead = None
    ) -> Decimal:
        """
        Get sum of transactions amounts by filters

        Args:
            unit_of_work
            filters: filters
            user: current user

        Returns:
            sum of transactions amounts
        """

        data = filters.model_dump(exclude_none=True)
        if user:
            data["user_id"] = user.id

        async with unit_of_work:
            repository = getattr(unit_of_work, self.repository)
            return await repository.get_amount(**data)

    async def get_count(self, unit_of_work: ABCUnitOfWork, *, filters: TransactionFilters) -> int:
        """
        Get count of transactions by filters

        Args:
            unit_of_work
            filters: filters

        Returns:
            count of transactions
        """

        async with unit_of_work:
            repository = getattr(unit_of_work, self.repository)
            return await repository.get_count(**filters.model_dump(exclude_none=True))


class TransactionSpendService(TransactionService):
    repository = "transaction_spend"

    @staticmethod
    async def create(
        unit_of_work: UnitOfWork,
        *,
        user_id: UUID4,
        amount: Decimal,
        object_id: UUID4,
        object_type: SpendType,
        info: str = "",
    ) -> TransactionSpend:
        """
        Create transaction_spend transaction

        Args:
            unit_of_work: UnitOfWork
            user_id: current user id
            amount: transaction_spend amount
            object_id: object id
            object_type: object type
            info
        Raises:
            NotEnoughBalanceForSpend: if user has not enough balance for withdrawal

        Returns:
            Spend transaction

        """

        obj_in = TransactionSpendCreate(
            user_id=user_id, amount=amount, object_id=object_id, object_type=object_type, info=info
        )
        user = await unit_of_work.user.get_one(id=user_id)

        if user.balance < amount:
            raise NotEnoughBalanceForSpend(required_amount=amount, available_amount=user.balance)

        user.balance -= obj_in.amount
        return await unit_of_work.transaction_spend.create(obj_in=obj_in)

    @staticmethod
    async def cancel(unit_of_work: UnitOfWork, transaction_id: UUID4 | str, info: str) -> TransactionSpend:
        """
        Cancel Spend transaction

        Args:
            unit_of_work: UnitOfWork
            transaction_id: transaction id
            info: pattern for info
        """

        transaction = await unit_of_work.transaction_spend.get_one(id=transaction_id)
        user = await unit_of_work.user.get_one(id=transaction.user_id)
        user.balance += transaction.amount

        transaction.status = TransactionStatus.CANCELLED
        transaction.info = info

        return transaction


class TransactionRefundService(TransactionService):
    repository = "transaction_refund"

    @staticmethod
    async def create(
        unit_of_work: UnitOfWork,
        *,
        user_id: UUID4,
        spend_tx_id: UUID4,
        amount: Decimal,
        object_type: SpendType,
        status: TransactionStatus = TransactionStatus.COMPLETED,
        info: str = "",
    ) -> TransactionRefund:
        """
        Create transaction refund transaction

        Args:
            unit_of_work: UnitOfWork
            user_id: current user id
            spend_tx_id
            amount: transaction_spend amount
            object_type: object type
            status
            info
        """

        obj_in = TransactionRefundCreate(
            user_id=user_id, amount=amount, spend_tx_id=spend_tx_id, status=status, object_type=object_type, info=info
        )
        user = await unit_of_work.user.get_one(id=user_id)

        user.balance += obj_in.amount
        return await unit_of_work.transaction_refund.create(obj_in=obj_in)
