from datetime import datetime
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator
from pydantic_core.core_schema import ValidationInfo

from app.enums import Country, GenerationStatus, Language, PageIntent, PageStatus
from app.models import Author, PageCluster
from app.models.cluster import ClusterSettings
from app.schemas.cluster.base import ClusterSettingsRead, SourceLinkRead
from app.schemas.elements.cluster_pages.base import BaseStyle
from app.schemas.page.cluster_page import ClusterPageTextInfo


class PageGenerateRead(BaseModel):
    id: UUID4
    topic: str
    general_style: BaseStyle | None = {}
    text_info: ClusterPageTextInfo | None = {}
    keywords: list[str] = []
    search_intent: PageIntent
    category: int
    reviews: dict[str, Any] | None = {}
    content_file: list[str] | None = []
    status: PageStatus

    parent_id: UUID4 | None = None
    parent_topic: str | None = None
    neighbours_ids: list[UUID4] = Field(default_factory=list, description="List of neighbours ids.")
    neighbours_topics: list[str] = Field(default_factory=list, description="List of neighbours topics.")
    children_ids: list[UUID4] = Field(default_factory=list, description="List of children ids.")
    children_topics: list[str] = Field(default_factory=list, description="List of children topics.")

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @property
    def children(self) -> list[tuple]:
        return list(zip(self.children_ids, self.children_topics))

    @property
    def neighbours(self) -> list[tuple]:
        return list(zip(self.neighbours_ids, self.neighbours_topics))

    @property
    def has_parent(self) -> bool:
        return bool(self.parent_id and self.parent_topic)


class ClusterGenerateRead(BaseModel):
    id: UUID4
    keyword: str
    language: Language
    target_country: Country
    target_audience: str | None
    link: str | None
    topics_number: int
    status: GenerationStatus
    created_at: datetime | None
    user_id: UUID4
    author: Author
    pages: list[PageGenerateRead] = []
    settings: dict[PageIntent, ClusterSettingsRead] = {}

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def transform(cls, data: dict[str, Any]) -> dict[str, Any]:
        data["pages"] = cls.transform_pages(language=data.get("language"), pages=data.get("pages", []))
        data["settings"] = cls.transform_settings(settings=data.get("settings", []))
        return data

    @staticmethod
    def transform_settings(settings: list[dict]) -> dict[PageIntent, ClusterSettingsRead]:
        return {PageIntent(item["search_intent"]): ClusterSettingsRead.model_validate(item) for item in settings}

    @staticmethod
    def transform_pages(language: Language | None, pages: list[dict]) -> list[PageGenerateRead]:
        filtered_pages = [page for page in pages if page["status"] == PageStatus.DRAFT]

        pages_to_generate: dict[UUID4, PageGenerateRead] = {}
        children_map: dict[UUID4, dict] = {}

        for page in filtered_pages:
            pages_to_generate[page["id"]] = PageGenerateRead.model_validate(page)

            if page["parent_id"]:
                if page["parent_id"] not in children_map:
                    children_map[page["parent_id"]] = {"children_ids": [], "children_topics": []}

                children_map[page["parent_id"]]["children_ids"].append(page["id"])
                children_map[page["parent_id"]]["children_topics"].append(page["topic"])

        for parent_id, child_data in children_map.items():
            child_ids = child_data["children_ids"]
            child_topics = child_data["children_topics"]

            neighbours_mapping = {child_ids[i]: child_topics[i] for i in range(len(child_ids))}

            for child_id in child_ids:
                neighbours_ids = [neighbours_id for neighbours_id in neighbours_mapping if neighbours_id != child_id]
                neighbours_topics = [neighbours_mapping[neighbours_id] for neighbours_id in neighbours_ids]

                pages_to_generate[child_id].neighbours_ids = neighbours_ids
                pages_to_generate[child_id].neighbours_topics = neighbours_topics

        for page_id, env in pages_to_generate.items():
            if env.parent_id:
                env.parent_topic = pages_to_generate[env.parent_id].topic

            if page_id in children_map:
                env.children_ids = children_map[page_id]["children_ids"]
                env.children_topics = children_map[page_id]["children_topics"]

        return list(pages_to_generate.values())

    @property
    def pages_number(self) -> int:
        return len(self.pages)


class PageRefreshRead(BaseModel):
    id: UUID4
    topic: str
    main_source_link: SourceLinkRead | None = None
    search_intent: PageIntent
    language: Language
    target_audience: str = ""
    category: int
    original_content_file: str
    releases: list[str]

    parent_id: UUID4 | None = None
    parent_topic: str | None = None
    neighbours_ids: list[UUID4] = Field(default_factory=list, description="List of neighbours ids.")
    neighbours_topics: list[str] = Field(default_factory=list, description="List of neighbours topics.")
    children_ids: list[UUID4] = Field(default_factory=list, description="List of children ids.")
    children_topics: list[str] = Field(default_factory=list, description="List of children topics.")

    h1_positions: list[int] = Field(default_factory=list)
    h2_positions: list[int] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def validate_refresh_page_schema(cls, data: dict, info: ValidationInfo) -> dict:
        if info.context:
            data["language"] = info.context.get("language", Language.US)

        else:
            data["language"] = Language.US

        return data


class ClusterRefreshRead(ClusterGenerateRead):
    pages: list[PageRefreshRead] = []

    @staticmethod
    def transform_settings(settings: list[ClusterSettings]) -> dict[PageIntent, ClusterSettingsRead]:  # type: ignore
        return {PageIntent(item.search_intent): ClusterSettingsRead.model_validate(item) for item in settings}

    @staticmethod
    def transform_pages(language: Language | None, pages: list[PageCluster]) -> list[PageRefreshRead]:  # type: ignore
        pages_to_generate: dict[UUID4, PageRefreshRead] = {}
        children_map: dict[UUID4, dict] = {}

        for page in pages:
            pages_to_generate[page.id] = PageRefreshRead.model_validate(page.__dict__, context={"language": language})

            if page.parent_id:
                if page.parent_id not in children_map:
                    children_map[page.parent_id] = {"children_ids": [], "children_topics": []}

                children_map[page.parent_id]["children_ids"].append(page.id)
                children_map[page.parent_id]["children_topics"].append(page.topic)

        for parent_id, child_data in children_map.items():
            child_ids = child_data["children_ids"]
            child_topics = child_data["children_topics"]

            neighbours_mapping = {child_ids[i]: child_topics[i] for i in range(len(child_ids))}

            for child_id in child_ids:
                neighbours_ids = [neighbours_id for neighbours_id in neighbours_mapping if neighbours_id != child_id]
                neighbours_topics = [neighbours_mapping[neighbours_id] for neighbours_id in neighbours_ids]

                pages_to_generate[child_id].neighbours_ids = neighbours_ids
                pages_to_generate[child_id].neighbours_topics = neighbours_topics

        for page_id, env in pages_to_generate.items():
            if env.parent_id:
                env.parent_topic = pages_to_generate[env.parent_id].topic

            if page_id in children_map:
                env.children_ids = children_map[page_id]["children_ids"]
                env.children_topics = children_map[page_id]["children_topics"]

        return list(pages_to_generate.values())


class ClusterGenerationInfo(BaseModel):
    pages_tx_id: UUID4 = None
    unprocessed_pages: set[UUID4] = set()

    def clear(self) -> None:
        self.unprocessed_pages.clear()


class Snapshot(BaseModel):
    page_id: str
    data: str
