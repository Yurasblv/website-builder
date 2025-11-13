from decimal import Decimal

from pydantic import UUID4, BaseModel, Field

from app.enums import SpendType, TransactionStatus


class TransactionSpendCreate(BaseModel):
    user_id: UUID4 = Field(..., description="User ID")
    amount: Decimal = Field(..., description="Spend amount")
    status: TransactionStatus = Field(TransactionStatus.PENDING, description="Spend status")
    object_id: UUID4 = Field(..., description="Object ID")
    object_type: SpendType = Field(..., description="Object type")
    info: str = Field("", description="Transaction info")
