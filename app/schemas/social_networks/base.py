from datetime import datetime

from pydantic import UUID4, BaseModel, Field, HttpUrl, field_validator

from app.enums import SocialNetworkType


class SocialNetworkBase(BaseModel):
    social_link: HttpUrl | None

    @field_validator("social_link", mode="after")
    @classmethod
    def validate_social_link(cls, v: str | None) -> str | None:
        return str(v) if v else None


class SocialNetworkAllResponse(SocialNetworkBase):
    id: UUID4 = Field(..., description="The ID of the social network")
    author_id: UUID4 = Field(..., description="The ID of author")
    social_network_type: SocialNetworkType = Field(
        None, description="Social network type", examples=SocialNetworkType.list()
    )
    created_at: datetime
    updated_at: datetime
