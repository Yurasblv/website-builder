from pydantic import UUID4, Field

from .base import SocialNetworkBase


class SocialNetworkXCreate(SocialNetworkBase):
    api_key: str = Field(..., description="The API key of the social network")
    api_secret: str = Field(..., description="The API secret of the social network")
    access_token: str = Field(..., description="The access token of the social network")
    access_token_secret: str = Field(..., description="The access token secret of the social network")


class SocialNetworkXRead(SocialNetworkXCreate):
    id: UUID4 = Field(..., description="The ID of the social network")


class SocialNetworkXUpdate(SocialNetworkXCreate):
    pass
