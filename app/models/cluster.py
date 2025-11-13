import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, event
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Country, GenerationStatus, Language, PageIntent
from app.enums.websocket import ClusterEventEnum
from app.models.base import Base, TimestampModel, UUIDModel


class Cluster(UUIDModel, TimestampModel, Base):
    __tablename__ = "cluster"

    keyword: Mapped[str]
    language: Mapped[Language] = mapped_column(ENUM(Language), default=Language.US, server_default=Language.US)
    target_country: Mapped[Country] = mapped_column(ENUM(Country), default=Country.US, server_default=Country.US)
    target_audience: Mapped[str | None] = mapped_column(default=None, nullable=True)
    status: Mapped[GenerationStatus] = mapped_column(
        ENUM(GenerationStatus), server_default=GenerationStatus.STEP1, default=GenerationStatus.STEP1
    )
    link: Mapped[str | None]
    topics_number: Mapped[int | None]
    is_community: Mapped[bool] = mapped_column(default=False, server_default="false", index=True)
    xmind: Mapped[str | None]

    snapshot: Mapped[str | None]

    industry_id: Mapped[UUID | None] = mapped_column(ForeignKey("industry.id", ondelete="RESTRICT"), nullable=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_info.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[UUID | None] = mapped_column(ForeignKey("author.id", ondelete="RESTRICT"), nullable=True)
    pbn_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pbn.id", name="cluster_pbn_fkey", ondelete="CASCADE"), nullable=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("project.id", name="cluster_project_fkey", ondelete="SET NULL"), nullable=True
    )

    author = relationship("Author", back_populates="clusters")
    industry = relationship("Industry", back_populates="clusters", lazy="joined")
    pages = relationship("PageCluster", back_populates="cluster", cascade="all, delete")
    pbn = relationship("PBN", back_populates="clusters", cascade="all, delete", passive_deletes=True)
    project = relationship("Project", back_populates="clusters")
    user = relationship("UserInfo", back_populates="clusters")

    settings: Mapped[list["ClusterSettings"]] = relationship("ClusterSettings", cascade="all, delete")

    @property
    def is_draft(self) -> bool:
        return self.status in GenerationStatus.draft_statuses()

    @property
    def industry_title(self) -> str | None:
        """Return the title of the cluster's industry."""
        if not self.industry_id:
            return None

        return self.industry.title_fr if self.language == Language.FR else self.industry.title_us


class ClusterSettings(UUIDModel, Base):
    __tablename__ = "cluster_settings"

    search_intent: Mapped[PageIntent] = mapped_column(
        ENUM(PageIntent, create_type=False), default=PageIntent.INFORMATIONAL, server_default=PageIntent.INFORMATIONAL
    )

    main_source_link: Mapped[dict[str, Any] | None] = mapped_column(default=None, server_default=None)

    reviews: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    general_style: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}", nullable=False)
    elements_params: Mapped[list[dict[str, Any]]] = mapped_column(default=list, server_default="{}", nullable=False)
    geolocation: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}", nullable=False)
    cluster_id: Mapped[UUID] = mapped_column(ForeignKey("cluster.id", ondelete="CASCADE"), index=True)


@event.listens_for(Cluster, "after_update")
def after_update_status(mapper: Any, connection: Any, target: Cluster) -> None:
    from app.schemas import ClusterResponse
    from app.utils.message_queue import enqueue_global_message

    if target.status == GenerationStatus.STEP1:
        return

    loop = asyncio.get_event_loop()

    data = ClusterResponse.model_validate(target)
    task = enqueue_global_message(
        event=ClusterEventEnum.UPDATED, user_id=target.user_id, **data.model_dump(mode="json")
    )

    asyncio.run_coroutine_threadsafe(task, loop)
