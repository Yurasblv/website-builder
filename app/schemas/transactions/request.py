from pydantic import BaseModel, Field

from app.enums import TransactionStatus, TransactionType


class TransactionFilters(BaseModel):
    transaction_type: TransactionType | None = Field(
        None, description="Transaction type", examples=TransactionType.list()
    )
    status: TransactionStatus | None = Field(None, description="Transaction status", examples=TransactionStatus.list())
