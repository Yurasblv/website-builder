from datetime import datetime
from uuid import uuid4

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator

from app.enums.provider import ServerProviderStatus, ServerProviderType
from app.enums.provider.hetzner import HetznerImageType, HetznerLocationType, HetznerServerType
from app.enums.provider.scaleway import ScalewayImageType, ScalewayLocationType, ScalewayServerType


class BaseProviderIdentifier(BaseModel):
    server_id: str = Field(..., description="Server id")
    provider_type: ServerProviderType
    location: str = Field(..., description="Server location")


class CreateProviderServer(BaseModel):
    id: UUID4 = Field(default_factory=uuid4, examples=["0c1c43fc-e6f1-45a7-8ae5-0283086dbb4e"])
    provider_type: ServerProviderType = Field(
        ..., description="Server provider type", examples=ServerProviderType.list()
    )
    name: str = Field(..., description="Server name", examples=["test-server"])
    location: HetznerLocationType | ScalewayLocationType = Field(
        ..., description="Server location", examples=HetznerLocationType.list() + ScalewayLocationType.list()
    )
    server_type: HetznerServerType | ScalewayServerType = Field(
        ..., description="Server instance type", examples=HetznerServerType.list() + ScalewayServerType.list()
    )
    image: HetznerImageType | ScalewayImageType = Field(
        ..., description="Server OS image", examples=HetznerImageType.list() + ScalewayImageType.list()
    )

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class GetProviderServer(BaseProviderIdentifier):
    pass


class DeleteProviderServer(BaseProviderIdentifier):
    pass


class CreateServerDns(BaseProviderIdentifier):
    ip: str = Field(..., description="Server ip")
    domain: str = Field(..., description="Server domain")


class ProviderServerRead(BaseModel):
    id: UUID4 | None = Field(None, description="Instance id")
    server_id: str = Field(..., description="Server id")
    provider_type: ServerProviderType
    name: str = Field(..., description="Server name")
    status: ServerProviderStatus = Field(..., description="Server status")
    location: str = Field(..., description="Server location")
    public_net_ipv4: str = Field(..., description="Server public ipv4")
    public_net_ipv6: str = Field(..., description="Server public ipv6")
    ssh_private_key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class WPConfig(BaseModel):
    SERVER_DOMAIN: str
    WP_TOKEN: str
    WP_ADMIN_LOGIN: str
    WP_ADMIN_PASSWORD: str
    WP_PORT: str
    WP_CONTAINER_NAME: str
    WP_TEMPLATE_URL: str
    WP_MYSQL_DB: str
    WP_MYSQL_USER: str
    WP_MYSQL_PASSWORD: str

    model_config = ConfigDict(from_attributes=True, extra="allow")

    @field_validator("SERVER_DOMAIN")
    @classmethod
    def validate_domain_zone(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            value = "https://" + value

        if not value.endswith("/"):
            value = value + "/"

        return value
