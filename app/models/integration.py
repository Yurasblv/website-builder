from uuid import UUID

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import IntegrationType, WPIntegrationType
from app.models.base import Base, TimestampModel, UUIDModel


class Integration(UUIDModel, TimestampModel, Base):
    __tablename__ = "integration"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_info.id"))
    integration_type: Mapped[IntegrationType] = mapped_column()

    user = relationship("UserInfo", back_populates="integrations", foreign_keys="Integration.user_id", lazy="selectin")

    __mapper_args__ = {
        "polymorphic_on": integration_type,
        "polymorphic_identity": __tablename__,
    }
    __table_args__ = (Index("integration_type_created_at_user_id_idx", "integration_type", "created_at", "user_id"),)


class IntegrationWordPress(Integration):
    __tablename__ = "integration_wordpress"

    id: Mapped[UUID] = mapped_column(ForeignKey("integration.id", ondelete="CASCADE"), primary_key=True, index=True)
    domain: Mapped[str] = mapped_column(index=True)
    api_key: Mapped[str]
    type: Mapped[WPIntegrationType] = mapped_column(
        default=WPIntegrationType.CUSTOMER, server_default=WPIntegrationType.CUSTOMER
    )

    __mapper_args__ = {
        "polymorphic_identity": IntegrationType.WORDPRESS,
    }
