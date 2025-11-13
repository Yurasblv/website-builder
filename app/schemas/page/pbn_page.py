from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.enums import Country, Language, PageIntent, PageStatus, PageType
from app.schemas import AuthorElementContent
from app.schemas.backlink import BacklinkCreate
from app.schemas.elements.cluster_pages.base import BaseStyle, ElementContent

from .cluster_page import ClusterPageGenerationMetadata


class PBNPageBase(BaseModel):
    id: UUID4
    page_type: PageType
    pbn_id: UUID4
    updated_at: datetime = Field(description="BlogPage update date.")
    created_at: datetime = Field(description="BlogPage create date.")


class PBNPageCreate(PBNPageBase):
    status: PageStatus = PageStatus.DRAFT
    original_content_file: str = None
    releases: list[str] = Field(default_factory=list)
    backlink: BacklinkCreate | None = None
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC), description="ClusterPage update date."
    )
    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC), description="ClusterPage creation date."
    )

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PBNExtraPageBase(PBNPageBase):
    pbn_id: UUID4
    topic: str


class PBNExtraPageCreate(PBNPageCreate):
    zip_file: str | None = None
    releases: list[str] = Field(default_factory=list)
    page_type: PageType = PageType.PBN_EXTRA


class PBNExtraPageRead(PBNExtraPageCreate):
    pass


class PBNExtraPageCommon(BaseModel):
    id: UUID4
    pbn_id: UUID4
    topic_path: str
    topic: str
    general_style: BaseStyle | None = BaseStyle()
    content: list[dict[str, Any]] = Field(default_factory=list)
    language: Language
    updated_at: datetime = Field(description="Extra PBN update date.")
    created_at: datetime = Field(description="Extra PBN create date.")
    search_intent: PageType = PageType.PBN_EXTRA


class PBNExtraPageGenerationMetadata(ClusterPageGenerationMetadata):
    domain: str
    wp_token: str
    user_id: UUID4
    user_balance: Decimal
    user_email: EmailStr
    pbn_id: UUID4
    page_uuid: UUID4 = Field(default_factory=uuid4)
    author: AuthorElementContent
    search_intent: PageIntent = PageIntent.INFORMATIONAL
    keyword: str
    language: Language
    target_country: Country

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PBNExtraPageGeneratorResponse(BaseModel):
    original_content: list[ElementContent] = Field(default_factory=list, description="List of elements content.")
    release_content: list[ElementContent] = Field(default_factory=list, description="List of elements content.")

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


class PBNExtraPageRequest(BaseModel):
    pbn_id: UUID4
    keyword: str = Field(..., description="Keyword for pbn generation", examples=["Lord Of The Rings"])

    @field_validator("keyword", mode="before")
    @classmethod
    def validate_keyword(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Keyword can't be empty")
        if value.isnumeric():
            raise ValueError("Keyword can't be numeric")

        return value


class PBNWpTag(BaseModel):
    tag_placeholder: str = Field(
        ..., description="Placeholder for a web element consisting of HTML tag, name and uuid."
    )
    new_content: str = Field(..., description="New content for a given web element.")


class PBNWpTags(BaseModel):
    tags: list[PBNWpTag] = Field(..., description="List of updated tags")
