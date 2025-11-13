from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import with_polymorphic

from app.models import (
    Transaction,
    TransactionRefund,
    TransactionSpend,
)
from app.repository.base import ModelInheritanceCreateMixin, PaginateRepositoryMixin, SQLAlchemyRepository

TransactionType = TransactionSpend | Transaction


class TransactionRepository(PaginateRepositoryMixin, SQLAlchemyRepository):
    model = Transaction

    async def get_multi(self, offset: int = 0, limit: int = 5000, /, **filters: Any) -> Sequence[Transaction]:
        statement = (
            select(self.model)
            .where(*self.get_where_clauses(filters))
            .offset(offset)
            .limit(limit)
            .order_by(self.model.created_at)
        )
        return await self.execute(statement=statement, action=lambda result: result.scalars().all())

    async def get_one(self, **filters: Any) -> Transaction:  # type:ignore[override]
        transaction = with_polymorphic(Transaction, "*")
        statement = select(transaction).where(*self.get_where_clauses(filters))
        return await self.execute(statement=statement, action=lambda result: result.scalars().one())

    async def get_amount(self, **filters: Any) -> Decimal:
        """
        Get total amount for specific transaction type for a user

        Kwargs:
            filters: filters for transactions

        Returns:
            Total amount
        """
        statement = select(func.sum(Transaction.amount)).where(*self.get_where_clauses(filters))
        amount = await self.execute(statement=statement, action=lambda result: result.scalars().one())
        return amount or Decimal(0)


class TransactionSpendRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = TransactionSpend


class TransactionRefundRepository(ModelInheritanceCreateMixin, SQLAlchemyRepository):
    model = TransactionRefund
