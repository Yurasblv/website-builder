from uuid import uuid4

from pydantic import UUID4, BaseModel, ConfigDict, Field

from app.enums import IntegrationType


class IntegrationBase(BaseModel):
    user_id: str
    integration_type: IntegrationType

    model_config = ConfigDict(from_attributes=True)


class IntegrationCreate(IntegrationBase):
    id: UUID4 = Field(default_factory=uuid4)
