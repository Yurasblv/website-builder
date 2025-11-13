from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, String, false, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Language, UserRole
from app.models.base import Base, CreatedAtModel, UUIDModel


class UserInfo(UUIDModel, CreatedAtModel, Base):
    __tablename__ = "user_info"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    last_online: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())
    role: Mapped[UserRole] = mapped_column(ENUM(UserRole), default=UserRole.USER, server_default=UserRole.USER)
    language: Mapped[Language] = mapped_column(ENUM(Language), default=Language.US, server_default=Language.US)
    invited_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_info.id"), nullable=True)
    company_id: Mapped[UUID | None]

    # Billing
    balance: Mapped[Decimal] = mapped_column(server_default="0")
    is_card_validated: Mapped[bool] = mapped_column(server_default=false(), default=False)

    # API
    api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Fingerprint
    fingerprint_id: Mapped[UUID | None]

    # Relationships
    clusters = relationship("Cluster", back_populates="user", cascade="all, delete")
    created_authors = relationship("Author", back_populates="created_by", cascade="all, delete")
    domain = relationship("Domain", back_populates="user", cascade="all, delete")
    integrations = relationship("Integration", back_populates="user", cascade="all, delete")
    money_sites = relationship("MoneySite", back_populates="user", cascade="all, delete", passive_deletes=True)
    pbns = relationship("PBN", back_populates="user")
    projects = relationship("Project", back_populates="user", cascade="all, delete")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete")

    @property
    def fullname(self) -> str:
        """
        Get full name of user

        Returns:
            fullname or Anonymous

        """
        parts = [part for part in [self.first_name, self.last_name] if part] or ["Anonymous"]
        return " ".join(parts)

    @property
    def is_blogger(self) -> bool:
        """
        Check if user is blogger

        Returns:
            bool: True if user is blogger

        """
        return self.role == UserRole.BLOGGER

    @property
    def is_bound(self) -> bool:
        """
        Check if user has fingerprint_id

        Returns:
            bool: True if user is bound

        """
        return bool(self.fingerprint_id)
