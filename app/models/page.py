from typing import Any
from uuid import UUID

from sqlalchemy import ARRAY, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import PageIntent, PageStatus, PageType
from app.models.base import Base, TimestampModel, UUIDModel


class Page(UUIDModel, TimestampModel, Base):
    __tablename__ = "page"

    original_content_file: Mapped[str | None] = mapped_column(nullable=True)
    releases: Mapped[list[str] | None] = mapped_column(
        MutableList.as_mutable(ARRAY(String)), nullable=True, server_default="{}"
    )
    status: Mapped[PageStatus] = mapped_column(
        ENUM(PageStatus), server_default=PageStatus.DRAFT, default=PageStatus.DRAFT
    )
    page_type: Mapped[PageType] = mapped_column()

    __mapper_args__ = {
        "polymorphic_on": page_type,
        "polymorphic_identity": __tablename__,
    }
    __table_args__ = (
        Index(
            "ix_page_type",
            "page_type",
        ),
    )

    @property
    def current_release(self) -> str:
        return self.releases[-1] if self.releases else ""

    @property
    def is_downgradable(self) -> bool:
        return len(self.releases or []) >= 2

    @property
    def is_upgradable(self) -> bool:
        return bool(self.releases)

    @property
    def topic_path(self) -> str:
        """Get the topic path of the page."""
        from app.utils.convertors import text_normalize

        topic = getattr(self, "topic", None)

        if not topic:
            raise ValueError("Topic is not set for this page.")

        return text_normalize(topic)


class PagePBNHome(Page):
    __tablename__ = "page_pbn_home"
    id: Mapped[UUID] = mapped_column(ForeignKey("page.id", ondelete="CASCADE"), primary_key=True, index=True)
    pbn_id = mapped_column(ForeignKey("pbn.id", name="page_pbn_extra_pbn_fkey", ondelete="CASCADE"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": PageType.PBN_HOME,
    }
    pbn = relationship("PBN", back_populates="page_home", cascade="all, delete", passive_deletes=True)
    _page = relationship("Page", backref="page_home", cascade="all, delete", passive_deletes=True)


class PagePBNLegal(Page):
    __tablename__ = "page_pbn_legal"
    id: Mapped[UUID] = mapped_column(ForeignKey("page.id", ondelete="CASCADE"), primary_key=True, index=True)
    pbn_id = mapped_column(ForeignKey("pbn.id", name="page_pbn_extra_pbn_fkey", ondelete="CASCADE"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": PageType.PBN_LEGAL,
    }
    pbn = relationship("PBN", back_populates="page_legal", cascade="all, delete", passive_deletes=True)
    _page = relationship("Page", backref="page_legal", cascade="all, delete", passive_deletes=True)


class PagePBNContact(Page):
    __tablename__ = "page_pbn_contact"
    id: Mapped[UUID] = mapped_column(ForeignKey("page.id", ondelete="CASCADE"), primary_key=True, index=True)
    pbn_id = mapped_column(ForeignKey("pbn.id", name="page_pbn_extra_pbn_fkey", ondelete="CASCADE"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": PageType.PBN_CONTACT,
    }
    pbn = relationship("PBN", back_populates="page_contact", cascade="all, delete", passive_deletes=True)
    _page = relationship("Page", backref="page_contact", cascade="all, delete", passive_deletes=True)


class PagePBNExtra(Page):
    __tablename__ = "page_pbn_extra"
    id: Mapped[UUID] = mapped_column(ForeignKey("page.id", ondelete="CASCADE"), primary_key=True, index=True)
    topic: Mapped[str]
    zip_file: Mapped[str | None] = mapped_column(nullable=True)

    pbn_id = mapped_column(ForeignKey("pbn.id", name="page_pbn_extra_pbn_fkey", ondelete="CASCADE"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": PageType.PBN_EXTRA,
    }
    pbn = relationship("PBN", back_populates="pages_extra", cascade="all, delete", passive_deletes=True)
    _page = relationship("Page", backref="pages_extra", cascade="all, delete", passive_deletes=True)


class PageCluster(Page):
    __tablename__ = "page_cluster"

    id: Mapped[UUID] = mapped_column(ForeignKey("page.id", ondelete="CASCADE"), primary_key=True, index=True)

    topic: Mapped[str]
    text_info: Mapped[dict[str, Any] | None] = mapped_column(default={}, server_default="{}", nullable=True)
    general_style: Mapped[dict[str, Any] | None] = mapped_column(default={}, server_default="{}", nullable=True)
    keywords: Mapped[list[str]] = mapped_column(default=[], server_default="{}")
    search_intent: Mapped[PageIntent] = mapped_column(
        ENUM(PageIntent), default=PageIntent.INFORMATIONAL, server_default=PageIntent.INFORMATIONAL
    )
    category: Mapped[int | None] = mapped_column(default=None)

    cluster_id: Mapped[UUID | None] = mapped_column(ForeignKey("cluster.id", ondelete="CASCADE"), nullable=True)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("page.id", ondelete="CASCADE"), nullable=True)
    reviews: Mapped[dict[str, Any] | None] = mapped_column(default={}, server_default="{}", nullable=True)

    cluster = relationship("Cluster", back_populates="pages")

    parent_page = relationship(
        "PageCluster",
        foreign_keys=[parent_id],
        back_populates="children",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )
    children = relationship("PageCluster", foreign_keys=[parent_id], cascade="all, delete-orphan", passive_deletes=True)

    __mapper_args__ = {
        "polymorphic_identity": PageType.CLUSTER,
        "inherit_condition": Page.id == id,
    }
