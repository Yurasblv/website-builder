from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Language
from app.models.base import Base, CreatedAtModel, UUIDModel


class EmailNotification(UUIDModel, CreatedAtModel, Base):
    __tablename__ = "email_notification"

    receiver: Mapped[str] = mapped_column(String(255))
    context: Mapped[dict[str, Any]] = mapped_column(nullable=False)

    template_id: Mapped[UUID] = mapped_column(ForeignKey("email_notification_template.id", ondelete="CASCADE"))

    template = relationship("EmailNotificationTemplate", back_populates="notifications", lazy="joined")


class EmailNotificationTemplate(UUIDModel, CreatedAtModel, Base):
    __tablename__ = "email_notification_template"

    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str]
    language: Mapped[Language] = mapped_column(ENUM(Language), default=Language.US, server_default=Language.US)

    notifications = relationship("EmailNotification", back_populates="template", cascade="all, delete-orphan")
