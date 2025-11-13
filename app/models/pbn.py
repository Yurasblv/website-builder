import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, ForeignKey, event
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.attributes import get_history

from app.core.exc import PBNNotEnoughBalanceForGeneration
from app.enums import Country, Language
from app.enums.pbn import PBNGenerationStatus, PBNPlanType, PBNTierType
from app.enums.websocket import PBNEventEnum
from app.models.base import Base, CreatedAtModel, TimestampModel, UUIDModel


class PBN(TimestampModel, UUIDModel, Base):
    __tablename__ = "pbn"
    template: Mapped[str] = mapped_column(nullable=False, default="", server_default="")

    pages_number: Mapped[int] = mapped_column(server_default="0", default="0", nullable=False)
    status: Mapped[PBNGenerationStatus] = mapped_column(
        ENUM(PBNGenerationStatus), server_default=PBNGenerationStatus.DRAFT, default=PBNGenerationStatus.DRAFT
    )
    language: Mapped[Language] = mapped_column(ENUM(Language), default=Language.US, server_default=Language.US)
    target_country: Mapped[Country] = mapped_column(ENUM(Country), default=Country.US, server_default=Country.US)
    tier: Mapped[PBNTierType] = mapped_column(ENUM(PBNTierType))

    expired_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    launch_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_info.id", name="pbn_user_id_fkey"), nullable=False)
    money_site_id: Mapped[UUID] = mapped_column(
        ForeignKey("money_site.id", name="pbn_money_site_fkey", ondelete="CASCADE"), nullable=False
    )
    service_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_account.id", name="pbn_service_account_fkey"), nullable=False
    )
    server_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("server_provider.id", name="pbn_server_provider_fkey", ondelete="SET NULL"), nullable=True
    )
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("pbn.id", ondelete="CASCADE"), nullable=True)

    wp_token: Mapped[str | None] = mapped_column(default="", server_default="", nullable=True)
    wp_port: Mapped[str | None] = mapped_column(default="", server_default="", nullable=True)

    # Relationships
    domain = relationship("Domain", back_populates="pbn", single_parent=True, uselist=False)
    user = relationship("UserInfo", back_populates="pbns", single_parent=True, uselist=False)
    clusters = relationship(
        "Cluster", back_populates="pbn", cascade="all, delete", passive_deletes=True, single_parent=True
    )
    page_home = relationship(
        "PagePBNHome",
        back_populates="pbn",
        cascade="all, delete",
        passive_deletes=True,
        single_parent=True,
        uselist=False,
    )
    page_contact = relationship(
        "PagePBNContact",
        back_populates="pbn",
        cascade="all, delete",
        passive_deletes=True,
        single_parent=True,
        uselist=False,
    )
    page_legal = relationship(
        "PagePBNLegal",
        back_populates="pbn",
        cascade="all, delete",
        passive_deletes=True,
        single_parent=True,
        uselist=False,
    )
    pages_extra = relationship("PagePBNExtra", back_populates="pbn", cascade="all, delete", passive_deletes=True)
    money_site = relationship(
        "MoneySite",
        back_populates="pbns",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
        uselist=False,
    )
    service_account = relationship(
        "ServiceAccount", back_populates="pbn", cascade="all", single_parent=True, passive_deletes=True
    )
    server = relationship("ServerProvider", back_populates="pbns", cascade="all", passive_deletes=True)

    parent = relationship(
        "PBN",
        remote_side="PBN.id",
        back_populates="children",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )
    children = relationship("PBN", back_populates="parent", cascade="all, delete-orphan", passive_deletes=True)


class PBNPlan(CreatedAtModel, UUIDModel, Base):
    __tablename__ = "pbn_plan"

    type: Mapped[PBNPlanType] = mapped_column(ENUM(PBNPlanType))
    option: Mapped[int] = mapped_column(CheckConstraint("option >= 1 AND option <= 3", name="check_option_range"))
    pages_amount: Mapped[int]
    websites_amount: Mapped[int]
    structure: Mapped[dict] = mapped_column(JSON, nullable=False)
    price: Mapped[Decimal]

    money_site = relationship("MoneySite", back_populates="plan", cascade="all, delete", passive_deletes=True)

    def check_balance(self, balance: Decimal) -> None:
        """
        Check if the user has enough balance to generate PBN pages.

        Raises:
            PBNNotEnoughBalanceForGeneration: If the balance is not enough.
        """

        if balance >= self.price:
            return

        raise PBNNotEnoughBalanceForGeneration(required=self.price, available=balance, pages_number=self.pages_amount)


@event.listens_for(PBN, "after_update")
def after_update_pbn_status(mapper: Any, connection: Any, target: PBN) -> None:
    from app.utils.message_queue import enqueue_global_message

    loop = asyncio.get_event_loop()

    history = get_history(target, "status")

    if history.has_changes():
        task = enqueue_global_message(
            event=PBNEventEnum.STATUS_CHANGED,
            user_id=target.user_id,
            pbn_id=target.id,
            status=target.status,
        )
        asyncio.run_coroutine_threadsafe(task, loop)
