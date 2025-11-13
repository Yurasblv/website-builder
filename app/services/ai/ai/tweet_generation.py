import random

from langchain_openai import ChatOpenAI

from app.core import settings
from app.enums import TweetThemes
from app.schemas import Tweet


class TweetGenerationService:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=settings.ai.OPENAI_MODEL_NAME,
            temperature=0.7,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=settings.ai.OPENAI_API_KEY,
        )
        self.structured_llm = self.llm.with_structured_output(Tweet)

    async def generate_tweet(self, introduction: str, forbidden_topics: list["str"] | None) -> Tweet:
        theme = random.choice(list(TweetThemes))

        extra_rule = (
            f" You have written tweets on these topics recently: {forbidden_topics}, so don't repeat yourself."
            if forbidden_topics
            else ""
        )

        messages = [
            (
                "system",
                f"{introduction}",
            ),
            (
                "human",
                f"Write a tweet that {theme}." + extra_rule,
            ),
        ]

        return await self.structured_llm.ainvoke(messages)
