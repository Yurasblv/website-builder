from decimal import Decimal

from pydantic import UUID4, BaseModel, Field

from app.enums import SpendType, TransactionStatus


class TransactionRefundCreate(BaseModel):
    user_id: UUID4 = Field(..., description="User ID")
    spend_tx_id: UUID4 = Field(..., description="Spend tx refund for")
    amount: Decimal = Field(..., description="Refund amount")
    status: TransactionStatus = Field(TransactionStatus.COMPLETED, description="Refund status")
    object_type: SpendType = Field(..., description="Object type")
    info: str = Field("", description="Transaction info")
