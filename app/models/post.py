from uuid import UUID

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import SocialNetworkType
from app.models.base import Base, TimestampModel, UUIDModel


class Post(UUIDModel, Base, TimestampModel):
    __tablename__ = "post"

    social_network_id: Mapped[UUID] = mapped_column(ForeignKey("social_network.id", ondelete="CASCADE"))
    post_type: Mapped[SocialNetworkType] = mapped_column()

    social_network = relationship("SocialNetwork", back_populates="posts")

    __mapper_args__ = {
        "polymorphic_on": post_type,
        "polymorphic_identity": __tablename__,
    }
    __table_args__ = (
        Index("post_type_type_created_at_social_network_id_idx", "post_type", "created_at", "social_network_id"),
    )


class PostX(Post):
    __tablename__ = "post_x"

    id: Mapped[UUID] = mapped_column(ForeignKey("post.id", ondelete="CASCADE"), primary_key=True, index=True)
    text: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": SocialNetworkType.X,
    }
