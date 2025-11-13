from uuid import UUID

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import SocialNetworkType
from app.models.base import Base, TimestampModel, UUIDModel


class SocialNetwork(UUIDModel, TimestampModel, Base):
    __tablename__ = "social_network"

    social_network_type: Mapped[SocialNetworkType] = mapped_column()
    author_id: Mapped[UUID | None] = mapped_column(ForeignKey("author.id", ondelete="CASCADE"), nullable=True)
    social_link: Mapped[str]

    author = relationship("Author", back_populates="social_networks")
    posts = relationship("Post", back_populates="social_network", cascade="all, delete", passive_deletes=True)

    __mapper_args__ = {
        "polymorphic_on": social_network_type,
        "polymorphic_identity": __tablename__,
    }
    __table_args__ = (
        Index("social_network_type_created_at_author_id_idx", "social_network_type", "created_at", "author_id"),
    )


class SocialNetworkX(SocialNetwork):
    __tablename__ = "social_network_x"

    id: Mapped[UUID] = mapped_column(ForeignKey("social_network.id", ondelete="CASCADE"), primary_key=True, index=True)
    api_key: Mapped[str]
    api_secret: Mapped[str]
    access_token: Mapped[str]
    access_token_secret: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": SocialNetworkType.X,
    }


class SocialNetworkWebsite(SocialNetwork):
    __tablename__ = "social_network_website"

    id: Mapped[UUID] = mapped_column(ForeignKey("social_network.id", ondelete="CASCADE"), primary_key=True, index=True)

    __mapper_args__ = {
        "polymorphic_identity": SocialNetworkType.WEBSITE,
    }
