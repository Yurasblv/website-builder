from pydantic import UUID4, Field

from .base import SocialNetworkBase


class SocialNetworkWebsiteRead(SocialNetworkBase):
    id: UUID4 = Field(..., description="The ID of the social network")
