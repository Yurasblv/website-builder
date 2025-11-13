from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import DomainStatus, DomainType
from app.models.base import Base, CreatedAtModel, UUIDModel


class Domain(UUIDModel, CreatedAtModel, Base):
    __tablename__ = "domain"

    name: Mapped[str] = mapped_column(nullable=False)
    domain_status: Mapped[DomainStatus] = mapped_column(
        ENUM(DomainStatus), server_default=DomainStatus.NEW, default=DomainStatus.NEW, nullable=False
    )
    domain_type: Mapped[DomainType] = mapped_column(nullable=False)
    expire_at: Mapped[datetime] = mapped_column(nullable=True)

    category_id: Mapped[UUID] = mapped_column(ForeignKey("category.id", ondelete="RESTRICT"), nullable=False)
    pbn_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pbn.id", name="domain_pbn_id_fkey", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_info.id", name="domain_user_id_fkey", ondelete="SET NULL"), nullable=True
    )

    analytics = relationship(
        "DomainAnalytics",
        back_populates="domain",
        cascade="all, delete",
        passive_deletes=True,
        single_parent=True,
        lazy="selectin",
    )
    category = relationship("Category", back_populates="domains", lazy="joined")
    user = relationship("UserInfo", back_populates="domain")
    pbn = relationship("PBN", back_populates="domain", single_parent=True)

    __mapper_args__ = {
        "polymorphic_on": domain_type,
        "polymorphic_identity": __tablename__,
    }


class DomainAnalytics(UUIDModel, CreatedAtModel, Base):
    __tablename__ = "domain_analytics"

    trust_flow: Mapped[int] = mapped_column(nullable=False)
    citation_flow: Mapped[int] = mapped_column(nullable=False)
    domain_rating: Mapped[int] = mapped_column(nullable=False)

    domain_id: Mapped[UUID] = mapped_column(
        ForeignKey("domain.id", name="domain_analytics_domain_fkey", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=False,
    )
    domain = relationship("Domain", back_populates="analytics", cascade="all, delete", passive_deletes=True)


class DomainExpired(Domain):
    __tablename__ = "domain_expired"

    id: Mapped[UUID] = mapped_column(ForeignKey("domain.id", ondelete="CASCADE"), primary_key=True, index=True)

    __mapper_args__ = {
        "polymorphic_identity": DomainType.EXPIRED,
    }


class DomainCustom(Domain):
    __tablename__ = "domain_custom"

    id: Mapped[UUID] = mapped_column(ForeignKey("domain.id", ondelete="CASCADE"), primary_key=True, index=True)
    NS: Mapped[list[str]] = mapped_column(default=[], server_default="{}", nullable=False)
    type: Mapped[DomainType] = mapped_column(
        nullable=False, default=DomainType.CUSTOM, server_default=DomainType.CUSTOM.name
    )

    __mapper_args__ = {
        "polymorphic_identity": DomainType.CUSTOM,
    }


class DomainAI(Domain):
    __tablename__ = "domain_ai"

    id: Mapped[UUID] = mapped_column(ForeignKey("domain.id", ondelete="CASCADE"), primary_key=True, index=True)
    keyword: Mapped[str] = mapped_column(nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": DomainType.AI_GENERATED,
    }
