import json
from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.enums import Language
from app.schemas.mixins import StrToJSONMixin


class BaseAuthor(BaseModel):
    industry_id: UUID4 = Field(description="Author industry id")
    first_name: str = Field(description="Author first name", examples=["John", "Jane"])
    last_name: str = Field(description="Author last name", examples=["Doe", "Smith"])
    language: Language = Field(description="Author language", examples=Language.list())


class Education(BaseModel):
    degree: str | None = Field(
        default=None, description="Degree", examples=["B.Sc. in Agricultural Science", "M.Sc. in Environmental Science"]
    )
    university: str | None = Field(
        default=None, description="University", examples=["University of California", "University of Oxford"]
    )


class AuthorResponseBase(BaseAuthor):
    id: UUID4 = Field(description="Author id")
    education: Education | None = Field(
        description="Author education",
        examples=[
            "B.Sc. in Agricultural Science, University of California",
            "M.Sc. in Environmental Science, University of California",
        ],
    )
    profession: str | None = Field(
        description="Author profession", examples=["Agronomist at Syngenta", "Mining Engineer at BHP"]
    )
    is_custom: bool = Field(..., description="Is custom author", validate_default=True)
    industry_title: str = Field(..., description="Author industry")
    avatar: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthorResponse(AuthorResponseBase):
    website_link: HttpUrl | None = Field(default=None, description="Author website link")


class SystemAuthorResponse(AuthorResponseBase):
    pass


class CreateAuthorBase(StrToJSONMixin, BaseAuthor):
    education: Education | None = None
    profession: str | None = None


class CreateAuthor(CreateAuthorBase):
    website_link: HttpUrl | None = Field(None, description="Author website link")

    @field_validator("website_link", mode="after")
    @classmethod
    def validate_website_link(cls, v: str | None) -> str | None:
        return str(v) if v else None


class CreateSystemAuthor(CreateAuthorBase):
    pass


class UpdateAuthor(CreateAuthor):
    industry_id: UUID4 | None = Field(None, description="Author industry id")
    first_name: str | None = None
    last_name: str | None = None
    language: Language | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_empty(cls, values: dict) -> dict:
        values = json.loads(values) if isinstance(values, str) else values

        if any(values.values()):
            return values

        raise ValueError("At least one field should be provided for update")


class AuthorLoadFromCSV(BaseModel):
    industry_title: str
    first_name: str
    last_name: str
    language: Language
    degree: str = Field(..., description="Degree", exclude=True)
    university: str = Field(..., description="University", exclude=True)
    education: dict
    profession: str
    avatar: str
    website: str

    @model_validator(mode="before")
    @classmethod
    def validate_education(cls, values: dict) -> dict:
        values["education"] = {"degree": values.get("degree"), "university": values.get("university")}
        return values

    model_config = ConfigDict(extra="ignore")


class AuthorElementContent(BaseModel):
    full_name: str = Field(description="Author full name.")
    website_link: str | None = Field(description="Author website link.")
    avatar: str | None = Field(description="Author avatar.")
    avatar_url: str | None = Field(description="Author avatar URL.")
    extra_info: list[tuple[str, str | None]] = Field(description="List of tuples containing tag type and value.")

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class AuthorFilters(BaseModel):
    industry_id: UUID4 | None = None
    first_name: str | None = None
    last_name: str | None = None
    language: Language | None = None
    education: str | None = None
    profession: str | None = None
