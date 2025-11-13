from datetime import datetime
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.enums import WPIntegrationType, WPPageType, WPPluginStyle


class IntegrationWordPressUpdate(BaseModel):
    api_key: str = Field(..., description="The API key for the WordPress site.")

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, values: str) -> str:
        if v := values.strip():
            return v

        raise ValueError("API key cannot be empty.")


class IntegrationWordPressCreateRequest(IntegrationWordPressUpdate):
    domain: HttpUrl = Field(..., description="The domain of the WordPress site.")


class IntegrationWordPressRead(BaseModel):
    id: UUID4
    domain: str = Field(..., description="The domain of the WordPress site.", examples=["example.com"])
    created_at: datetime
    updated_at: datetime
    type: WPIntegrationType

    model_config = ConfigDict(from_attributes=True)

    @field_validator("domain", mode="before")
    @classmethod
    def validate_domain(cls, values: str) -> str:
        return values.split("//")[-1].strip("/")


class IntegrationWordPressUpload(BaseModel):
    replace: bool = Field(True, description="Whether to overwrite existing files.")
    style: WPPluginStyle = Field(
        WPPluginStyle.NDA, description="The style of the WordPress plugin.", examples=WPPluginStyle.list()
    )
    type: WPPageType = Field(WPPageType.PAGE, description="The type of the WordPress page.", examples=WPPageType.list())

    def get_data(self, **kwargs: Any) -> dict[str, str | bool]:
        return dict(replace=self.replace, style=self.style, **kwargs)


class IntegrationWordPressUploadByChunks(BaseModel):
    domain: str = Field(..., description="The domain of the WordPress site.", examples=["example.com"])
    api_key: str = Field(..., description="The API key for the WordPress site.")
    keyword: str
    data: IntegrationWordPressUpload
    cluster_id: str
    user_id: str
    file_bytes: bytes
    is_api_upload: bool = True


class IntegrationWordPressVersionResponse(BaseModel):
    current_version: str = Field(..., description="The current version of the WordPress plugin.")
    latest_version: str = Field(..., description="The latest version of the WordPress plugin.")
    is_latest: bool = Field(..., description="Whether the version is the latest one.")
