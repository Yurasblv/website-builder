import random
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import UUID4, BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.core import settings
from app.enums import Country, GenerationStatus, Language, PageIntent, SourceLinkMode
from app.models.cluster import ClusterSettings
from app.schemas.elements import BaseStyle, ElementStyleParam, GeolocationSchema
from app.schemas.mixins import StrToJSONMixin
from app.schemas.xmindmap import XMindmapBase


class RangeMixin:
    min: float | int
    max: float | int

    @model_validator(mode="after")
    def validate_range(self) -> "RangeMixin":
        if self.min > self.max:
            raise ValueError("`min` value cannot be greater than `max` value")

        return self

    @property
    def random(self) -> float | int:
        match self.min, self.max:
            case int(), int():
                return random.randint(self.min, self.max)  # type: ignore
            case float(), float():
                return round(random.uniform(self.min, self.max), 1)
            case _:
                raise ValueError("Invalid range type")


class Rating(RangeMixin, BaseModel):
    min: float = Field(..., ge=1.0, description="Minimum value", examples=[1.0])
    max: float = Field(..., le=5.0, description="Maximum value", examples=[5.0])


class Count(RangeMixin, BaseModel):
    min: int = Field(..., ge=1, description="Minimum value", examples=[1])
    max: int = Field(..., le=5000, description="Maximum value", examples=[5000])


class Reviews(BaseModel):
    rating: Rating = Field(..., description="Range for the mark of the page")
    count: Count = Field(..., description="Range for the amount of reviews")

    model_config = ConfigDict(from_attributes=True)


class SourceLinkCreate(BaseModel):
    keyword: str = Field(..., description="Keyword for source link", examples=["Lord Of The Rings"], max_length=100)
    link: HttpUrl
    mode: SourceLinkMode = Field(SourceLinkMode.HEAD, description="Mode for main source link")

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        data["link"] = str(data["link"])
        return data


class SourceLinkRead(BaseModel):
    keyword: str = ""
    link: str = ""
    mode: SourceLinkMode | None = None

    def __bool__(self) -> bool:
        return all([self.keyword, self.link, self.mode])


class ClusterSettingsBase(BaseModel):
    id: UUID4 = Field(default_factory=uuid4)
    cluster_id: UUID4
    search_intent: PageIntent

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)


class ClusterSettingsRead(ClusterSettingsBase):
    main_source_link: SourceLinkRead | None = None
    reviews: Reviews | None = None
    general_style: BaseStyle | None = None
    elements_params: list[ElementStyleParam] = Field(default_factory=list)
    geolocation: GeolocationSchema | dict = {}

    @field_validator("reviews", "general_style", "main_source_link", mode="before")
    @classmethod
    def validate_fields(cls, value) -> Any:  # type:ignore[no-untyped-def]
        if isinstance(value, dict) and not value:
            return None
        return value


class ClusterSettingsCreate(ClusterSettingsBase):
    main_source_link: SourceLinkCreate | dict[str, Any] = {}
    reviews: Reviews | dict[str, Any] = {}
    general_style: BaseStyle | dict[str, Any]
    elements_params: list[ElementStyleParam]
    geolocation: GeolocationSchema | dict[str, Any] = {}

    def to_model(self, warnings: bool = True) -> ClusterSettings:
        return ClusterSettings(**self.model_dump(warnings=warnings))


class ClusterSettingsUpdate(BaseModel):
    reviews: Reviews | None = None
    search_intent: PageIntent | None = None
    main_source_link: SourceLinkCreate | None = None
    general_style: BaseStyle | None = None
    elements_params: list[ElementStyleParam] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ClusterResponse(BaseModel):
    id: UUID4
    keyword: str
    author_id: UUID4 | None
    industry_id: UUID4 | None
    industry_title: str | None
    language: Language
    status: GenerationStatus
    is_draft: bool
    link: str | None
    topics_number: int
    created_at: datetime
    updated_at: datetime
    snapshot: str | None
    is_community: bool
    project_id: UUID4 | None
    pbn_id: UUID4 | None

    model_config = ConfigDict(from_attributes=True)


class ClusterCreate(StrToJSONMixin, BaseModel):
    keyword: str = Field(
        ..., description="Keyword for cluster generation", examples=["Lord Of The Rings"], max_length=100
    )
    language: Language = Field(Language.US, description="Language for cluster generation", examples=Language.list())
    target_country: Country = Field(..., description="Target country for cluster generation", examples=Country.list(10))
    target_audience: str | None = Field(
        None, description="Target audience of the cluster", examples=["Teenagers", "Elderly people"], max_length=3000
    )
    main_source_link: SourceLinkCreate | None = Field(None, description="Used in main page for first H2 tag")
    max_pages: int = Field(5, gt=0, le=settings.MAX_PAGES)

    @field_validator("keyword", mode="before")
    @classmethod
    def validate_keyword(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Keyword can't be empty")
        if value.isnumeric():
            raise ValueError("Keyword can't be numeric")

        return value


class ClusterCreateData(BaseModel):
    user_id: UUID4
    data: ClusterCreate
    file_data: list[XMindmapBase] = Field(default_factory=list)


class ClusterUpdate(BaseModel):
    step: int = Field(default=3, ge=3, le=4)
    author_id: UUID4 | None = Field(default=None, examples=[""])

    @model_validator(mode="after")
    def check_step_rules(self) -> "ClusterUpdate":
        match self.step:
            case 3 if self.author_id is None:
                raise ValueError("Author ID is required")

        return self

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        data["status"] = GenerationStatus.get_step_by_id(data.pop("step"))
        return data


class ClusterQueueResponse(BaseModel):
    cluster_id: UUID4
    queue: int
