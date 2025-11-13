import os
import random
from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.config.base import BaseConfig


class AIConfig(BaseConfig):
    # OpenAI
    OPENAI_API_KEY: str = Field(..., alias="OPENAI_API_KEY")
    OPENAI_MODEL_NAME: str = "gpt-4o"
    OPENAI_SECONDARY_MODEL_NAME: str = "gpt-4o-mini"
    OPENAI_SMART_MODEL_NAME: str = "o1"
    OPENAI_RETRY_ATTEMPTS: int = 3
    OPENAI_RETRY_WAIT_SECONDS: int = 60
    OPENAI_TOPIC_TEMPERATURE: float = 1.0
    temperature_regression: float = 0.04
    similarity_point: float = 0.70
    similarity_regression: float = 0.02
    similarity_regression_noize: tuple[float, float] = (0.9, 1.1)

    # LangSmith
    LANGSMITH_TRACING: bool = Field(True, alias="LANGSMITH_TRACING")
    LANGSMITH_ENDPOINT: str = Field("https://api.smith.langchain.com", alias="LANGSMITH_ENDPOINT")
    LANGSMITH_API_KEY: str = Field("", alias="LANGSMITH_API_KEY")
    LANGSMITH_PROJECT: str = Field("NDA-local-kk", alias="LANGSMITH_PROJECT")

    # FreePik
    FREEPIK_API_KEY: str = Field(..., alias="FREEPIK_API_KEY")
    FREEPIK_URL: str = Field("https://api.freepik.com/v1/resources", alias="FREEPIK_URL")

    # Flux
    FLUX_API_KEY: str = Field(..., alias="FLUX_API_KEY")
    FLUX_ENDPOINT: str = Field("https://api.aimlapi.com/v1/images/generations", alias="FLUX_ENDPOINT")

    # bleach formatter
    ALLOWED_TAGS: list[str] = ["section", "a", "p", "b", "strong", "ref"]
    ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
        "a": ["id", "href"],
        "ref": ["fn_item_id"],
    }

    OPEN_AI_ROLE: str = (
        "You are a highly skilled web site content creator and web site designer. "
        "Stick to your target language and country. "
        "You are writing content and a structure of the website for a specified keyword. "
        "Use meta words if given to generate more detailed content. "
        "Take into account that today is {date} year and month.\n\n"
        "**Always format your answer in the following way: **\n"
        "- use sentence case;\n"
        "- never add any additional explanations of result;\n"
        "- never enclose your answer in quotes, provide just text;\n"
        "- never add any markdown and emojis. "
    ).format(date=datetime.now().strftime("%Y/%m"))

    OPENAI_FORMATTING_ROLE: str = (
        "You are a highly skilled web site content editor. "
        "Your goal is to change the given content according to the given rules. "
    )

    OPENAI_CASE_VERIFICATION_ROLE: str = """
    You are a helpful assistant responsible for verifying that the input text is correctly formatted.
    The only acceptable formatting style is sentence case.
    Ensure the entire text strictly adheres to sentence case throughout."""

    OPENAI_JOURNALIST_ROLE: str = """
    You are a professional content reviewer.
    Given a piece of content, pay attention to the most relevant keywords and entities
    from it and transform them according to the instructions. """

    LOWERCASE_WARNING: str = """
    Entire text appears to be written in lowercase, including sentence beginnings, acronyms, and proper nouns.
    It needs full capitalization corrections throughout."""

    NER_PREDICTIONS_FILE_PATH: str = os.path.abspath("./Regression_Data.csv")

    def get_similar_point(self, layer: int) -> float:
        """
        Get the similarity point for the given layer.

        Args:
            layer: The layer number.

        Returns:
            The similarity point.
        """
        regression = self.similarity_regression * layer * random.uniform(*self.similarity_regression_noize)

        return self.similarity_point - regression

    def get_temperature(self, layer: int) -> float:
        """
        Get the temperature for the given layer.

        Args:
            layer: The layer number.

        Returns:
            The temperature.
        """
        regression = self.OPENAI_TOPIC_TEMPERATURE + layer * self.temperature_regression

        return min(regression, 2.0)

    def model_post_init(self, __context: Any) -> None:
        """Export LangSmith keys to the environment."""
        if not self.LANGSMITH_API_KEY:
            return

        os.environ["LANGSMITH_API_KEY"] = self.LANGSMITH_API_KEY
        os.environ["LANGSMITH_PROJECT"] = self.LANGSMITH_PROJECT
        os.environ["LANGSMITH_ENDPOINT"] = self.LANGSMITH_ENDPOINT
        os.environ["LANGSMITH_TRACING"] = str(self.LANGSMITH_TRACING)
