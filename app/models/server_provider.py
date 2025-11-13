from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.provider import ServerProviderStatus, ServerProviderType
from app.models.base import Base, TimestampModel, UUIDModel


class ServerProvider(UUIDModel, TimestampModel, Base):
    __tablename__ = "server_provider"

    server_id: Mapped[str]
    name: Mapped[str]
    location: Mapped[str]
    status: Mapped[ServerProviderStatus] = mapped_column(ENUM(ServerProviderStatus))
    public_net_ipv4: Mapped[str]
    public_net_ipv6: Mapped[str]
    ssh_private_key: Mapped[str] = mapped_column(String, nullable=False, server_default="")

    provider_type: Mapped[ServerProviderType] = mapped_column()

    money_sites: Mapped[set["MoneySite"]] = relationship(  # noqa: F821
        "MoneySite", secondary="moneysite_server_association", back_populates="servers"
    )
    pbns = relationship("PBN", back_populates="server", cascade="all", passive_deletes=True)

    __mapper_args__ = {
        "polymorphic_on": provider_type,
        "polymorphic_identity": __tablename__,
    }


class ServerProviderHetzner(ServerProvider):
    __tablename__ = "server_provider_hetzner"

    id: Mapped[UUID] = mapped_column(ForeignKey("server_provider.id", ondelete="CASCADE"), primary_key=True, index=True)

    __mapper_args__ = {
        "polymorphic_identity": ServerProviderType.HETZNER,
    }


class ServerProviderScaleway(ServerProvider):
    __tablename__ = "server_provider_scaleway"

    id: Mapped[UUID] = mapped_column(ForeignKey("server_provider.id", ondelete="CASCADE"), primary_key=True, index=True)
    admin_password_encryption_ssh_key_id: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": ServerProviderType.SCALEWAY,
    }
