from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import SpendType, TransactionStatus, TransactionType
from app.models.base import Base, TimestampModel, UUIDModel


class Transaction(UUIDModel, TimestampModel, Base):
    __tablename__ = "transaction"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_info.id"))
    amount: Mapped[Decimal]
    status: Mapped[TransactionStatus] = mapped_column(default=TransactionStatus.PENDING)
    info: Mapped[str] = mapped_column(server_default="")
    transaction_type: Mapped[TransactionType]

    user = relationship("UserInfo", back_populates="transactions", foreign_keys="Transaction.user_id", lazy="selectin")

    __mapper_args__ = {
        "polymorphic_on": "transaction_type",
        "polymorphic_identity": "transaction",
    }
    __table_args__ = (Index("transaction_type_created_at_user_id_idx", "transaction_type", "created_at", "user_id"),)


class TransactionRefund(Transaction):
    __tablename__ = "transaction_refund"
    id: Mapped[UUID] = mapped_column(ForeignKey("transaction.id"), primary_key=True)
    object_type: Mapped[SpendType]
    spend_tx_id: Mapped[UUID] = mapped_column(ForeignKey("transaction_spend.id", ondelete="CASCADE"), nullable=True)

    __mapper_args__ = {"polymorphic_identity": TransactionType.REFUND}


class TransactionSpend(Transaction):
    __tablename__ = "transaction_spend"
    id: Mapped[UUID] = mapped_column(ForeignKey("transaction.id"), primary_key=True)

    object_id: Mapped[UUID]
    object_type: Mapped[SpendType]

    __mapper_args__ = {"polymorphic_identity": TransactionType.SPEND}
