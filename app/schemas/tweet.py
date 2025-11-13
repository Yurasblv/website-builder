from pydantic import BaseModel, Field


class Tweet(BaseModel):
    topic: str = Field(description="The topic of the tweet")
    text: str = Field(description="The text of the tweet")
