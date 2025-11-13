from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from app.enums import InformationalPageElementType, Language, PageIntent, PageType
from app.schemas.cluster.base import SourceLinkRead
from app.schemas.elements import BaseStyle, ElementContent, ElementSettings
from app.schemas.elements.cluster_pages.base import GeolocationSchema

from .base import PageBase


class ClusterPageBase(PageBase):
    topic: str
    topic_path: str = Field(default="")
    cluster_id: UUID4
    search_intent: PageIntent = PageIntent.INFORMATIONAL
    page_type: PageType = PageType.CLUSTER
    updated_at: datetime = Field(description="ClusterPage update date.")
    created_at: datetime = Field(description="ClusterPage create date.")


class ClusterPageTextInfo(BaseModel):
    h2_tags_number: int = 5
    n_words: int = 300
    summary: str = ""


class ClusterPageCreate(ClusterPageBase):
    parent_id: UUID4 | None = None
    text_info: ClusterPageTextInfo = ClusterPageTextInfo()
    keywords: list[str] = Field(default_factory=list, description="List of keywords.")
    category: int | None = None
    reviews: dict[str, Any] = Field(default_factory=dict, description="List of keywords.")
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC), description="ClusterPage update date."
    )
    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC), description="ClusterPage creation date."
    )


class ClusterPageFilters(BaseModel):
    page_id: UUID4 | None = None
    parent_id: UUID4 | None = None
    offset: int = Field(default=0, ge=0)
    offset_id: str | None = None
    limit: int = Field(default=0, ge=0, le=100)


class ClusterPageCommon(ClusterPageBase):
    language: Language
    general_style: BaseStyle | None = None
    content: list[dict[str, Any]] | None = None
    related_parent: UUID4 | None = Field(None, alias="parent_id")
    related_children: list[UUID4] = Field(default_factory=list, description="List of related children ids.")
    reviews: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def set_extra_attrs(cls, data: Any, info: Any) -> dict:
        if isinstance(data, dict) and info.context:
            if "language" in info.context:
                data["language"] = info.context["language"]

            if "topic_path" in info.context:
                data["topic_path"] = info.context["topic_path"]

        return data


class ClusterPageRelations(ClusterPageBase):
    category: int | None = None
    related_parent: UUID4 | None = None
    related_children: list["ClusterPageRelations"] = Field(
        default_factory=list, description="List of related children."
    )


class ClusterPageGenerationMetadata(BaseModel):
    pbn_id: UUID4 | None
    cluster_id: UUID4
    page_uuid: UUID4
    search_intent: PageIntent
    main_source_link: SourceLinkRead | None = None
    geolocation: GeolocationSchema | dict = Field(default_factory=dict, description="Geolocation data.")
    topic_name: str
    text_info: ClusterPageTextInfo = ClusterPageTextInfo()
    keywords: list[str] = Field(default_factory=list, description="List of keywords.")
    target_audience: str | None = None
    topic_category: int | None = 0
    reviews: dict[str, Any] | None = {}
    parent_url: UUID4 | str | None = None
    parent_topic: str | None = None
    neighbours_urls: list[UUID4 | str] = Field(default_factory=list, description="List of neighbours ids.")
    neighbours_topics: list[str] = Field(default_factory=list, description="List of neighbours topics.")
    children_urls: list[UUID4 | str] = Field(default_factory=list, description="List of children ids.")
    children_topics: list[str] = Field(default_factory=list, description="List of children topics.")

    @property
    def children(self) -> list[tuple]:
        return list(zip(self.children_urls, self.children_topics))

    @property
    def neighbours(self) -> list[tuple]:
        return list(zip(self.neighbours_urls, self.neighbours_topics))

    @property
    def has_parent(self) -> bool:
        return bool(self.parent_url and self.parent_topic)

    @property
    def relations(self) -> list[tuple]:
        relations = []

        if self.has_parent:
            relations.append((self.parent_url, self.parent_topic))

        relations.extend(self.neighbours)
        relations.extend(self.children)

        return relations


class ClusterPageGeneratorResponse(BaseModel):
    page_metadata: ClusterPageGenerationMetadata
    original_content: list[ElementContent] = Field(default_factory=list, description="List of elements content.")
    release_content: list[ElementContent] = Field(default_factory=list, description="List of elements content.")
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC), description="ClusterPage update date."
    )
    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC), description="ClusterPage creation date."
    )

    @property
    def valid(self) -> bool:
        return all([self.original_content, self.release_content])

    def sort_content(self) -> None:
        self.original_content = sorted([i for i in self.original_content], key=lambda i: i.position)
        self.release_content = sorted([i for i in self.release_content], key=lambda i: i.position)

    def filter_processed(self) -> None:
        def _filter(data: list[ElementContent]) -> list[ElementContent]:
            content = []

            for i in data:
                if i.children:
                    i.children = _filter(i.children)

                if i.processed:
                    content.append(i)

            return content

        self.original_content = _filter(self.original_content)
        self.release_content = _filter(self.release_content)


class ClusterPageUpdateCommon(BaseModel):
    id: UUID4 | None = Field(
        default=None, description="ClusterPage id.", examples=["ca4a9fcb-1201-432e-a72e-9df69f799f84"]
    )
    topic: str | None = Field(
        default=None, description="ClusterPage topic.", examples=["Best Street Fight Games", "History of Harry Potter"]
    )
    search_intent: PageIntent | None = Field(
        default=None, description="ClusterPage search_intent.", examples=PageIntent.list()
    )


class ClusterPageUpdate(BaseModel):
    general_style: BaseStyle | None = None
    content: list[ElementContent] | None = None


class ClusterPageStyleUpdateParam(BaseModel):
    tag: InformationalPageElementType
    classname: str | None = Field(None, description="Classname for element.")
    settings: ElementSettings | None = Field(None, description="Element arguments.")
    style: BaseStyle | None = Field(None, description="Element style.")


class ClusterPagesElementsStyleUpdate(BaseModel):
    general_style: BaseStyle | None = Field(None, description="General page style.")
    style_params: list[ClusterPageStyleUpdateParam] = Field(
        default_factory=list, description="List of elements style params."
    )


class ClusterPagesIntentInfo(BaseModel):
    intent: PageIntent
    pages_count: int
