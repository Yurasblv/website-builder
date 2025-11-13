from pydantic import BaseModel, ConfigDict, Field


class CloudFlareBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class CloudFlareResponseBase(CloudFlareBase):
    success: bool | None = Field(None, description="Success status")
    errors: list[dict] | None = Field(None, description="List of errors")
    messages: list[dict] | None = Field(None, description="List of messages")


class CloudFlareAccount(CloudFlareBase):
    id: str = Field(..., description="Account ID")
    name: str = Field(..., description="Account name")


class CloudFlareSSLCertificateConfig(CloudFlareBase):
    enabled: bool = Field(..., description="Enabled status")


class CloudFlareZoneDetails(CloudFlareBase):
    id: str = Field(..., description="Zone ID")
    account: CloudFlareAccount = Field(..., description="Account details")
    name: str = Field(..., description="Zone name")
    ns: list[str] | None = Field(None, alias="name_servers", description="Vanity name servers")
    original_ns: list[str] | None = Field(None, alias="original_name_servers", description="Original name servers")


class CloudFlareZoneResponse(CloudFlareResponseBase):
    result: CloudFlareZoneDetails = Field(..., description="List of zones")


class CloudflareSSLCertificateResponse(CloudFlareResponseBase):
    result: list[dict] | None = Field(None, description="List of SSL certificates")


class CloudFlareSSLCertificateSettingsResponse(CloudFlareResponseBase):
    result: CloudFlareSSLCertificateConfig = Field(..., description="SSL certificate settings")
