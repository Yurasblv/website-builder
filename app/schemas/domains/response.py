from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict, Field

from app.enums import DomainStatus, DomainType


class DomainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID4 = Field(..., description="Unique identifier for the domain.")
    name: str = Field(..., description="The name of the domain, e.g., 'example.com'.", examples=["example.com"])
    category_id: UUID4 = Field(..., description="The category of the domain.")
    domain_type: DomainType = Field(..., description="The type of the domain.", examples=DomainType.list())
    domain_status: DomainStatus = Field(..., description="The status of the domain.", examples=DomainStatus.list())
    expire_at: datetime | None = Field(None, description="The expiration date of the domain.")
    created_at: datetime = Field(None, description="Creation datetime.")
    pbn_id: UUID4 | None = Field(None, description="Unique identifier for the PBN.")
    user_id: UUID4 | None = Field(None, description="Unique identifier for the user.")


class DomainCustomResponse(DomainResponse):
    NS: list[str] = Field(
        ...,
        description="List of name servers associated with the domain.",
        examples=["ns1.example.com", "ns2.example.com"],
    )
