from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from urllib3.util import parse_url

from app.core import settings
from app.enums import Language, SocialNetworkType
from app.models.base import Base, CreatedAtModel, UUIDModel


class Author(CreatedAtModel, UUIDModel, Base):
    __tablename__ = "author"

    first_name: Mapped[str]
    last_name: Mapped[str]
    language: Mapped[Language] = mapped_column(ENUM(Language), nullable=False, default=Language.US)
    education: Mapped[dict[str, Any]] = mapped_column(default={}, server_default="{}")
    profession: Mapped[str | None]
    avatar: Mapped[str | None]

    industry_id: Mapped[UUID] = mapped_column(ForeignKey("industry.id", ondelete="RESTRICT"), nullable=False)
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_info.id", ondelete="CASCADE"), nullable=True, default=None
    )
    created_by = relationship("UserInfo", back_populates="created_authors")
    clusters = relationship("Cluster", back_populates="author", cascade="all, delete", passive_deletes=True)
    industry = relationship("Industry", back_populates="authors", lazy="joined")
    social_networks = relationship(
        "SocialNetwork", back_populates="author", cascade="all, delete", passive_deletes=True, lazy="subquery"
    )

    @property
    def full_name(self) -> str:
        """Return the full name of the author."""
        return f"{self.first_name} {self.last_name}"

    @property
    def avatar_url(self) -> str:
        """Return the URL of the author's avatar."""
        if not self.avatar:
            return ""

        return parse_url(f"{settings.storage.authors_uri}/{self.avatar}").url

    @property
    def website_link(self) -> str | None:
        """Return the website link of the author."""
        website = [
            social.social_link
            for social in self.social_networks
            if social.social_network_type == SocialNetworkType.WEBSITE
        ]
        return website[0] if website else None

    @property
    def extra_info(self) -> list[tuple[str, str | None]]:
        """Return the extra information about the author with the corresponding tag type."""
        education = ", ".join([value for value in self.education.values() if value])

        values = [
            ("P", self.full_name),
            ("DIV", education),
            ("DIV", self.profession),
        ]

        return [(tag, value) for tag, value in values if value]

    @property
    def is_custom(self) -> bool:
        """Return whether the author is custom or not."""
        return bool(self.created_by_id)

    @property
    def industry_title(self) -> str:
        """Return the title of the author's industry."""
        return self.industry.title_fr if self.language == Language.FR else self.industry.title_us

    @property
    def introduction(self) -> str:
        """Return the introduction of the author."""
        university = self.education.get("university", "")
        degree = self.education.get("degree", "")
        return (
            f"You are {self.full_name}, a person specializing in {self.industry_title}."
            f" You have a degree of {degree} from {university}. You work as a {self.profession}. "
            f"You write in {'American English' if self.language == 'US' else 'French'}"
        )
