from pydantic import UUID4, BaseModel, Field

from app.enums import SocialNetworkType


class PostCreate(BaseModel):
    text: str = Field(..., description="The topic of the post")
    social_network_id: UUID4 = Field(..., description="The social id of the post")
    post_type: SocialNetworkType = Field(..., description="The type of the post")
