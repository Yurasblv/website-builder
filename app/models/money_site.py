from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtModel, UUIDModel


class MoneySite(UUIDModel, CreatedAtModel, Base):
    __tablename__ = "money_site"

    url: Mapped[str]
    keyword: Mapped[str]
    pbns_generated: Mapped[int] = mapped_column(default=0, server_default="0")
    pbns_deployed: Mapped[int] = mapped_column(default=0, server_default="0")
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_info.id", ondelete="CASCADE", name="moneysite_user_fkey"), nullable=False, index=True
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("pbn_plan.id", ondelete="SET NULL", name="moneysite_plan_fkey"), nullable=True, index=True
    )

    user = relationship("UserInfo", back_populates="money_sites", passive_deletes=True)
    pbns = relationship("PBN", back_populates="money_site", cascade="delete", passive_deletes=True)
    plan = relationship("PBNPlan", back_populates="money_site")

    service_accounts: Mapped[set["ServiceAccount"]] = relationship(  # noqa
        "ServiceAccount", secondary="moneysite_serviceaccount_association", back_populates="money_sites"
    )
    servers: Mapped[set["ServerProvider"]] = relationship(  # noqa
        "ServerProvider", secondary="moneysite_server_association", back_populates="money_sites"
    )
